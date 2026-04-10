from dataclasses import dataclass


@dataclass(frozen=True)
class SubjectProperty:
    property_id: str
    building: str
    neighborhood: str
    latitude: float
    longitude: float
    bedrooms: int
    bathrooms: float
    size_m2: float
    furnished: bool
    baseline_rent_usd_month: float


SUBJECT_PROPERTY = SubjectProperty(
    property_id="awa-playa-2x2-main",
    building="AWA",
    neighborhood="Playacar, Playa del Carmen",
    latitude=20.6275,
    longitude=-87.0815,
    bedrooms=2,
    bathrooms=2.0,
    size_m2=115.0,
    furnished=True,
    baseline_rent_usd_month=2500.0,
)

# Approximate FX for MVP. Replace with daily FX ingestion in production.
FX_TO_USD = {
    "USD": 1.0,
    "MXN": 0.058,  # 1 MXN -> USD
}

MIN_QUALITY_SCORE = 0.5
MIN_COMP_SCORE = 0.45
MAX_COMPS = 20
CONFIDENCE_MIN_FOR_RECOMMENDATION = 0.45
