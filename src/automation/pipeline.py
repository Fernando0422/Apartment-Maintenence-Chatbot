from pathlib import Path

from .alerts import evaluate_alerts, write_ops_log
from .clean import normalize_and_save_clean_listings
from .db import init_db
from .engine import generate_recommendation
from .ingest import load_payloads, save_raw_listings
from .report import render_daily_report


def run_pipeline(mode: str = "sample") -> Path:
    init_db()
    payloads, source_results = load_payloads(mode=mode)
    if not source_results:
        raise RuntimeError(
            f"No enabled sources configured for mode='{mode}'. "
            "Enable at least one source in config/sources.json."
        )
    if not payloads:
        errors = [f"{r.source_name}: {r.error}" for r in source_results if not r.success]
        raise RuntimeError(
            "No payloads collected from configured sources. "
            + (" | ".join(errors) if errors else "Check source configuration.")
        )
    _, run_id = save_raw_listings(payloads)
    normalize_and_save_clean_listings(scraped_at=run_id)
    recommendation, comps = generate_recommendation(scraped_at=run_id)
    report_path = render_daily_report(recommendation, comps)

    ops_log = report_path.with_suffix(".ops.log")
    alerts = evaluate_alerts(source_results, recommendation)
    write_ops_log(ops_log, source_results, alerts)
    return report_path
