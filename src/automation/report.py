from datetime import datetime
from pathlib import Path

from .config import SUBJECT_PROPERTY
from .models import Recommendation, ScoredComp


ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "data" / "reports"


def _fmt_money(value: float) -> str:
    return f"${value:,.0f}"


def render_daily_report(recommendation: Recommendation, comps: list[ScoredComp]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d")
    report_path = REPORTS_DIR / f"market_report_{ts}.md"

    lines: list[str] = []
    lines.append("# AWA Playa Daily Rental Market Report")
    lines.append("")
    lines.append(f"Run date: {recommendation.run_date.isoformat()}")
    lines.append(f"Subject property ID: `{recommendation.subject_property_id}`")
    lines.append("")
    lines.append("## Subject Property")
    lines.append("")
    lines.append(f"- Building: {SUBJECT_PROPERTY.building}")
    lines.append(f"- Neighborhood: {SUBJECT_PROPERTY.neighborhood}")
    lines.append(
        f"- Unit profile: {SUBJECT_PROPERTY.bedrooms} bed / {SUBJECT_PROPERTY.bathrooms:g} bath / {SUBJECT_PROPERTY.size_m2:g} m2"
    )
    lines.append(f"- Furnished: {'yes' if SUBJECT_PROPERTY.furnished else 'no'}")
    lines.append(f"- Baseline lease: {_fmt_money(SUBJECT_PROPERTY.baseline_rent_usd_month)} USD/month")
    lines.append("")
    lines.append("## Market Snapshot (Comparable Set)")
    lines.append("")
    lines.append(f"- Comparable count used: {recommendation.comp_count}")
    lines.append(f"- P25: {_fmt_money(recommendation.p25)}")
    lines.append(f"- P50 (median): {_fmt_money(recommendation.p50)}")
    lines.append(f"- P75: {_fmt_money(recommendation.p75)}")
    lines.append(f"- Confidence score: {recommendation.confidence_score:.3f}")
    lines.append("")
    lines.append("## Recommended Strategy Bands")
    lines.append("")
    lines.append(f"- Fast lease strategy: {_fmt_money(recommendation.fast_rent)}")
    lines.append(f"- Balanced strategy: {_fmt_money(recommendation.balanced_rent)}")
    lines.append(f"- Premium strategy: {_fmt_money(recommendation.premium_rent)}")
    lines.append("")
    lines.append("## Underpricing Signal")
    lines.append("")
    if recommendation.balanced_rent > 0:
        lines.append(
            f"- Baseline vs balanced market estimate: {recommendation.underpricing_pct:+.2f}%"
        )
    else:
        lines.append("- No underpricing estimate due to insufficient confidence.")
    lines.append(f"- Notes: {recommendation.notes}")
    lines.append("")
    lines.append("## Top Comparable Listings")
    lines.append("")
    lines.append("| Rank | Listing ID | Building | Price USD/mo | Score | Why |")
    lines.append("|---:|---|---|---:|---:|---|")
    for idx, comp in enumerate(comps, start=1):
        lines.append(
            f"| {idx} | {comp.listing.source_listing_id} | {comp.listing.building} | "
            f"{comp.listing.price_usd_month:,.0f} | {comp.score:.3f} | {comp.score_reasons} |"
        )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path
