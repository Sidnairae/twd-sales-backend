"""
auth.py — FastAPI dependency for authenticating incoming requests.

Usage in any router:
    from app.lib.auth import get_current_user
    ...
    def my_endpoint(user=Depends(get_current_user)):
        ...  # user.id is the authenticated Supabase user ID

Future: to switch to Azure AD SSO, replace the body of get_current_user
with Azure AD JWT validation using the AZURE_TENANT_ID / AZURE_CLIENT_ID
env vars defined in config.py.  The function signature stays identical,
so no router code needs to change.
"""

import logging
from fastapi import HTTPException, Header

from app.lib.clients import get_admin_client

logger = logging.getLogger(__name__)


def get_current_user(authorization: str = Header(...)):
    """
    Validate a Supabase Bearer token and return the authenticated user.
    Raises HTTP 401 if the token is missing, malformed, or expired.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    try:
        result = get_admin_client().auth.get_user(token)
        if not result or not result.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return result.user
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Token validation failed: %s", e)
        raise HTTPException(status_code=401, detail=f"Token validation failed: {e}")
