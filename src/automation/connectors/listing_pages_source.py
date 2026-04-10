from __future__ import annotations

import json
import re
from html import unescape
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import ListingSourceConnector


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _extract_currency_and_price(text: str) -> tuple[str, float] | None:
    # Accepts values like "$95,000 MXN / month" or "USD 6,000 /mes"
    m = re.search(
        r"(USD|MXN|\$)\s*([\d,]+(?:\.\d+)?)|([\d,]+(?:\.\d+)?)\s*(USD|MXN)",
        text,
        flags=re.IGNORECASE,
    )
    if not m:
        return None
    if m.group(1):
        currency_raw = m.group(1).upper()
        amount_raw = m.group(2)
    else:
        amount_raw = m.group(3)
        currency_raw = m.group(4).upper()

    currency = "USD" if currency_raw in {"USD", "$"} else "MXN"
    amount = float(amount_raw.replace(",", ""))
    return currency, amount


def _extract_beds(text: str) -> int:
    m = re.search(r"(\d+)\s*(?:rec[aá]maras|bed(?:room)?s?)", text, flags=re.IGNORECASE)
    return int(m.group(1)) if m else 0


def _extract_baths(text: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:ba[ñn]os|bath(?:room)?s?)", text, flags=re.IGNORECASE)
    return float(m.group(1)) if m else 0.0


def _extract_size_m2(text: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:m2|m²)", text, flags=re.IGNORECASE)
    if m:
        return float(m.group(1))
    sqft = re.search(r"(\d{3,5}(?:\.\d+)?)\s*(?:sq\.?\s*ft|sqft)", text, flags=re.IGNORECASE)
    if sqft:
        return round(float(sqft.group(1)) * 0.092903, 2)
    return 0.0


class ListingPagesConnector(ListingSourceConnector):
    def fetch(self) -> list[dict[str, Any]]:
        entries = self.spec.config.get("entries", [])
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"Source '{self.spec.name}' missing non-empty 'entries' config")

        timeout = int(self.spec.config.get("timeout_seconds", 20))
        headers = self.spec.config.get("headers", {})
        if not isinstance(headers, dict):
            headers = {}
        request_headers = {"User-Agent": "Mozilla/5.0"}
        request_headers.update({str(k): str(v) for k, v in headers.items()})

        out: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            url = str(entry.get("url", "")).strip()
            if not url:
                continue
            listing_id = str(entry.get("source_listing_id", "")).strip() or url
            known_market_type = str(entry.get("market_type", "long_term")).strip().lower()
            known_building = str(entry.get("building", "AWA")).strip()
            known_neighborhood = str(entry.get("neighborhood", "Playa del Carmen Centro")).strip()

            try:
                req = Request(url=url, headers=request_headers)
                with urlopen(req, timeout=timeout) as resp:
                    html = resp.read().decode("utf-8", "ignore")
            except HTTPError as exc:
                raise RuntimeError(
                    f"HTTP error fetching source '{self.spec.name}' entry '{url}': {exc.code}"
                ) from exc
            except URLError as exc:
                raise RuntimeError(
                    f"URL error fetching source '{self.spec.name}' entry '{url}': {exc.reason}"
                ) from exc

            # Prefer JSON-LD if available.
            title = ""
            description = ""
            price: float | None = None
            currency: str | None = None
            size_m2 = 0.0
            bedrooms = 0
            bathrooms = 0.0

            for ld in re.findall(
                r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                html,
                flags=re.IGNORECASE | re.DOTALL,
            ):
                text = _clean_text(ld)
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    continue
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    if not title:
                        title = str(item.get("name", "")).strip()
                    if not description:
                        description = str(item.get("description", "")).strip()
                    offers = item.get("offers")
                    if isinstance(offers, dict):
                        maybe_price = offers.get("price")
                        maybe_currency = offers.get("priceCurrency")
                        if maybe_price is not None and price is None:
                            try:
                                price = float(str(maybe_price).replace(",", ""))
                            except ValueError:
                                pass
                        if maybe_currency and currency is None:
                            currency = str(maybe_currency).upper()

            doc_text = _clean_text(re.sub(r"<[^>]+>", " ", html))
            if not title:
                h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.IGNORECASE | re.DOTALL)
                if h1:
                    title = _clean_text(h1.group(1))
            if not title:
                t = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
                if t:
                    title = _clean_text(t.group(1))

            if price is None or currency is None:
                parsed = _extract_currency_and_price(doc_text)
                if parsed:
                    currency, price = parsed

            if bedrooms == 0:
                bedrooms = _extract_beds(doc_text)
            if bathrooms == 0.0:
                bathrooms = _extract_baths(doc_text)
            if size_m2 == 0.0:
                size_m2 = _extract_size_m2(doc_text)

            if price is None or currency is None:
                continue

            payload: dict[str, Any] = {
                "source": self.spec.name,
                "source_listing_id": listing_id,
                "url": url,
                "title": title or f"{known_building} listing",
                "market_type": known_market_type or "long_term",
                "building": known_building,
                "neighborhood": known_neighborhood,
                "latitude": float(entry.get("latitude", 20.6368)),
                "longitude": float(entry.get("longitude", -87.0748)),
                "bedrooms": int(entry.get("bedrooms", bedrooms)),
                "bathrooms": float(entry.get("bathrooms", bathrooms)),
                "size_m2": float(entry.get("size_m2", size_m2)),
                "furnished": bool(entry.get("furnished", True)),
                "price": float(price),
                "currency": currency,
                "period": str(entry.get("period", "month")).lower(),
                "first_seen_date": str(entry.get("first_seen_date", "")),
                "last_seen_date": str(entry.get("last_seen_date", "")),
                "description": description or title,
            }
            out.append(payload)

        return out
