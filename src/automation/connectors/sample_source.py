from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import ListingSourceConnector


class SampleFileConnector(ListingSourceConnector):
    def fetch(self) -> list[dict[str, Any]]:
        path_str = str(self.spec.config.get("path", "")).strip()
        if not path_str:
            raise ValueError(f"Source '{self.spec.name}' missing 'path' config")
        path = Path(path_str)
        if not path.is_absolute():
            root = Path(__file__).resolve().parents[3]
            path = root / path
        payloads = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payloads, list):
            raise ValueError(f"Source '{self.spec.name}' must return JSON list")
        normalized: list[dict[str, Any]] = []
        for payload in payloads:
            if not isinstance(payload, dict):
                continue
            payload.setdefault("source", self.spec.name)
            normalized.append(payload)
        return normalized
