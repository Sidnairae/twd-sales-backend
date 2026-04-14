"""
auth.py — user login via Supabase email/password authentication.

Returns a JWT access token that must be passed as a Bearer token in the
Authorization header for all other endpoints.

Future: when Azure AD SSO is ready, this endpoint can be retired in favour
of the OAuth2 flow.  The rest of the API is unaffected — it only cares that
a valid Bearer token is present, not how it was obtained.
"""

import os
import logging

import httpx
from fastapi import APIRouter, HTTPException

from app.config import ENV_SUPABASE_URL, ENV_SUPABASE_ANON_KEY
from app.schemas import LoginRequest, LoginResponse

logger = logging.getLogger(__name__)
router  = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    """
    Authenticate with email + password.
    Returns an access_token to use in subsequent requests.
    """
    supabase_url = os.environ.get(ENV_SUPABASE_URL, "").rstrip("/")
    if not supabase_url:
        raise HTTPException(status_code=500, detail="SUPABASE_URL is not configured")

    anon_key = os.environ.get(ENV_SUPABASE_ANON_KEY, "").strip()
    if not anon_key:
        raise HTTPException(status_code=500, detail="SUPABASE_ANON_KEY is not configured")

    try:
        r = httpx.post(
            f"{supabase_url}/auth/v1/token?grant_type=password",
            json={"email": body.email, "password": body.password},
            headers={"apikey": anon_key, "Content-Type": "application/json"},
            timeout=15,
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Auth service timed out — try again.")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Auth service unreachable: {e}")

    if r.status_code == 200:
        data = r.json()
        return {
            "access_token": data["access_token"],
            "user": {
                "id":    data["user"]["id"],
                "email": data["user"]["email"],
            },
        }

    # Parse error from Supabase response
    try:
        b   = r.json()
        err = b.get("error_description") or b.get("message") or b.get("error") or str(b)
    except Exception:
        err = r.text or "Unknown error"

    logger.warning("Login failed for %s: %s", body.email, err)
    raise HTTPException(status_code=401, detail=err)
