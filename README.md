# Playa Rental Market Automation (MVP)

This repository now includes a runnable MVP pipeline that automates daily rental market monitoring for a specific property profile:

- Building: AWA Playa del Carmen
- Unit profile: 2 bed / 2 bath
- Segment: long-term monthly rentals only
- Baseline lease: 2,500 USD/month

## What it does

1. Ingests raw listing data (sample data for MVP)
2. Normalizes listings to USD/month
3. Filters to long-term comps and scores comparables
4. Produces strategy recommendations (fast, balanced, premium)
5. Generates a daily markdown report in `data/reports/`

## Project structure

- `docs/ARCHITECTURE.md` - system architecture and data flow
- `docs/IMPLEMENTATION_PLAN.md` - practical implementation sequence and pseudocode
- `sql/schema.sql` - database schema
- `src/automation/` - pipeline modules
- `scripts/run_pipeline.py` - one-command pipeline runner
- `data/sample_listings.json` - deterministic MVP input dataset

## Run

```bash
python3 scripts/run_pipeline.py
```

You should see output like:

```text
Pipeline completed. Report generated: /workspace/data/reports/market_report_YYYYMMDD.md
```

## Notes

- This MVP intentionally uses local sample data for deterministic behavior.
- To move to production:
  - replace sample data adapter with source-specific connectors
  - replace SQLite with Postgres
  - schedule the runner 1-2 times per day
  - add alerting and data quality checks
