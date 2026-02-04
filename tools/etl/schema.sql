-- schema.sql
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS providers (
  provider_id       TEXT PRIMARY KEY,            -- canonical key = ukprn if present, else stable hash
  ukprn             TEXT,                        -- 8-digit if available
  name              TEXT NOT NULL,
  website           TEXT,
  email             TEXT,
  phone             TEXT,
  address           TEXT,
  postcode          TEXT,
  lat               REAL,
  lon               REAL,
  country           TEXT,                        -- 'ENG','WLS','SCT','NIR' when known
  provider_type     TEXT,                        -- FE college, sixth form, independent SPI, ILP etc.
  is_residential    INTEGER DEFAULT 0,           -- 0/1 based on s41 text and later enrichment
  is_specialist     INTEGER DEFAULT 0,           -- non-residential specialist flags (GIAS or s41)
  s41_approved      INTEGER DEFAULT 0,           -- 0/1 from Section 41 list
  ofsted_urn        TEXT,                        -- optional enrichment
  ofsted_url        TEXT,                        -- optional enrichment
  source_flags      TEXT,                        -- JSON: {ncs:true, s41:true, gias:true}
  first_seen_utc    TEXT,
  last_seen_utc     TEXT
);

CREATE INDEX IF NOT EXISTS idx_providers_postcode ON providers(postcode);
CREATE INDEX IF NOT EXISTS idx_providers_latlon ON providers(lat, lon);
CREATE INDEX IF NOT EXISTS idx_providers_res ON providers(is_residential,s41_approved);

CREATE TABLE IF NOT EXISTS geocodes (
  postcode_key  TEXT PRIMARY KEY,  -- uppercase, no spaces
  postcode      TEXT,
  lat           REAL,
  lon           REAL,
  terminated    INTEGER DEFAULT 0,
  meta_json     TEXT,
  last_updated_utc TEXT
);
