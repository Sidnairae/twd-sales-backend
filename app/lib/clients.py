"""
clients.py — singleton instances of every external service client.

Creating a new client on every request wastes memory and connection overhead.
These module-level singletons are initialised once when first accessed and
reused for the lifetime of the process.

All other modules should import from here — never instantiate clients directly.
"""

import os
import logging
from supabase import create_client, Client
from anthropic import Anthropic

from app.config import (
    ENV_SUPABASE_URL,
    ENV_SUPABASE_SERVICE_KEY,
    ENV_SUPABASE_ANON_KEY,
    ENV_ANTHROPIC_KEY,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

_admin_client: Client | None = None
_anon_client:  Client | None = None


def get_admin_client() -> Client:
    """
    Supabase client using the service-role key.

    The service-role key bypasses Row Level Security (RLS), so every query
    that uses this client MUST include an explicit .eq("user_id", user.id)
    filter to enforce access control in Python code.
    """
    global _admin_client
    if _admin_client is None:
        _admin_client = create_client(
            os.environ[ENV_SUPABASE_URL],
            os.environ[ENV_SUPABASE_SERVICE_KEY],
        )
        logger.debug("Supabase admin client initialised.")
    return _admin_client


def get_anon_client() -> Client:
    """
    Supabase client using the anon key.
    Used only for validating user auth tokens.
    """
    global _anon_client
    if _anon_client is None:
        _anon_client = create_client(
            os.environ[ENV_SUPABASE_URL],
            os.environ[ENV_SUPABASE_ANON_KEY],
        )
        logger.debug("Supabase anon client initialised.")
    return _anon_client


# ---------------------------------------------------------------------------
# Anthropic (Claude)
# ---------------------------------------------------------------------------

_anthropic_client: Anthropic | None = None


def get_anthropic_client() -> Anthropic:
    """Singleton Anthropic client — initialised once, reused per process."""
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = Anthropic(api_key=os.environ[ENV_ANTHROPIC_KEY])
        logger.debug("Anthropic client initialised.")
    return _anthropic_client
