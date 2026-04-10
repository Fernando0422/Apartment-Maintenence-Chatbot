from dataclasses import dataclass
from datetime import date


@dataclass
class RawListing:
    source: str
    source_listing_id: str
    url: str
    payload_json: str
    scraped_at: str


@dataclass
class CleanListing:
    raw_id: int
    source: str
    source_listing_id: str
    market_type: str
    building: str
    neighborhood: str
    latitude: float
    longitude: float
    bedrooms: int
    bathrooms: float
    size_m2: float
    furnished: bool
    price_usd_month: float
    first_seen_date: str
    last_seen_date: str
    quality_score: float
    is_duplicate: bool


@dataclass
class ScoredComp:
    listing: CleanListing
    score: float
    score_reasons: str


@dataclass
class Recommendation:
    subject_property_id: str
    run_date: date
    comp_count: int
    p25: float
    p50: float
    p75: float
    fast_rent: float
    balanced_rent: float
    premium_rent: float
    confidence_score: float
    baseline_rent: float
    underpricing_pct: float
    notes: str
