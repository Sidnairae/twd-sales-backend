from fastapi import HTTPException, Header
from app.lib.supabase_client import get_admin_client

def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.replace("Bearer ", "").strip()
    supabase = get_admin_client()
    result = supabase.auth.get_user(token)
    if not result.user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return result.user
