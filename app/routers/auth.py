import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(body: LoginRequest):
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not supabase_url:
        raise HTTPException(status_code=500, detail="SUPABASE_URL not configured")

    # Try anon key first, fall back to service role key
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    keys = [k for k in [anon_key, service_key] if k]

    if not keys:
        raise HTTPException(status_code=500, detail="No Supabase API key configured")

    last_error = "Login failed"
    for api_key in keys:
        try:
            r = httpx.post(
                f"{supabase_url}/auth/v1/token?grant_type=password",
                json={"email": body.email, "password": body.password},
                headers={"apikey": api_key, "Content-Type": "application/json"},
                timeout=15,
            )
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Auth service timed out")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Auth service unreachable: {e}")

        if r.status_code == 200:
            data = r.json()
            return {
                "access_token": data["access_token"],
                "user": {"id": data["user"]["id"], "email": data["user"]["email"]},
            }

        try:
            b = r.json()
            err = b.get("error_description") or b.get("message") or b.get("error") or str(b)
        except Exception:
            err = r.text or "Unknown error"

        last_error = err
        # If wrong credentials (not an API key issue), no point trying another key
        if "invalid_grant" in err.lower() or "invalid login" in err.lower() or "email" in err.lower():
            break

    raise HTTPException(status_code=401, detail=last_error)
