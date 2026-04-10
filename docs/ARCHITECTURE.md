# Playa Rental Market Automation MVP

## Objective

Produce a daily recommendation for the next listing cycle of a specific property:

- Property: AWA Playa del Carmen condo
- Segment: long-term rentals only (monthly)
- Unit type: 2 bed / 2 bath
- Baseline lease: 2,500 USD/month

The system is designed to answer:

1. Where the market is today
2. Whether the baseline is likely under market
3. A suggested price band with confidence

## MVP Architecture

Single repository, single runtime, single SQLite database:

1. **Ingestion Layer**
   - Reads raw listing payloads from source adapters
   - Stores immutable records in `raw_listings`
2. **Cleaning & Normalization Layer**
   - Standardizes currency/period to USD/month
   - Normalizes neighborhood/building names
   - Classifies segment (`long_term` / `short_term`)
   - Applies quality flags and dedupe
   - Writes to `clean_listings`
3. **Comparable Scoring Layer**
   - Filters by segment, location, and unit spec
   - Scores similarity to subject property
   - Prefers same-building comparables
4. **Recommendation Layer**
   - Computes P25/P50/P75 from weighted comps
   - Produces strategy bands: fast, balanced, premium
   - Computes confidence score and underpricing signal
   - Stores in `recommendations`
5. **Reporting Layer**
   - Generates a markdown daily report to `data/reports/`
   - Summarizes market movement, comp set, recommendation, confidence

## Data Flow

1. `sample_listings.json` (or future live connectors) -> `raw_listings`
2. `raw_listings` -> normalize/classify -> `clean_listings`
3. `clean_listings` -> similarity scoring -> in-memory comp set
4. comp set -> recommendation metrics -> `recommendations`
5. recommendation + comps -> markdown report

## Why this architecture first

- Keeps delivery fast while preserving production migration path.
- Enforces data contracts and traceability from day one.
- Avoids premature microservice complexity.

## Production upgrade path

When scaling:

- Replace JSON adapter with scheduled crawlers/APIs.
- Replace SQLite with Postgres (`raw`, `clean`, `analytics` schemas).
- Add orchestration (n8n/Prefect/Airflow) and alerting.
- Add source reliability scoring and automated QA gates.
