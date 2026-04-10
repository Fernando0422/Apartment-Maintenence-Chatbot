from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .connectors.registry import SourceRunResult
from .models import Recommendation


@dataclass(frozen=True)
class AlertMessage:
    severity: str
    message: str


def evaluate_alerts(
    source_results: Iterable[SourceRunResult],
    recommendation: Recommendation,
) -> list[AlertMessage]:
    alerts: list[AlertMessage] = []
    failures = [r for r in source_results if not r.success]
    if failures:
        alerts.append(
            AlertMessage(
                severity="warning",
                message=f"{len(failures)} sources failed during fetch.",
            )
        )
    if recommendation.comp_count < 3:
        alerts.append(
            AlertMessage(
                severity="warning",
                message="Comparable depth below threshold (min 3).",
            )
        )
    if recommendation.confidence_score < 0.45:
        alerts.append(
            AlertMessage(
                severity="critical",
                message="Confidence below decision threshold.",
            )
        )
    return alerts


def write_ops_log(path: Path, source_results: Iterable[SourceRunResult], alerts: Iterable[AlertMessage]) -> None:
    lines: list[str] = []
    lines.append("=== SOURCE RUN SUMMARY ===")
    for result in source_results:
        status = "OK" if result.success else "FAIL"
        err = f" | error={result.error}" if result.error else ""
        lines.append(f"[{status}] {result.source_name} listings={result.listing_count}{err}")

    lines.append("")
    lines.append("=== ALERTS ===")
    found = False
    for alert in alerts:
        found = True
        lines.append(f"[{alert.severity.upper()}] {alert.message}")
    if not found:
        lines.append("[INFO] No alerts")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
