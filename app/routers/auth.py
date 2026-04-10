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
    supabase_url = os.environ["SUPABASE_URL"]
    api_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    r = httpx.post(
        f"{supabase_url}/auth/v1/token?grant_type=password",
        json={"email": body.email, "password": body.password},
        headers={"apikey": api_key, "Content-Type": "application/json"},
        timeout=15,
    )
    if r.status_code != 200:
        detail = r.json().get("error_description") or r.json().get("msg") or "Login failed"
        raise HTTPException(status_code=401, detail=detail)

    data = r.json()
    return {
        "access_token": data["access_token"],
        "user": {"id": data["user"]["id"], "email": data["user"]["email"]},
    }
