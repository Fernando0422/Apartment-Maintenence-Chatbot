# Implementation Plan (MVP)

## Scope locked for first release

- One subject property profile (AWA, Playa del Carmen, 2/2)
- Long-term monthly rental segment only
- Local execution with deterministic sample data
- Daily market report generation

## Technical milestones

1. Define schema and contracts
2. Build ingestion adapter interface and sample adapter
3. Build normalization + dedupe + quality checks
4. Build comp scoring and recommendation engine
5. Build report generator
6. Add one-command runner

## Explicit constraints

- Recommendation only if confidence >= threshold.
- All pricing normalized to USD/month.
- Short-term listings excluded from long-term decision model.

## Critical pseudocode

```text
run_pipeline(subject_property):
    init_db()
    raw_records = fetch_all_sources()
    save_raw(raw_records)

    clean_records = []
    for raw in raw_records:
        normalized = normalize_listing(raw)
        if normalized.market_type != "long_term":
            continue
        if normalized.is_duplicate:
            continue
        if normalized.quality_score < MIN_QUALITY:
            continue
        save_clean(normalized)
        clean_records.append(normalized)

    comps = select_candidate_comps(clean_records, subject_property)
    scored = score_comps(comps, subject_property)
    top_comps = take_top(scored, n=20, min_score=COMP_MIN_SCORE)

    recommendation = build_recommendation(top_comps, subject_property)
    save_recommendation(recommendation)

    report_path = render_daily_report(subject_property, top_comps, recommendation)
    return report_path
```

## Success criteria

- Pipeline completes with exit code 0.
- Report generated with:
  - comp count
  - market median and quantiles
  - strategy rent bands
  - confidence and underpricing signal
