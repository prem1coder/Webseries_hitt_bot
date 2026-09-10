-- ==============================================================================
-- Telegram Video Search & Download Bot - Schema Definition (001_schema.sql)
-- Source of Truth: PostgreSQL 17 relational schema
-- ==============================================================================

-- 1. Contents Table (one row per movie or series)
CREATE TABLE IF NOT EXISTS contents (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    content_type VARCHAR(20) NOT NULL CHECK (content_type IN ('movie', 'series')),
    year SMALLINT,
    original_title TEXT,
    poster_url TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Seasons Table (for series)
CREATE TABLE IF NOT EXISTS seasons (
    id BIGSERIAL PRIMARY KEY,
    content_id BIGINT NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    season_number SMALLINT NOT NULL,
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(content_id, season_number)
);

-- 3. Episodes Table (episodes within seasons)
CREATE TABLE IF NOT EXISTS episodes (
    id BIGSERIAL PRIMARY KEY,
    season_id BIGINT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    episode_number SMALLINT NOT NULL,
    title TEXT,
    normalized_title TEXT,
    duration_seconds INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(season_id, episode_number)
);

-- 4. Files Table (each quality/version and Telegram message reference)
CREATE TABLE IF NOT EXISTS files (
    id BIGSERIAL PRIMARY KEY,
    content_id BIGINT NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    episode_id BIGINT REFERENCES episodes(id) ON DELETE CASCADE,
    quality VARCHAR(20),
    file_name TEXT,
    file_size_bytes BIGINT,
    duration_seconds INTEGER,
    audio TEXT,
    telegram_channel_id BIGINT NOT NULL,
    telegram_message_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(telegram_channel_id, telegram_message_id)
);

-- 5. Indexes for fast normalized search & multi-quality resolution
CREATE INDEX IF NOT EXISTS idx_contents_normalized_title ON contents(normalized_title);
CREATE INDEX IF NOT EXISTS idx_files_content_quality ON files(content_id, quality);
CREATE INDEX IF NOT EXISTS idx_files_episode_quality ON files(episode_id, quality);
CREATE UNIQUE INDEX IF NOT EXISTS idx_telegram_message_unique ON files(telegram_channel_id, telegram_message_id);
