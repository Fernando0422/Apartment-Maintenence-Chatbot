import math
import statistics
from datetime import date

from .config import (
    CONFIDENCE_MIN_FOR_RECOMMENDATION,
    MAX_COMPS,
    MIN_COMP_SCORE,
    SUBJECT_PROPERTY,
    SubjectProperty,
)
from .db import get_connection
from .models import CleanListing, Recommendation, ScoredComp


def _fetch_candidate_comps(scraped_at: str | None = None) -> list[CleanListing]:
    with get_connection() as conn:
        if scraped_at:
            rows = conn.execute(
                """
                SELECT
                    c.raw_id, c.source, c.source_listing_id, c.market_type, c.building, c.neighborhood,
                    c.latitude, c.longitude, c.bedrooms, c.bathrooms, c.size_m2, c.furnished,
                    c.price_usd_month, c.first_seen_date, c.last_seen_date, c.quality_score, c.is_duplicate
                FROM clean_listings c
                JOIN raw_listings r ON r.id = c.raw_id
                WHERE
                    c.market_type = 'long_term'
                    AND c.is_duplicate = 0
                    AND r.scraped_at = ?
                """,
                (scraped_at,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT
                    raw_id, source, source_listing_id, market_type, building, neighborhood,
                    latitude, longitude, bedrooms, bathrooms, size_m2, furnished,
                    price_usd_month, first_seen_date, last_seen_date, quality_score, is_duplicate
                FROM clean_listings
                WHERE market_type = 'long_term' AND is_duplicate = 0
                """
            ).fetchall()
    comps: list[CleanListing] = []
    for row in rows:
        comps.append(
            CleanListing(
                raw_id=int(row["raw_id"]),
                source=row["source"],
                source_listing_id=row["source_listing_id"],
                market_type=row["market_type"],
                building=row["building"],
                neighborhood=row["neighborhood"],
                latitude=float(row["latitude"] or 0),
                longitude=float(row["longitude"] or 0),
                bedrooms=int(row["bedrooms"] or 0),
                bathrooms=float(row["bathrooms"] or 0),
                size_m2=float(row["size_m2"] or 0),
                furnished=bool(row["furnished"]),
                price_usd_month=float(row["price_usd_month"]),
                first_seen_date=row["first_seen_date"],
                last_seen_date=row["last_seen_date"],
                quality_score=float(row["quality_score"]),
                is_duplicate=bool(row["is_duplicate"]),
            )
        )
    return comps


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _subject_coordinates(subject: SubjectProperty) -> tuple[float, float]:
    return subject.latitude, subject.longitude


def _score_comp(comp: CleanListing, subject: SubjectProperty) -> ScoredComp:
    reasons: list[str] = []
    score = 0.0

    if comp.building.strip().lower() == subject.building.strip().lower():
        score += 0.35
        reasons.append("same_building")

    if comp.neighborhood.strip().lower() == subject.neighborhood.strip().lower():
        score += 0.2
        reasons.append("same_neighborhood")

    bed_delta = abs(comp.bedrooms - subject.bedrooms)
    score += max(0.0, 0.15 - (bed_delta * 0.08))
    reasons.append(f"bed_delta={bed_delta}")

    bath_delta = abs(comp.bathrooms - subject.bathrooms)
    score += max(0.0, 0.1 - (bath_delta * 0.05))
    reasons.append(f"bath_delta={bath_delta:.1f}")

    size_delta_pct = abs(comp.size_m2 - subject.size_m2) / max(subject.size_m2, 1.0)
    score += max(0.0, 0.1 - size_delta_pct * 0.2)
    reasons.append(f"size_delta_pct={size_delta_pct:.2f}")

    if comp.furnished == subject.furnished:
        score += 0.05
        reasons.append("furnished_match")

    subject_lat, subject_lon = _subject_coordinates(subject)
    dist = _distance_km(subject_lat, subject_lon, comp.latitude, comp.longitude)
    dist_bonus = max(0.0, 0.05 - (dist * 0.02))
    score += dist_bonus
    reasons.append(f"distance_km={dist:.2f}")

    score = max(0.0, min(score, 1.0))
    return ScoredComp(listing=comp, score=score, score_reasons=", ".join(reasons))


def _quantile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = (len(sorted_vals) - 1) * q
    low = math.floor(idx)
    high = math.ceil(idx)
    if low == high:
        return sorted_vals[low]
    frac = idx - low
    return sorted_vals[low] * (1.0 - frac) + sorted_vals[high] * frac


def _confidence(scored: list[ScoredComp]) -> float:
    if not scored:
        return 0.0
    avg_score = statistics.mean(x.score for x in scored)
    comp_depth = min(len(scored) / 12.0, 1.0)
    return round((avg_score * 0.7) + (comp_depth * 0.3), 3)


def generate_recommendation(
    subject: SubjectProperty = SUBJECT_PROPERTY,
    scraped_at: str | None = None,
) -> tuple[Recommendation, list[ScoredComp]]:
    comps = _fetch_candidate_comps(scraped_at=scraped_at)
    scored = [_score_comp(comp, subject) for comp in comps]
    filtered = [x for x in scored if x.score >= MIN_COMP_SCORE]
    filtered.sort(key=lambda x: x.score, reverse=True)
    top = filtered[:MAX_COMPS]

    prices = sorted([x.listing.price_usd_month for x in top])
    p25 = round(_quantile(prices, 0.25), 2)
    p50 = round(_quantile(prices, 0.50), 2)
    p75 = round(_quantile(prices, 0.75), 2)
    conf = _confidence(top)

    if conf < CONFIDENCE_MIN_FOR_RECOMMENDATION or not prices:
        note = "Insufficient confidence for strong recommendation."
        fast = balanced = premium = 0.0
        underpricing = 0.0
    else:
        fast = round(p25, 2)
        balanced = round(p50, 2)
        premium = round(p75, 2)
        underpricing = round(((balanced - subject.baseline_rent_usd_month) / subject.baseline_rent_usd_month) * 100.0, 2)
        note = "Recommendation generated from long-term comparable set."

    rec = Recommendation(
        subject_property_id=subject.property_id,
        run_date=date.today(),
        comp_count=len(top),
        p25=p25,
        p50=p50,
        p75=p75,
        fast_rent=fast,
        balanced_rent=balanced,
        premium_rent=premium,
        confidence_score=conf,
        baseline_rent=subject.baseline_rent_usd_month,
        underpricing_pct=underpricing,
        notes=note,
    )
    _save_recommendation(rec)
    return rec, top


def _save_recommendation(rec: Recommendation) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO recommendations (
                subject_property_id, run_date, comp_count, p25, p50, p75,
                fast_rent, balanced_rent, premium_rent, confidence_score,
                baseline_rent, underpricing_pct, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec.subject_property_id,
                rec.run_date.isoformat(),
                rec.comp_count,
                rec.p25,
                rec.p50,
                rec.p75,
                rec.fast_rent,
                rec.balanced_rent,
                rec.premium_rent,
                rec.confidence_score,
                rec.baseline_rent,
                rec.underpricing_pct,
                rec.notes,
            ),
        )
