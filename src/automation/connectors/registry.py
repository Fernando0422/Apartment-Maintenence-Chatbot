from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .base import ListingSourceConnector, SourceSpec
from .http_json_source import HttpJsonConnector
from .sample_source import SampleFileConnector


ROOT = Path(__file__).resolve().parents[3]
SOURCES_CONFIG_PATH = ROOT / "config" / "sources.json"


@dataclass(frozen=True)
class SourceRunResult:
    source_name: str
    success: bool
    listing_count: int
    error: str | None = None


def load_source_specs() -> list[SourceSpec]:
    data = json.loads(SOURCES_CONFIG_PATH.read_text(encoding="utf-8"))
    raw_sources = data.get("sources", [])
    if not isinstance(raw_sources, list):
        raise ValueError("config/sources.json must contain a 'sources' array")

    specs: list[SourceSpec] = []
    for entry in raw_sources:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        source_type = str(entry.get("type", "")).strip()
        enabled = bool(entry.get("enabled", False))
        modes = entry.get("modes", [])
        if not name or not source_type:
            continue
        mode_tuple = tuple(str(m).strip() for m in modes if str(m).strip())
        cfg = {k: v for k, v in entry.items() if k not in {"name", "type", "enabled", "modes"}}
        specs.append(
            SourceSpec(
                name=name,
                source_type=source_type,
                enabled=enabled,
                modes=mode_tuple,
                config=cfg,
            )
        )
    return specs


def _build_connector(spec: SourceSpec) -> ListingSourceConnector:
    if spec.source_type == "sample":
        return SampleFileConnector(spec)
    if spec.source_type == "http_json":
        return HttpJsonConnector(spec)
    raise ValueError(f"Unsupported source type: {spec.source_type}")


def fetch_from_sources(mode: str) -> tuple[list[dict[str, Any]], list[SourceRunResult]]:
    mode = mode.strip().lower()
    if mode not in {"sample", "live", "hybrid"}:
        raise ValueError("mode must be one of: sample, live, hybrid")

    all_payloads: list[dict[str, Any]] = []
    run_results: list[SourceRunResult] = []
    for spec in load_source_specs():
        if not spec.enabled:
            continue
        if mode not in spec.modes:
            continue

        connector = _build_connector(spec)
        try:
            payloads = connector.fetch()
            all_payloads.extend(payloads)
            run_results.append(
                SourceRunResult(
                    source_name=spec.name,
                    success=True,
                    listing_count=len(payloads),
                    error=None,
                )
            )
        except Exception as exc:  # broad by design for ingestion isolation
            run_results.append(
                SourceRunResult(
                    source_name=spec.name,
                    success=False,
                    listing_count=0,
                    error=str(exc),
                )
            )
    return all_payloads, run_results
