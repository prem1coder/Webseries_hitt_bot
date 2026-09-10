# 🎬 Webseries Hitt Bot (`Webseries_hitt_bot`)

> **Telegram Video Search, Dynamic Navigation & Secure Web Download System**  
> Source-of-Truth Architecture built with **Python 3.12+**, **aiogram v3**, **Telethon (MTProto)**, **PostgreSQL 17**, and **FastAPI**.

---

## 📌 Project Overview

**Webseries Hitt Bot** is an authorized search, browsing, and download gateway for private Telegram video libraries:
* **Zero VPS Storage Footprint**: Video files remain securely hosted in Telegram's cloud. The VPS only stores metadata and channel/message identifiers.
* **Efficient Exact-Title Search**: User queries hit indexed PostgreSQL tables with fast normalized title matching.
* **Dynamic Multi-Resolution Navigation**: Only seasons, episodes, and qualities (`480p`, `720p`, `1080p`, `2160p/4K`) that actually exist in the database are rendered as interactive buttons, sorted by numeric resolution descending.
* **Fail-Closed Mandatory Membership**: Users are verified as channel subscribers before generating download capabilities. API errors or invalid channel IDs deny access.
* **Cryptographically Signed Expiring Links**: Generates HMAC-SHA256 URL-safe expiring tokens for web streaming & download with strict schema validation, clock-skew tolerance, and TTL bounds.
* **Direct MTProto Streaming with Range Support**: Supports HTML5 video streaming with full HTTP Range resume support (HTTP 206 Partial Content, RFC 7233 / RFC 9110 compliant HTTP 416 handling) and concurrency limits to protect VPS bandwidth.
* **Idempotent Real-time Live Sync**: Automatically indexes newly posted videos in real-time via Telethon event listeners with race-safe database savepoints.

---

## 🏗️ Architecture Flow

```
[ Telegram Private Archive ]
            │ (MTProto Scrape / Live Event)
            ▼
   [ Telethon Indexer ] ──► [ Filename Parser ] ──► [ PostgreSQL 17 DB ]
                                                            │
[ Telegram User ] ◄──► [ aiogram v3 Bot ] ◄─────────────────┤ (Normalized Title Search)
        │                      │
        │                      ▼
        │             [ Channel Membership Check ]
        │                      │
        │                      ▼ (Generates Signed Token)
        │
        ▼ (Clicks Web Link)
[ FastAPI Web Portal ] ──► [ MTProto Chunk Streamer ] ──► [ Browser Stream / Download ]
```

---

## 🗄️ Relational Database Schema

**Authoritative Production Source of Truth**: [`database/init/001_schema.sql`](file:///e:/Webseries_hitt_bot/database/init/001_schema.sql)

```sql
contents (id, title, normalized_title, content_type, year, original_title, poster_url, description)
  │  CONSTRAINT uq_contents_identity UNIQUE (normalized_title, content_type, year)
  │
  ├──► seasons (id, content_id, season_number, title)
  │      │  CONSTRAINT uq_seasons_content_season UNIQUE (content_id, season_number)
  │      │
  │      └──► episodes (id, season_id, episode_number, title, normalized_title, duration_seconds)
  │             │  CONSTRAINT uq_episodes_season_episode UNIQUE (season_id, episode_number)
  │             │
  │             └──► files (id, content_id, episode_id, quality, file_name, file_size_bytes, duration_seconds, audio, telegram_channel_id, telegram_message_id)
  │                    CONSTRAINT uq_files_telegram_message UNIQUE (telegram_channel_id, telegram_message_id)
  │
  └──► files (movie direct quality links)
```

---

## 🚀 Local & Production Execution Sequence

### Step 1: Clean Deployment Archive
Remove `.env`, `.venv`, `.git`, caches, nested archives, and session files from deployable archives. Verify no secrets or credentials exist in public source archives.

### Step 2: Environment Configuration
Copy `.env.example` to `.env` and configure credentials:
```bash
cp .env.example .env
```
Ensure all variables are populated before starting services. When `ENVIRONMENT=production`, strict startup validation will fail fast if credentials, secrets, or channel IDs are invalid or default.

### Step 3: Database Bootstrap
Start PostgreSQL and initialize the schema via `database/init/001_schema.sql`:
```bash
docker compose up -d postgres
```
Runtime services do not implicitly mutate or create schema tables in production; `001_schema.sql` is the single authority.

### Step 4: Telethon Authentication (One-Time Setup)
Create separate authenticated archive and stream sessions interactively:
```bash
python -m indexer.telegram.login
```

### Step 5: Run Automated Tests
Verify all unit and integration tests pass in a clean Python 3.12 virtual environment:
```bash
pytest -v
```

### Step 6: Historical Indexing (Controlled One-Off Job)
Index past messages from your archive channel as a deliberate one-time setup:
```bash
python -m indexer.main
```

### Step 7: Start Live Listener & Services
- **Start Real-time Upload Listener**:
  ```bash
  python -m indexer.listener
  ```
- **Start Telegram Bot**:
  ```bash
  python -m bot.main
  ```
- **Start Web Download & Streaming Portal**:
  ```bash
  python -m web.main
  ```

---

## 🧪 Automated Test Suite

The test suite runs with pytest and verifies all 66 test cases across parser logic, security constraints, membership gates, token cryptography, HTTP Range semantics, and database idempotency:

```bash
python -m pytest -v
```

**Results:**
```
66 passed in 8.10s (100% pass rate)
```

---

## 🔒 Security Approvals & Implementation Standards

1. **No Secrets in Source**: `.env` and `*.session` are strictly ignored by `.gitignore` and `.dockerignore`.
2. **Fail-Closed Membership Check**: If `MAIN_CHANNEL_ID` is missing, misconfigured as a URL, or the Telegram API check fails, access is denied.
3. **Hardened Token Cryptography**: Versioned (`v: 1`), typed (`typ: "download"`), positive integer IDs, lifetime-capped, future-`iat` rejected (>60s clock skew), and verified with constant-time HMAC-SHA256 comparison.
4. **Range & Suffix Semantics**: HTTP Range requests support single byte ranges, suffix ranges (`bytes=-500`), and RFC-compliant HTTP 416 responses for unsatisfiable ranges.
5. **Streaming Concurrency Protection**: Stream requests use an `asyncio.Semaphore` bounded by `MAX_CONCURRENT_STREAMS` to safeguard VPS bandwidth and CPU.
6. **Non-Root Containers**: Docker containers run under unprivileged user `appuser`.
7. **Database Concurrency & Savepoints**: Concurrent indexer jobs use per-message transaction savepoints (`begin_nested()`) and retry logic to guarantee idempotency.

---

## 📄 License
Source code developed for **Webseries Hitt Bot** (`Webseries_hitt_bot`).
