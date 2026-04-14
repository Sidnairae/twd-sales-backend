# TWD Sales Assistant — Backend

FastAPI backend for the TWD Sales Assistant.  
Imports marine engineering projects from GlobalData, scores and ranks them by BD priority, and surfaces AI-generated research and meeting prep cards to the sales team.

---

## What it does

1. **Import** — upload a GlobalData `.xlsx` export and the backend parses every project, detects FID signals and contractor awards, and stores everything in Supabase.
2. **Score & rank** — run a sync to score all projects across five dimensions (past work, execution date, project value, project phase, relationship) and rank them for the current week.
3. **Research** — trigger a Bing web search on any project and get a Claude-generated intelligence report cached for 7 days.
4. **Meeting prep** — generate a structured BD prep card (situation, key questions, value proposition, red flags, next steps) for any project.
5. **Summarise** — condense a long GlobalData description into 2–3 actionable sentences.
6. **Contacts & favourites** — track outreach status per contact, flag key contacts, and save favourite projects.

---

## Project structure

```
twd-sales-backend/
├── main.py                        Entry point — app setup, CORS, logging, startup checks
├── requirements.txt
├── .env.example                   Copy to .env and fill in keys
│
├── app/
│   ├── config.py                  ← Single source of truth for ALL constants
│   │                                (table names, model names, env var names, weights)
│   │
│   ├── lib/
│   │   ├── clients.py             Singleton Supabase + Anthropic clients
│   │   ├── auth.py                FastAPI auth dependency (Bearer token validation)
│   │   ├── scoring.py             Project priority scoring logic
│   │   ├── categorize.py          Auto-categorise projects + normalise stage names
│   │   ├── detect.py              Regex detection of FID and contractor signals
│   │   ├── regions.py             Country → world region mapping
│   │   ├── categories.py          Saved search category definitions
│   │   └── utils.py               Shared helpers (chunk)
│   │
│   └── routers/
│       ├── auth.py                POST /api/login
│       ├── import_data.py         POST /api/import
│       ├── sync_scores.py         POST /api/sync
│       ├── projects.py            GET  /api/projects
│       ├── contacts.py            PATCH /api/contacts/{id}
│       ├── favorites.py           GET/POST /api/favorites
│       ├── summarize.py           POST /api/summarize
│       ├── research.py            POST /api/research
│       ├── meeting_prep.py        POST /api/meeting-prep/{project_id}
│       └── clear.py               DELETE /api/clear
```

**Rule:** if something breaks — wrong table name, retired model, changed weight — `app/config.py` is the only file you need to touch.

---

## API endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/login` | — | Email + password → JWT token |
| POST | `/api/import` | ✓ | Upload `.xlsx` files, parse and store projects |
| POST | `/api/sync` | ✓ | Score and rank all projects for the current week |
| GET | `/api/projects` | ✓ | Get ranked project list (`?limit=100&offset=0`) |
| PATCH | `/api/contacts/{id}` | ✓ | Update contact outreach info / main contact flag |
| GET | `/api/favorites` | ✓ | Get all favourited projects |
| POST | `/api/favorites` | ✓ | Toggle favourite on a project |
| POST | `/api/summarize` | ✓ | Summarise a project description (Claude Haiku) |
| POST | `/api/research` | ✓ | Web research report for a project (Bing + Claude) |
| POST | `/api/meeting-prep/{id}` | ✓ | Generate a BD meeting prep card (Claude Sonnet) |
| DELETE | `/api/clear` | ✓ | Preview (`?confirm=false`) or delete all user data (`?confirm=true`) |
| GET | `/health` | — | Health check for Azure App Service |

All authenticated endpoints require an `Authorization: Bearer <token>` header.  
Interactive docs available at `/docs` when the server is running.

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Sidnairae/twd-sales-backend.git
cd twd-sales-backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | Yes | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key (keep secret) |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude |
| `BING_SEARCH_API_KEY` | No | Enables the `/research` endpoint |
| `ALLOWED_ORIGINS` | No | Comma-separated frontend URLs (defaults to localhost) |
| `AZURE_TENANT_ID` | No | For Azure AD SSO — not active yet |
| `AZURE_CLIENT_ID` | No | For Azure AD SSO — not active yet |

### 3. Run locally

```bash
uvicorn main:app --reload
```

API is at `http://localhost:8000`  
Swagger docs at `http://localhost:8000/docs`

---

## Deployment (Azure App Service)

Set all environment variables in **Azure App Service → Configuration → Application settings** (same names as `.env`).

Startup command:
```
uvicorn main:app --host 0.0.0.0 --port 8000
```

The app validates all required environment variables on startup and will refuse to start with a clear error message if any are missing.

---

## Scoring model

Projects are scored out of ~100 points each week:

| Dimension | Max pts | Logic |
|---|---|---|
| Past work | 25 | Based on HubSpot deal history with the client |
| Execution date | 25 | Closer start date = higher urgency |
| Project value | 20 | Log scale: $1M → 0 pts, $1B → 20 pts |
| Project phase | 20 | Tender/FEED stages score highest |
| Relationship | 10 | Known contacts + prior dealings |
| Contractor bonus | +5 | Named contractor known (+3 if unnamed) |
| Momentum bonus | +5 | Based on GlobalData momentum score |

All weights live in `app/config.py → SCORE_WEIGHTS`.

---

## Future roadmap

- **Azure AD SSO** — replace Supabase email login with company Microsoft account. Env vars `AZURE_TENANT_ID` and `AZURE_CLIENT_ID` are already defined in `config.py` — no other code changes needed once the App Registration is set up.
- **Azure Database for PostgreSQL** — migrate from Supabase to an Azure-hosted database for full company ownership of the data.
- **Automated weekly sync** — Azure Logic App or cron job to run `/api/sync` every Monday morning automatically.
