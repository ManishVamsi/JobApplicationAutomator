# Job Application Assistant

AI-powered multi-user web application that helps you discover, filter, and track jobs across multiple portals and LinkedIn, using an LLM to match postings against your resume.

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Frontend   │    │   Backend    │    │  Extension   │
│  React + TS  │───▶│   FastAPI    │◀───│  Chrome MV3  │
│  Tailwind v4 │    │  PostgreSQL  │    │  LinkedIn    │
│   Vite SPA   │    │    Redis     │    │  Detector    │
└──────────────┘    └──────────────┘    └──────────────┘
                          │
                    ┌─────┴─────┐
                    │  Groq LLM │  ← scoring runs in-process
                    │  JSearch  │    via BackgroundTasks
                    └───────────┘
                          ▲
                    External cron  ← triggers /admin/trigger-job-fetch
```

> **No separate worker process required.** Resume parsing and post scoring run
> as FastAPI `BackgroundTasks` inside the web process. Daily job fetching and
> monthly quota resets are triggered by external cron services (e.g.,
> cron-job.org, GitHub Actions) hitting protected admin endpoints. The Celery
> app/task files remain in the repo (`app/workers/`) unused, in case a future
> move to a real task queue is needed.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy (async), Alembic |
| **Database** | PostgreSQL 16, Redis 7 |
| **Frontend** | React 19, TypeScript, Vite 8, Tailwind CSS v4 |
| **LLM** | Groq API (Llama 3.3 70B) |
| **Jobs API** | JSearch (RapidAPI) |
| **Email** | Resend |
| **Background Tasks** | FastAPI BackgroundTasks + external cron (no Celery required) |
| **Auth** | Passwordless OTP + JWT (PyJWT) |
| **Extension** | Chrome Manifest V3 |

## Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- Node.js 18+

### 1. Start backend services
```bash
cd backend
cp .env.example .env  # Edit with your API keys
docker-compose up -d
```

### 2. Start frontend dev server
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### 3. Install the Chrome extension
1. Open `chrome://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked" → select the `extension/` directory
4. Click the extension icon → enter your backend URL and API token

## Project Structure

```
JobApplicationAutomator/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routers (auth, users, portals, jobs, linkedin, health, admin)
│   │   ├── core/          # Config, security, database, logging, middleware
│   │   ├── models/        # SQLAlchemy models (8 tables)
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   ├── services/      # Business logic (8 services) + background_tasks.py
│   │   └── workers/       # [UNUSED] Celery app + tasks (kept for future reference)
│   ├── db/migrations/     # Alembic migrations
│   ├── scripts/           # Operational scripts (key rotation)
│   ├── tests/             # pytest (15 tests)
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/    # AppShell, FilterBar, StatusBadge, ScoreBadge
│   │   ├── lib/           # Axios client, utilities
│   │   ├── pages/         # Login, JobList, JobSources, LinkedInPosts
│   │   └── store/         # Zustand auth store
│   ├── index.html
│   └── vite.config.ts
├── extension/
│   ├── manifest.json
│   ├── content.js         # LinkedIn post detector
│   ├── background.js      # API relay service worker
│   ├── popup.html/js      # Settings & status UI
│   └── icons/
└── docker-compose.yml
```

## Security

| Feature | Implementation |
|---------|---------------|
| **Auth** | Passwordless OTP (6-digit, 10min TTL, 5 failed guesses invalidates) |
| **JWT** | PyJWT with `type` claim enforcement (anti-confusion), 15min access TTL |
| **Refresh** | httpOnly cookie, CSRF proof via expired access token, env-conditional flags |
| **Credentials** | Envelope encryption (Fernet), per-user data keys, master key rotation script |
| **API Token** | SHA-256 hashed, revocable, `jaa_` prefix, last_used_at tracking |
| **Rate Limiting** | Redis sliding window: 60/min global, 5/min OTP, 30/min LinkedIn ingest |
| **CORS** | Exact origin (no wildcards), credentials=true |

## Environment Variables

```bash
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-secret-key
ENCRYPTION_MASTER_KEY=<Fernet.generate_key()>

# API Keys
GROQ_API_KEY=your-groq-key
JSEARCH_API_KEY=your-rapidapi-key
RESEND_API_KEY=your-resend-key

# Admin (for external cron triggers)
ADMIN_TRIGGER_SECRET=<openssl rand -hex 32>

# Optional
ENVIRONMENT=local|production
FRONTEND_URL=http://localhost:5173
```

## Operational Runbook

### ENCRYPTION_MASTER_KEY Rotation
```bash
# 1. Set the new key
export ENCRYPTION_MASTER_KEY_NEW=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 2. Run the rotation script
python -m backend.scripts.rotate_master_key

# 3. Swap keys in .env
# ENCRYPTION_MASTER_KEY=<new key>

# 4. Restart services
```

### Job Fetching (External Cron)

Daily job fetching is triggered by an external cron hitting the admin endpoint:
```bash
# Daily (e.g., 06:00 UTC via cron-job.org or GitHub Actions)
curl -X POST https://your-backend.onrender.com/api/v1/admin/trigger-job-fetch \
  -H "Authorization: Bearer $ADMIN_TRIGGER_SECRET"
```

### JSearch Quota Reset (External Cron)

Monthly quota reset (1st of each month):
```bash
curl -X POST https://your-backend.onrender.com/api/v1/admin/reset-jsearch-quota \
  -H "Authorization: Bearer $ADMIN_TRIGGER_SECRET"
```

### JSearch Quota
- Free tier: 200 requests/month
- Fetch runs once daily, max 6 requests per cycle
- Monthly usage tracked in Redis key `jsearch:monthly_usage`

## License

MIT
