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
    # Accepts values like "$95,000 MXN / month", "USD 6,000 /mes", "$ 3,200 /mes".
    m = re.search(
        r"\$\s*([\d,]+(?:\.\d+)?)\s*(USD|MXN)?|"
        r"(USD|MXN)\s*([\d,]+(?:\.\d+)?)|"
        r"([\d,]+(?:\.\d+)?)\s*(USD|MXN)",
        text,
        flags=re.IGNORECASE,
    )
    if not m:
        return None

    if m.group(1):
        amount_raw = m.group(1)
        trailing = (m.group(2) or "").upper()
        # In MX listing pages, "$" usually means MXN unless explicitly USD.
        currency = trailing if trailing in {"USD", "MXN"} else "MXN"
    elif m.group(3):
        currency = m.group(3).upper()
        amount_raw = m.group(4)
    else:
        amount_raw = m.group(5)
        currency = m.group(6).upper()

    amount = float(amount_raw.replace(",", ""))
    return currency, amount


def _extract_beds(text: str) -> int:
    candidates: list[int] = []
    for m in re.finditer(r"\b(\d{1,2})\s+(?:rec[aá]maras|bed(?:room)?s?)\b", text, flags=re.IGNORECASE):
        candidates.append(int(m.group(1)))
    for m in re.finditer(r"\b(?:rec[aá]maras|bed(?:room)?s?)\s*[:\-]?\s*(\d{1,2})\b", text, flags=re.IGNORECASE):
        candidates.append(int(m.group(1)))
    valid = [x for x in candidates if 0 < x <= 10]
    return valid[0] if valid else 0


def _extract_baths(text: str) -> float:
    candidates: list[float] = []
    for m in re.finditer(r"\b(\d{1,2}(?:\.\d+)?)\s+(?:ba[ñn]os|bath(?:room)?s?)\b", text, flags=re.IGNORECASE):
        candidates.append(float(m.group(1)))
    for m in re.finditer(r"\b(?:ba[ñn]os|bath(?:room)?s?)\s*[:\-]?\s*(\d{1,2}(?:\.\d+)?)\b", text, flags=re.IGNORECASE):
        candidates.append(float(m.group(1)))
    valid = [x for x in candidates if 0 < x <= 10]
    return valid[0] if valid else 0.0


def _extract_size_m2(text: str) -> float:
    m2_matches = re.finditer(r"\b(\d{2,4}(?:\.\d+)?)\s*(?:m2|m²)\b", text, flags=re.IGNORECASE)
    m2_vals = [float(m.group(1)) for m in m2_matches]
    m2_valid = [x for x in m2_vals if 15 <= x <= 1000]
    if m2_valid:
        return m2_valid[0]
    sqft_matches = re.finditer(r"\b(\d{3,5}(?:\.\d+)?)\s*(?:sq\.?\s*ft|sqft)\b", text, flags=re.IGNORECASE)
    sqft_vals = [float(m.group(1)) for m in sqft_matches]
    sqft_valid = [x for x in sqft_vals if 200 <= x <= 12000]
    if sqft_valid:
        return round(sqft_valid[0] * 0.092903, 2)
    return 0.0


def _extract_currency_and_price_from_segment(segment: str) -> tuple[str, float] | None:
    # Prioritize explicit currency labels near the target section.
    m = re.search(r"\$?\s*([\d,]+(?:\.\d+)?)\s*(USD|MXN)\b", segment, flags=re.IGNORECASE)
    if m:
        amount = float(m.group(1).replace(",", ""))
        currency = m.group(2).upper()
        return currency, amount
    return _extract_currency_and_price(segment)


def _extract_section_after(text: str, heading: str, max_chars: int = 2000) -> str:
    idx = text.lower().find(heading.lower())
    if idx < 0:
        return ""
    return text[idx : idx + max_chars]


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
                    title = _clean_text(re.sub(r"<[^>]+>", " ", h1.group(1)))
            if not title:
                t = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
                if t:
                    title = _clean_text(t.group(1))

            # Focus parsing in the listing details area when present to avoid page-wide noise.
            detail_segment = (
                _extract_section_after(doc_text, "Rental Details and Pricing", max_chars=2500)
                or _extract_section_after(doc_text, "Typologies & Prices", max_chars=2500)
                or _extract_section_after(doc_text, "Monthly Rental Price", max_chars=1200)
                or _extract_section_after(doc_text, "Monthly Rent", max_chars=1200)
                or doc_text[:2500]
            )

            if price is None or currency is None:
                parsed = _extract_currency_and_price_from_segment(detail_segment)
                if parsed:
                    currency, price = parsed

            if bedrooms == 0:
                bedrooms = _extract_beds(detail_segment) or _extract_beds(doc_text)
            if bathrooms == 0.0:
                bathrooms = _extract_baths(detail_segment) or _extract_baths(doc_text)
            if size_m2 == 0.0:
                size_m2 = _extract_size_m2(detail_segment) or _extract_size_m2(doc_text)

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
