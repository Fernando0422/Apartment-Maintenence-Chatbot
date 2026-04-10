from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import ListingSourceConnector


class HttpJsonConnector(ListingSourceConnector):
    def fetch(self) -> list[dict[str, Any]]:
        url = str(self.spec.config.get("url", "")).strip()
        if not url:
            raise ValueError(f"Source '{self.spec.name}' missing 'url' config")
        timeout = int(self.spec.config.get("timeout_seconds", 20))
        headers = self.spec.config.get("headers", {})
        if not isinstance(headers, dict):
            headers = {}

        req = Request(url=url, headers={str(k): str(v) for k, v in headers.items()})
        try:
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
        except HTTPError as exc:
            raise RuntimeError(f"HTTP error fetching source '{self.spec.name}': {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"URL error fetching source '{self.spec.name}': {exc.reason}") from exc

        parsed = json.loads(raw)
        payloads: list[dict[str, Any]]
        if isinstance(parsed, list):
            payloads = [x for x in parsed if isinstance(x, dict)]
        elif isinstance(parsed, dict) and isinstance(parsed.get("listings"), list):
            payloads = [x for x in parsed["listings"] if isinstance(x, dict)]
        else:
            raise ValueError(
                f"Source '{self.spec.name}' JSON must be a list or object with 'listings' array"
            )

        for payload in payloads:
            payload.setdefault("source", self.spec.name)
        return payloads
