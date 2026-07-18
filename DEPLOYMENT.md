# Deployment Guide & Production Docker Configuration

This guide explains how to deploy the **Job Application Assistant** to production environments (Vercel for frontend, Render/Railway/Fly.io for backend, and hosted PostgreSQL and Redis instances).

---

## 1. Production Docker Configuration

The application uses a multi-stage `Dockerfile` optimized for minimal size (~120MB) and fast builds.

### 1.1 Backend Dockerfile (`backend/Dockerfile`)
The backend is packaged into a production-ready image.
```dockerfile
# Build stage
FROM python:3.12-alpine AS builder

WORKDIR /app

RUN apk add --no-cache build-base libffi-dev openssl-dev

COPY pyproject.toml .
RUN pip install --no-cache-dir --user .

# Production stage
FROM python:3.12-alpine AS runner

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Runs migrations automatically before starting the server
ENTRYPOINT ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

---

## 2. Infrastructure Setup

### 2.1 Database (PostgreSQL)
- Choose a hosted provider (Render, Supabase, Neon, AWS RDS, or Aiven).
- Enable TLS/SSL connections.
- Ensure your `DATABASE_URL` uses the `postgresql+asyncpg://` scheme.

### 2.2 Cache (Redis)
- Provision a hosted Redis server (Upstash, Render, RedisLabs).
- Enable persistence if rate limits and daily fetch states need to survive restarts.

---

## 3. Backend Deployment (Render / Fly.io)

### 3.1 Step-by-Step for Render
1. Create a new **Web Service** on Render.
2. Connect your Git repository.
3. Configure the environment:
   - **Environment:** `Docker`
   - **Plan:** Free / Starter
4. Add all environment variables (see below).
5. Render will automatically build the image using `backend/Dockerfile` and start the service.

---

## 4. Frontend Deployment (Vercel)

### 4.1 Step-by-Step for Vercel
1. Create a new project on Vercel.
2. Select the repository root.
3. Configure the directory settings:
   - Set **Root Directory** to `frontend`.
4. Configure Build & Development settings:
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
5. Configure Environment Variables:
   - `VITE_API_URL`: Set this to your deployed backend API URL (e.g., `https://jobapp-api.onrender.com/api/v1`).
6. Click **Deploy**. Vercel will build and serve your static React bundle.

---

## 5. Required Environment Variables (Production)

| Variable | Example / Value | Description |
|----------|-----------------|-------------|
| `ENVIRONMENT` | `production` | Enables cookie secure flags and restricts API docs |
| `DATABASE_URL` | `postgresql+asyncpg://user:password@host/database` | Async PostgreSQL link |
| `REDIS_URL` | `rediss://...` | Secure Redis connection URI |
| `JWT_SECRET_KEY` | *generated 256-bit string* | Token encryption secret |
| `ENCRYPTION_MASTER_KEY` | *generated Fernet key* | Master key for user keys |
| `GROQ_API_KEY` | `gsk_...` | Groq LLM API Key |
| `JSEARCH_API_KEY` | *RapidAPI key* | JSearch endpoint key |
| `RESEND_API_KEY` | `re_...` | Email delivery API Key |
| `RESEND_FROM_EMAIL` | `noreply@yourdomain.com` | Verified sender domain address |
| `ADMIN_TRIGGER_SECRET` | *random hex string* | Protection token for cron tasks |
| `FRONTEND_URL` | `https://your-app.vercel.app` | Required for CORS strict matches |

---

## 6. Daily Scheduling via External Cron

Since Celery has been removed to run the system in a single-process container, scheduling is handled by external HTTPS cron requests.

### 6.1 Set Up Daily Fetch (e.g., via cron-job.org)
1. Register on [cron-job.org](https://cron-job.org).
2. Create a new cron job:
   - **URL:** `https://your-backend.onrender.com/api/v1/admin/trigger-job-fetch`
   - **Method:** `POST`
   - **Schedule:** Everyday at 06:00 UTC (or your preferred time)
   - **Headers:** `Authorization: Bearer <ADMIN_TRIGGER_SECRET>`

### 6.2 Set Up Monthly Quota Reset
1. Create a second cron job on cron-job.org:
   - **URL:** `https://your-backend.onrender.com/api/v1/admin/reset-jsearch-quota`
   - **Method:** `POST`
   - **Schedule:** 1st day of every month at 00:00 UTC
   - **Headers:** `Authorization: Bearer <ADMIN_TRIGGER_SECRET>`
