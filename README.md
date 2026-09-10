# 🎬 Webseries Hitt Bot (`Webseries_hitt_bot`)

> **High-Performance Telegram Video Search, Dynamic Navigation & Secure Web Download System**  
> Source-of-Truth Architecture built with **Python 3.12**, **aiogram v3**, **Telethon (MTProto)**, **PostgreSQL 17**, and **FastAPI**.

---

## 📌 Project Overview

**Webseries Hitt Bot** is an authorized search, browsing, and download gateway for private Telegram video libraries:
* **Zero VPS Storage Footprint**: Video files remain securely hosted in Telegram's cloud. The VPS only stores metadata and channel/message identifiers.
* **Instantaneous Search**: User queries hit indexed PostgreSQL tables with sub-millisecond response times.
* **Dynamic Multi-Resolution Navigation**: Only seasons, episodes, and qualities (`480p`, `720p`, `1080p`, `2160p/4K`) that actually exist in the database are rendered as interactive buttons.
* **Mandatory Channel Membership**: Users are verified as channel subscribers before generating download links.
* **Cryptographically Signed Expiring Links**: Generates HMAC-SHA256 URL-safe expiring tokens for web streaming & download.
* **Real-time Live Sync**: Automatically indexes newly posted videos in real-time via Telethon event listeners.

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

```sql
contents (id, title, normalized_title, content_type, year, original_title, poster_url, description)
  │
  ├──► seasons (id, content_id, season_number, title)
  │      │
  │      └──► episodes (id, season_id, episode_number, title, normalized_title, duration_seconds)
  │             │
  │             └──► files (id, content_id, episode_id, quality, file_name, file_size_bytes, duration_seconds, audio, telegram_channel_id, telegram_message_id)
  │
  └──► files (movie direct quality links)
```

---

## 🚀 Quick Start & Setup Guide

### 1. Prerequisites
- Python 3.12+
- Docker Desktop / Docker Engine & Docker Compose
- Git

### 2. Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/prem1coder/Webseries_hitt_bot.git
cd Webseries_hitt_bot

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables (`.env`)
Create your `.env` configuration by copying `.env.example`:

```bash
# On Linux / macOS:
cp .env.example .env

# On Windows PowerShell:
Copy-Item .env.example .env
```

Open `.env` and fill in your credentials:

| Variable | Description | Source / Notes |
| :--- | :--- | :--- |
| `BOT_TOKEN` | Telegram Bot API Token | Obtained from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_API_ID` | Telegram MTProto API ID | Obtained from [my.telegram.org](https://my.telegram.org) |
| `TELEGRAM_API_HASH` | Telegram MTProto API Hash | Obtained from [my.telegram.org](https://my.telegram.org) |
| `TELEGRAM_SESSION_NAME` | MTProto Session Name | Default: `archive_indexer` |
| `ARCHIVE_CHANNEL_ID` | Target Telegram Archive Channel ID or Invite Link | Your private video repository channel |
| `MAIN_CHANNEL_ID` | Main Telegram Channel ID or Invite Link | Channel required for mandatory subscription check |
| `MAIN_CHANNEL_INVITE_LINK` | Invite link shown to users who need to join | Channel invite link |
| `DATABASE_URL` | PostgreSQL Async Connection String | Format: `postgresql+asyncpg://user:password@host:5432/dbname` |
| `DOWNLOAD_SECRET` | Secure random 32+ character signing key | Generated secret string (e.g. `openssl rand -hex 32`) |
| `TOKEN_EXPIRY_MINUTES` | Validity period of signed download links | Default: `15` |
| `DOMAIN` | Domain or host running the download portal | e.g. `localhost:8000` or `yourdomain.com` |

### 4. Start Local PostgreSQL Database
```bash
docker compose up -d postgres
```

### 5. Telethon Authentication (One-Time Setup)
Run the interactive login script once to authorize your Telegram account:
```bash
python -m indexer.telegram.login
```

### 6. Run Historical Archive Crawler (Optional)
To index all past messages from your private archive channel:
```bash
python -m indexer.main
```

### 7. Start Services
- **Run Telegram Bot**:
  ```bash
  python -m bot.main
  ```
- **Run FastAPI Download & Streaming Portal**:
  ```bash
  python -m web.main
  ```
- **Run Real-time Upload Listener**:
  ```bash
  python -m indexer.listener
  ```

---

## 🧪 Running Automated Tests

```bash
# Run filename parser tests
python -m pytest tests/test_parser.py -v

# Or run with standard unittest runner:
python tests/test_parser_unittest.py
python tests/test_token_unittest.py
python tests/test_search_unittest.py
```

---

## 🐳 Production VPS Deployment (Docker Compose)

### 1. Build and Start Full Multi-Container Stack
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 2. Configure Nginx Reverse Proxy & SSL
Copy `nginx/nginx.conf` to `/etc/nginx/sites-available/webseries_hitt_bot` and enable it:
```bash
sudo ln -s /etc/nginx/sites-available/webseries_hitt_bot /etc/nginx/sites-enabled/
sudo certbot --nginx -d yourdomain.com
sudo systemctl reload nginx
```

---

---

## 🔒 Security & Performance Best Practices
1. **Never commit `.env` or session files (`*.session`)**: Kept in `.gitignore` and `.dockerignore`.
2. **Fail-Closed Membership Verification**: If `MAIN_CHANNEL_ID` is missing, misconfigured as a URL, or if the Telegram API check fails, access is denied.
3. **Hardened HMAC-SHA256 Tokens**: Versioned (`v: 1`), typed (`typ: "download"`), positive integer IDs, lifetime-capped, and verified with constant-time comparison.
4. **Chunked MTProto Streaming**: Web player reads video byte ranges on demand, preventing RAM spikes and avoiding disk storage on VPS.
5. **Separated Telethon Sessions**: Indexer and Web services use independent `.session` files to prevent SQLite database lock contention.
6. **Non-Root Containers**: Docker containers run under unprivileged user `appuser`.
7. **Parameterized SQL & Connection Pooling**: Prevents SQL injection and maximizes concurrent database throughput.

---

## 🚦 Production Approval Gates

Before VPS deployment, ensure all gates pass:
- [x] No exposed or real credentials in GitHub repository.
- [x] `.env` and `*.session` excluded via `.gitignore` and `.dockerignore`.
- [x] Docker images run as non-root (`appuser`) without embedded secrets.
- [x] Database schema initializes cleanly via `001_schema.sql`.
- [x] All 44 automated unit & security tests pass.
- [x] Exact normalized title search matches V1 requirements.
- [x] Series season packs handled safely without creating fake E01 episodes.
- [x] Non-member cannot receive download tokens; API failures deny access.
- [x] Web endpoints reject tampered or expired tokens.
- [x] Web streaming runs through a dedicated authenticated session.

---

## 📄 License
Source code developed for **Webseries Hitt Bot** (`Webseries_hitt_bot`).
