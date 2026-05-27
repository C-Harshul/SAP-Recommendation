-- Experience Garage recommendation engine — silver & gold tables
-- Requires: CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- Produced by continuous market-trends enrichment (not weekly graph)
CREATE TABLE IF NOT EXISTS gold.trend_signals (
    trend_id TEXT PRIMARY KEY,
    theme TEXT,
    summary TEXT,
    evidence_urls TEXT[],
    source_count INT,
    momentum TEXT CHECK (momentum IN ('rising', 'stable', 'fading')),
    novelty TEXT CHECK (novelty IN ('new', 'emerging', 'established')),
    first_seen TIMESTAMPTZ,
    peak_week DATE,
    embedding VECTOR(1024),
    last_updated TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_trend_signals_embedding
    ON gold.trend_signals USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Stage 2: extracted ideas
CREATE TABLE IF NOT EXISTS silver.extracted_ideas (
    idea_id TEXT PRIMARY KEY,
    source_type TEXT CHECK (source_type IN ('interview', 'community')),
    source_id TEXT,
    pain_point TEXT,
    proposed_solution TEXT,
    evidence_quotes JSONB,
    sentiment TEXT,
    specificity TEXT CHECK (specificity IN ('vague', 'specific', 'actionable')),
    embedding VECTOR(1024),
    extracted_at TIMESTAMPTZ,
    prompt_version TEXT
);

-- Stage 3: synthesized solutions
CREATE TABLE IF NOT EXISTS silver.candidate_solutions (
    solution_id TEXT PRIMARY KEY,
    problem_id TEXT REFERENCES silver.extracted_ideas (idea_id),
    solution_text TEXT,
    approach TEXT,
    origin TEXT CHECK (origin IN ('user_proposed', 'llm_synthesized')),
    inspired_by TEXT[],
    embedding VECTOR(1024),
    generated_at TIMESTAMPTZ,
    prompt_version TEXT
);

-- Stage 4: clusters
CREATE TABLE IF NOT EXISTS gold.idea_clusters (
    cluster_id TEXT PRIMARY KEY,
    canonical TEXT,
    source_count INT,
    evidence_ids TEXT[],
    embedding VECTOR(1024),
    first_seen TIMESTAMPTZ,
    last_updated TIMESTAMPTZ
);

-- Stages 6–7: ranked missions
CREATE TABLE IF NOT EXISTS gold.ranked_missions (
    mission_id TEXT PRIMARY KEY,
    cluster_id TEXT REFERENCES gold.idea_clusters (cluster_id),
    rank INT,
    source_count FLOAT,
    source_diversity FLOAT,
    recency FLOAT,
    specificity FLOAT,
    signal_urgency FLOAT,
    market_validation FLOAT,
    feasibility FLOAT,
    sap_relevance FLOAT,
    novelty FLOAT,
    effort_score FLOAT,
    impact_score FLOAT,
    final_score FLOAT,
    weights_version TEXT,
    writeup TEXT,
    related_trend_ids TEXT[],
    trace_id TEXT,
    prompt_version TEXT,
    generated_at TIMESTAMPTZ
);

-- Pipeline cache metadata (v0 uses EG_PIPELINE_CACHE_DIR JSON files; optional Postgres mirror)
CREATE TABLE IF NOT EXISTS gold.pipeline_runs (
    input_fingerprint TEXT PRIMARY KEY,
    config_fingerprint TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    prompt_version TEXT,
    weights_version TEXT,
    git_sha TEXT,
    interviews_count INT,
    community_count INT,
    trends_count INT,
    missions_count INT,
    snapshot_json JSONB
);

CREATE TABLE IF NOT EXISTS silver.processed_sources (
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    extract_stage_fingerprint TEXT NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL,
    ideas_json JSONB,
    PRIMARY KEY (source_type, source_id, content_hash, extract_stage_fingerprint)
);
