import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import get_connection


ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT / "data" / "sample_listings.json"


def load_sample_payloads() -> list[dict[str, Any]]:
    payloads = json.loads(SAMPLE_DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(payloads, list):
        raise ValueError("Sample listings must be a JSON list")
    return payloads


def save_raw_listings(payloads: list[dict[str, Any]]) -> list[int]:
    scraped_at = datetime.now(timezone.utc).isoformat()
    inserted_ids: list[int] = []
    with get_connection() as conn:
        for payload in payloads:
            cursor = conn.execute(
                """
                INSERT INTO raw_listings (source, source_listing_id, url, payload_json, scraped_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload["source"],
                    payload["source_listing_id"],
                    payload.get("url", ""),
                    json.dumps(payload, sort_keys=True),
                    scraped_at,
                ),
            )
            inserted_ids.append(int(cursor.lastrowid))
    return inserted_ids
