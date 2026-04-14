"""
main.py — TWD Sales Assistant API entry point.

Starts the FastAPI application, validates required environment variables,
configures logging and CORS, registers all routers, and exposes a /health
endpoint for Azure App Service health checks.

Run locally:
    uvicorn main:app --reload

Run in production (Azure App Service startup command):
    uvicorn main:app --host 0.0.0.0 --port 8000
"""

import os
import logging
import traceback

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load .env before anything else so config values are available on import
load_dotenv()

from app.config import REQUIRED_ENV_VARS, get_allowed_origins
from app.routers import (
    auth,
    projects,
    import_data,
    contacts,
    favorites,
    sync_scores,
    summarize,
    meeting_prep,
    research,
    clear,
)

# ---------------------------------------------------------------------------
# Logging
# Structured output readable by Azure App Service log stream and local dev.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Startup validation
# Fail fast with a clear message rather than a cryptic KeyError at runtime.
# ---------------------------------------------------------------------------
missing = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
if missing:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(missing)}\n"
        "Check your .env file or Azure App Service configuration."
    )


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="TWD Sales Assistant API",
    version="1.0.0",
    description=(
        "Backend for the TWD Sales Assistant. "
        "Imports and scores marine engineering projects from GlobalData, "
        "enriches them with CRM history and web research, and surfaces "
        "prioritised leads to the BD team."
    ),
)


# ---------------------------------------------------------------------------
# CORS
# Origins are read from ALLOWED_ORIGINS env var (comma-separated).
# Defaults to localhost only — never wide-open in production.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global error handler
# Catches any unhandled exception, logs the full traceback (server-side only),
# and returns a clean JSON response to the client.
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled error on %s %s\n%s",
        request.method,
        request.url,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {exc}"},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router,         prefix="/api", tags=["auth"])
app.include_router(projects.router,     prefix="/api", tags=["projects"])
app.include_router(import_data.router,  prefix="/api", tags=["import"])
app.include_router(contacts.router,     prefix="/api", tags=["contacts"])
app.include_router(favorites.router,    prefix="/api", tags=["favorites"])
app.include_router(sync_scores.router,  prefix="/api", tags=["sync"])
app.include_router(summarize.router,    prefix="/api", tags=["summarize"])
app.include_router(meeting_prep.router, prefix="/api", tags=["meeting_prep"])
app.include_router(research.router,     prefix="/api", tags=["research"])
app.include_router(clear.router,        prefix="/api", tags=["clear"])


# ---------------------------------------------------------------------------
# Health check
# Used by Azure App Service to confirm the process is alive.
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"])
def health():
    """Returns 200 OK when the service is running."""
    return {"status": "ok"}
