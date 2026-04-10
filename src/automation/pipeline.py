from pathlib import Path

from .clean import normalize_and_save_clean_listings
from .db import init_db
from .engine import generate_recommendation
from .ingest import load_sample_payloads, save_raw_listings
from .report import render_daily_report


def run_pipeline() -> Path:
    init_db()
    payloads = load_sample_payloads()
    save_raw_listings(payloads)
    normalize_and_save_clean_listings()
    recommendation, comps = generate_recommendation()
    return render_daily_report(recommendation, comps)
