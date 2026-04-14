"""
config.py — single source of truth for all constants, table names,
model names, and environment variable names.

If something breaks (wrong table name, model retired, weight change,
API key renamed), this is the ONLY file you need to touch.
No magic strings anywhere else in the codebase.
"""

import os


# ---------------------------------------------------------------------------
# Database table names
# ---------------------------------------------------------------------------

TABLE_PROJECTS       = "projects"
TABLE_CONTACTS       = "contacts"
TABLE_FAVORITES      = "favorites"
TABLE_SCORES         = "priority_scores"
TABLE_SNAPSHOTS      = "weekly_snapshots"
TABLE_RESEARCH_CACHE = "research_cache"
TABLE_SYNC_LOGS      = "sync_logs"
TABLE_HUBSPOT        = "hubspot_companies"


# ---------------------------------------------------------------------------
# Claude model names
# If Anthropic retires a model, update here — no other file needs changing.
# ---------------------------------------------------------------------------

CLAUDE_FAST_MODEL  = "claude-haiku-4-5-20251001"  # used for: summarize (cheap, fast)
CLAUDE_SMART_MODEL = "claude-sonnet-4-6"           # used for: research, meeting prep


# ---------------------------------------------------------------------------
# Scoring weights  (must always sum to 100)
# ---------------------------------------------------------------------------

SCORE_WEIGHTS = {
    "past_work":      25,
    "execution_date": 25,
    "project_value":  20,
    "project_phase":  20,
    "relationship":   10,
}


# ---------------------------------------------------------------------------
# Excel import settings
# ---------------------------------------------------------------------------

# How many rows to scan downward looking for the header row
HEADER_SEARCH_MAX_ROWS = 12

# Rows to skip after the header row before data starts
# (GlobalData exports have a units row + one blank row = 2)
HEADER_DATA_OFFSET = 2

# How many Key_Contact columns to parse per project row
CONTACT_SLOTS = 6

# Max rows per Supabase batch upsert (avoids request-size limits)
IMPORT_CHUNK_SIZE = 200


# ---------------------------------------------------------------------------
# Research cache
# ---------------------------------------------------------------------------

# Number of days before a cached research result is considered stale
RESEARCH_CACHE_MAX_AGE_DAYS = 7


# ---------------------------------------------------------------------------
# Environment variable names
#
# Always reference these constants instead of writing the string directly.
# Example:  os.getenv(ENV_BING_KEY)  not  os.getenv("BING_SEARCH_API_KEY")
# ---------------------------------------------------------------------------

ENV_SUPABASE_URL         = "SUPABASE_URL"
ENV_SUPABASE_ANON_KEY    = "SUPABASE_ANON_KEY"
ENV_SUPABASE_SERVICE_KEY = "SUPABASE_SERVICE_ROLE_KEY"
ENV_ANTHROPIC_KEY        = "ANTHROPIC_API_KEY"
ENV_BING_KEY             = "BING_SEARCH_API_KEY"   # optional — enables /research
ENV_ALLOWED_ORIGINS      = "ALLOWED_ORIGINS"        # optional — comma-separated frontend URLs

# --- Future: Azure AD SSO ---
# Uncomment and fill in once the App Registration is set up.
# Auth code will pick these up automatically — no other changes needed.
ENV_AZURE_TENANT_ID  = "AZURE_TENANT_ID"   # not active yet
ENV_AZURE_CLIENT_ID  = "AZURE_CLIENT_ID"   # not active yet


# ---------------------------------------------------------------------------
# Startup validation
# The app will refuse to start if any of these are missing from the environment.
# ---------------------------------------------------------------------------

REQUIRED_ENV_VARS = [
    ENV_SUPABASE_URL,
    ENV_SUPABASE_SERVICE_KEY,
    ENV_ANTHROPIC_KEY,
]


# ---------------------------------------------------------------------------
# CORS allowed origins
# ---------------------------------------------------------------------------

def get_allowed_origins() -> list[str]:
    """
    Read allowed frontend origins from the ALLOWED_ORIGINS environment variable
    (comma-separated).  Falls back to localhost only — so production is never
    wide-open by accident.

    Set in .env for local dev:
        ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

    Set in Azure App Service config for production:
        ALLOWED_ORIGINS=https://sales.twd.nl
    """
    raw = os.getenv(ENV_ALLOWED_ORIGINS, "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return ["http://localhost:3000", "http://localhost:5173"]
