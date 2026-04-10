from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.lib.supabase_client import get_admin_client

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(body: LoginRequest):
    supabase = get_admin_client()
    try:
        result = supabase.auth.sign_in_with_password({"email": body.email, "password": body.password})
        return {
            "access_token": result.session.access_token,
            "user": {"id": result.user.id, "email": result.user.email},
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
