import json
from typing import Any

from .config import FX_TO_USD, MIN_QUALITY_SCORE
from .db import get_connection
from .models import CleanListing


def _price_to_usd_month(price: float, currency: str, period: str) -> float:
    if currency not in FX_TO_USD:
        raise ValueError(f"Unsupported currency: {currency}")
    price_usd = price * FX_TO_USD[currency]
    if period == "month":
        return price_usd
    if period == "week":
        return price_usd * 4.345
    if period == "night":
        return price_usd * 30.0
    raise ValueError(f"Unsupported period: {period}")


def _quality_score(payload: dict[str, Any]) -> float:
    score = 0.0
    if payload.get("description"):
        score += 0.3
    if payload.get("size_m2", 0) >= 80:
        score += 0.2
    if payload.get("bedrooms", 0) >= 2:
        score += 0.2
    if payload.get("bathrooms", 0) >= 2:
        score += 0.1
    if payload.get("building"):
        score += 0.2
    return min(score, 1.0)


def _is_probable_duplicate(payload: dict[str, Any]) -> bool:
    # Simple MVP duplicate heuristic; improve with fuzzy address/title hash.
    title = (payload.get("title") or "").strip().lower()
    building = (payload.get("building") or "").strip().lower()
    return not title or not building


def normalize_and_save_clean_listings() -> list[CleanListing]:
    clean_listings: list[CleanListing] = []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT r.id, r.source, r.source_listing_id, r.payload_json
            FROM raw_listings r
            LEFT JOIN clean_listings c
              ON c.source = r.source AND c.source_listing_id = r.source_listing_id
            WHERE c.id IS NULL
            ORDER BY r.id ASC
            """
        ).fetchall()
        for row in rows:
            payload = json.loads(row["payload_json"])
            market_type = payload.get("market_type", "unknown")
            quality = _quality_score(payload)
            duplicate = _is_probable_duplicate(payload)
            if quality < MIN_QUALITY_SCORE:
                continue

            price_usd_month = _price_to_usd_month(
                float(payload["price"]),
                str(payload["currency"]).upper(),
                str(payload["period"]).lower(),
            )
            item = CleanListing(
                raw_id=int(row["id"]),
                source=row["source"],
                source_listing_id=row["source_listing_id"],
                market_type=market_type,
                building=str(payload.get("building", "")).strip(),
                neighborhood=str(payload.get("neighborhood", "")).strip(),
                latitude=float(payload.get("latitude", 0.0)),
                longitude=float(payload.get("longitude", 0.0)),
                bedrooms=int(payload.get("bedrooms", 0)),
                bathrooms=float(payload.get("bathrooms", 0)),
                size_m2=float(payload.get("size_m2", 0)),
                furnished=bool(payload.get("furnished", False)),
                price_usd_month=round(price_usd_month, 2),
                first_seen_date=str(payload.get("first_seen_date", "")),
                last_seen_date=str(payload.get("last_seen_date", "")),
                quality_score=round(quality, 3),
                is_duplicate=duplicate,
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO clean_listings (
                    raw_id, source, source_listing_id, market_type, building, neighborhood,
                    latitude, longitude, bedrooms, bathrooms, size_m2, furnished,
                    price_usd_month, first_seen_date, last_seen_date, quality_score, is_duplicate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.raw_id,
                    item.source,
                    item.source_listing_id,
                    item.market_type,
                    item.building,
                    item.neighborhood,
                    item.latitude,
                    item.longitude,
                    item.bedrooms,
                    item.bathrooms,
                    item.size_m2,
                    1 if item.furnished else 0,
                    item.price_usd_month,
                    item.first_seen_date,
                    item.last_seen_date,
                    item.quality_score,
                    1 if item.is_duplicate else 0,
                ),
            )
            clean_listings.append(item)
    return clean_listings
