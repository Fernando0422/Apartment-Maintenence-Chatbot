import json
from datetime import datetime, timezone
from typing import Any

from .connectors.registry import SourceRunResult, fetch_from_sources
from .db import get_connection


def load_payloads(mode: str = "sample") -> tuple[list[dict[str, Any]], list[SourceRunResult]]:
    return fetch_from_sources(mode=mode)


def save_raw_listings(payloads: list[dict[str, Any]]) -> tuple[list[int], str]:
    run_id = datetime.now(timezone.utc).isoformat()
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
                    run_id,
                ),
            )
            inserted_ids.append(int(cursor.lastrowid))
    return inserted_ids, run_id
