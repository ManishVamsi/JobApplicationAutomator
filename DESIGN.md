# Architectural & Design Specifications

This document details the architectural decisions, design patterns, security controls, database schema, and LLM orchestration flow for the **Job Application Assistant**.

---

## 1. System Architecture

```
                               ┌────────────────────────────────────────────────────────┐
                               │                     User Browser                       │
                               │                                                        │
                               │  ┌────────────────────────┐    ┌────────────────────┐  │
                               │  │   Vite + React SPA     │    │ Chrome Extension   │  │
                               │  │   (Tailwind CSS v4)    │    │ (Manifest V3)      │  │
                               │  └────────────────────────┘    └────────────────────┘  │
                               └──────────────┬────────────────────────────┬────────────┘
                                              │ HTTP                       │ HTTP (API Token)
                                              ▼                            ▼
                               ┌────────────────────────────────────────────────────────┐
                               │                    FastAPI Backend                     │
                               │                                                        │
                               │  ┌────────────────────────┐    ┌────────────────────┐  │
                               │  │    REST API Routers    │───▶│  BackgroundTasks   │  │
                               │  │  (Auth, Jobs, LinkedIn)│    │(Resume Parse/Score)│  │
                               │  └────────────────────────┘    └──────────┬─────────┘  │
                               └──────────────┬────────────────────────────┼────────────┘
                                              │ SQLAlchemy                 │ LLM API
                                              ▼                            ▼
                               ┌───────────────────────────┐    ┌────────────────────┐
                               │        PostgreSQL         │    │      Groq API      │
                               │      (Alembic DB)         │    │ (Llama-3.3-70b-v)  │
                               └───────────────────────────┘    └────────────────────┘
```

The system is designed as a lightweight, single-process FastAPI web server that handles request routing, database connection pools, local/S3 uploads, and runs in-process async background workers using FastAPI `BackgroundTasks`.

---

## 2. Authentication & Authorization Flow

### 2.1 Passwordless Login (OTP)
1. **Request:** User enters their email.
   - Limit: 5 requests per minute per email (Redis-based rate limit).
   - Backend generates a 6-digit OTP, stores it in Redis with a 10-minute TTL, and sends it via Resend.
2. **Verification:** User submits the 6-digit OTP.
   - Limit: 10 attempts per minute per IP (Redis-based rate limit).
   - If verification fails 5 times, the OTP is immediately deleted from Redis, forcing a new request.
   - Upon success, backend returns a short-lived (15-minute) JWT Access Token.
   - A Refresh Token is set in a secure, `httpOnly`, `SameSite` environment-conditional cookie (Lax/Secure=False for local, None/Secure=True for production).

### 2.2 JWT Verification (Type-Claim Anti-Confusion)
To avoid JWT token confusion:
- Access Tokens carry `type: "access"`.
- Refresh Tokens carry `type: "refresh"`.
- All decode/verification calls assert the expected `type` claim explicitly.
- Access token is kept strictly in React memory (Zustand state) to mitigate XSS risks.

### 2.3 CSRF Protection on Token Refresh
The `/auth/refresh` endpoint requires:
1. The Refresh Token cookie (automatic browser delivery).
2. The expired JWT Access Token in the `Authorization: Bearer <token>` header as CSRF proof (submitting client ownership verification).

---

## 3. Database Schema

The database is managed using Alembic migrations under `backend/db/migrations/`.

```mermaid
erDiagram
    User ||--o{ Resume : owns
    User ||--o{ Portal : configures
    User ||--o{ Job : tracks
    User ||--o{ LinkedInPost : ingests
    User ||--o{ ApiToken : possesses
    User ||--o{ AuditLog : generates
    User ||--o{ CredentialAccessLog : records

    User {
        uuid id PK
        string email UK
        string password_hash
        string name
        string target_roles
        string target_locations
        string work_auth_status
        datetime created_at
    }

    Resume {
        uuid id PK
        uuid user_id FK
        string filename
        integer file_size_bytes
        string s3_key
        jsonb parsed_data
        datetime created_at
    }

    Portal {
        uuid id PK
        uuid user_id FK
        string portal_type
        string display_name
        string status
        binary encrypted_credentials
        datetime created_at
    }

    Job {
        uuid id PK
        uuid user_id FK
        string title
        string company
        string location
        string country
        string url
        float match_score
        string match_rationale
        string sponsorship
        jsonb raw_data
        datetime fetched_at
    }

    LinkedInPost {
        uuid id PK
        uuid user_id FK
        string post_url UK
        string poster_name
        string raw_text
        float match_score
        string match_rationale
        string country
        string sponsorship
        string source
        datetime submitted_at
        datetime scored_at
    }

    ApiToken {
        uuid id PK
        uuid user_id FK
        string token_hash UK
        string prefix
        datetime created_at
        datetime revoked_at
        datetime last_used_at
    }
```

---

## 4. Encryption Architecture (Envelope Pattern)

To protect third-party portal credentials stored in the database:
1. **Master Key:** A 256-bit Fernet key supplied via `ENCRYPTION_MASTER_KEY` environment variable.
2. **User Data Key:** Each user has a unique data key generated during signup. This key is encrypted by the Master Key and stored in the `User` table.
3. **Data Encryption:** When a user configures a portal, a fresh Fernet instances uses the user's decrypted data key to encrypt the credentials before writing to the `Portal.encrypted_credentials` column.

### 4.1 Master Key Rotation
The rotation script (`backend/scripts/rotate_master_key.py`) facilitates secure rotation:
1. Re-encrypts all User Data Keys using the new `ENCRYPTION_MASTER_KEY_NEW`.
2. Leaves encrypted credentials untouched, avoiding decryption of raw credentials.
3. Fully idempotent and atomic.

---

## 5. LLM Matching & Ingestion Flows

### 5.1 Resume Parsing
- **Trigger:** PDF or DOCX file upload.
- **Mechanism:** Text is extracted and sent to the LLM (Groq Llama-3.3-70b-v) with structural instructions.
- **Output:** Parsed JSON specifying target roles, skills, experience, and years of experience.

### 5.2 Job Match Scoring
- **Trigger:** Fetch cycle or manual post upload.
- **Process:** Unscored jobs are grouped and matched against the user's parsed resume details.
- **Prompting:** The LLM returns a structured JSON containing a match score (0-100), logical rationale, visa sponsorship indication, and identified country.

---

## 6. Chrome Extension

The extension acts as a silent background parser:
1. **Content Script:** Injects a `MutationObserver` on LinkedIn feeds, checking posts against hiring keyword regexes.
2. **Deduplication:** Maintains an in-memory set of post URLs to prevent duplicate ingestions.
3. **API Relay:** Sends matched posts to the backend's `/linkedin-posts/ingest` endpoint using a long-lived extension API token (`jaa_...`).

---

## 7. Visual Design System

The frontend uses a **light, professional theme** inspired by Linear, Notion, and Vercel. All tokens are defined as CSS custom properties in `index.css` via Tailwind v4's `@theme` directive.

### 7.1 Color Palette

| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg-page` | `#F8F9FB` | Page background (off-white) |
| `--color-bg-surface` | `#FFFFFF` | Surface/panel background |
| `--color-bg-card` | `#FFFFFF` | Card backgrounds |
| `--color-bg-elevated` | `#F1F3F5` | Elevated surfaces, loading skeletons |
| `--color-bg-sidebar` | `#FAFBFC` | Sidebar navigation |
| `--color-text-primary` | `#1A1D23` | Headings, body text |
| `--color-text-secondary` | `#5F6B7A` | Descriptions, metadata |
| `--color-text-muted` | `#9CA3AF` | Captions, placeholders |
| `--color-accent` | `#6366F1` | Primary buttons, active nav, links |
| `--color-accent-hover` | `#4F46E5` | Hovered accent elements |
| `--color-border-default` | `#E5E7EB` | Card/input borders |
| `--color-border-subtle` | `#F0F0F3` | Very light separators |

### 7.2 Semantic Status Colors

Each status color has three variants: a strong foreground, a light background (for badge pills), and a subtle transparent (for overlays).

| Status | Foreground | Background | Example |
|--------|-----------|------------|---------|
| Success | `#16A34A` | `#F0FDF4` | "Connected" badge |
| Warning | `#D97706` | `#FFFBEB` | "Needs Re-auth" badge |
| Error | `#DC2626` | `#FEF2F2` | "Error" badge |
| Info | `#2563EB` | `#EFF6FF` | "Extension" source badge |

### 7.3 Typography

- **Font:** Inter (with system-ui fallback)
- **Headings:** `font-semibold`, `text-xl` (page titles), `text-base` (card titles)
- **Body:** `text-sm` (14px) — primary content size
- **Caption:** `text-xs` (12px) — metadata, timestamps

### 7.4 Spacing & Layout

- **Page padding:** `2rem` (`--spacing-page`)
- **Card padding:** `1.5rem` (p-6)
- **Card gap:** `1.5rem` (space-y-6) between sections
- **Sidebar width:** `15rem` (w-60), flex-shrink-0, no position:fixed
- **Main content:** flex-1, independent overflow-y scroll

### 7.5 Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-card` | `0 1px 3px rgba(0,0,0,0.04)` | Cards, filter bar |
| `--shadow-elevated` | `0 4px 12px rgba(0,0,0,0.06)` | Hover states, login card |
| `--shadow-glow` | `0 0 0 3px rgba(99,102,241,0.12)` | Focus rings on inputs |

### 7.6 Component Patterns

- **Buttons (primary):** `bg-accent` + `text-inverse` + `shadow-sm`, hover darkens
- **Buttons (secondary/ghost):** `text-secondary`, no border, hover changes text color
- **Status badges:** Pill shape (`rounded-full`), light background + dark text (e.g., green-50 bg + green-600 text), with a small colored dot indicator
- **Score badges:** Same pill pattern, color-coded by score tier (≥80 green, ≥60 blue, ≥40 amber, <40 red)
- **Inputs:** White bg, light border, subtle focus glow ring, muted placeholder
- **Cards:** White bg on off-white page, subtle border, soft shadow — no heavy borders

