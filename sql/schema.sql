CREATE TABLE IF NOT EXISTS raw_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_listing_id TEXT NOT NULL,
    url TEXT,
    payload_json TEXT NOT NULL,
    scraped_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clean_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    source_listing_id TEXT NOT NULL,
    market_type TEXT NOT NULL,
    building TEXT,
    neighborhood TEXT,
    latitude REAL,
    longitude REAL,
    bedrooms INTEGER,
    bathrooms REAL,
    size_m2 REAL,
    furnished INTEGER NOT NULL DEFAULT 0,
    price_usd_month REAL NOT NULL,
    first_seen_date TEXT,
    last_seen_date TEXT,
    quality_score REAL NOT NULL,
    is_duplicate INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(raw_id) REFERENCES raw_listings(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_clean_unique_source_listing
    ON clean_listings(source, source_listing_id);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_property_id TEXT NOT NULL,
    run_date TEXT NOT NULL,
    comp_count INTEGER NOT NULL,
    p25 REAL,
    p50 REAL,
    p75 REAL,
    fast_rent REAL,
    balanced_rent REAL,
    premium_rent REAL,
    confidence_score REAL,
    baseline_rent REAL,
    underpricing_pct REAL,
    notes TEXT
);
