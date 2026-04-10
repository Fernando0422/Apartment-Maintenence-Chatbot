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

Run with explicit mode:

```bash
python3 scripts/run_pipeline.py --mode sample
python3 scripts/run_pipeline.py --mode live
python3 scripts/run_pipeline.py --mode hybrid
```

Modes:
- `sample`: uses only local sample seed sources
- `live`: uses only live-enabled connectors from `config/sources.json`
- `hybrid`: combines both

## Live connector configuration

Edit `config/sources.json`:

- enable or disable each source (`"enabled": true/false`)
- choose source type (`sample`, `http_json`)
- map which modes can run it (`"modes": ["live"]`, etc.)

Example live source:

```json
{
  "name": "my_live_feed",
  "type": "http_json",
  "enabled": true,
  "modes": ["live", "hybrid"],
  "url": "https://my-feed.example.com/listings.json",
  "timeout_seconds": 20,
  "headers": {
    "User-Agent": "PlayaRentalAutomationMVP/1.0"
  }
}
```

Expected response format:
- JSON array of listing objects, or
- JSON object containing `listings: []`

Each listing must include at minimum:
- `source_listing_id`
- `price`
- `currency` (`USD` or `MXN`)
- `period` (`night`, `week`, or `month`)
- `market_type` (`long_term` or `short_term`)

## Notes

- This MVP intentionally uses local sample data for deterministic behavior.
- To move to production:
  - keep adding source-specific connectors under `src/automation/connectors/`
  - replace SQLite with Postgres
  - schedule the runner 1-2 times per day
  - route ops alerts to email/Slack/WhatsApp

## Scheduler setup

Scheduler-friendly wrapper:

```bash
./scripts/run_scheduled.sh hybrid
```

Cron example (UTC 08:00 and 20:00):

```cron
0 8,20 * * * cd /workspace && /workspace/scripts/run_scheduled.sh hybrid
```

Operational logs are written alongside reports:
- `data/reports/*.ops.log`
