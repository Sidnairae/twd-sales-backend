from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.lib.auth import get_current_user
from app.lib.supabase_client import get_admin_client

router = APIRouter()

class FavoriteToggle(BaseModel):
    project_id: Optional[str] = None
    globaldata_id: str
    project_name: Optional[str] = None
    company_name: Optional[str] = None

@router.get("/favorites")
def get_favorites(user=Depends(get_current_user)):
    supabase = get_admin_client()
    data = supabase.table("favorites").select(
        "id, globaldata_id, project_name, company_name, created_at, project_id, "
        "projects(id, name, company_name, country, status, project_value_usd, "
        "execution_date, sector, world_region, stage_normalized, project_url, "
        "description, key_contacts, globaldata_id)"
    ).eq("user_id", user.id).order("created_at", desc=True).execute()
    return {"favorites": data.data or []}

@router.post("/favorites")
def toggle_favorite(body: FavoriteToggle, user=Depends(get_current_user)):
    supabase = get_admin_client()
    existing = supabase.table("favorites").select("id").eq(
        "user_id", user.id
    ).eq("globaldata_id", body.globaldata_id).maybe_single().execute()

    if existing.data:
        supabase.table("favorites").delete().eq("id", existing.data["id"]).execute()
        return {"ok": True, "is_favorite": False}
    else:
        supabase.table("favorites").insert({
            "user_id": user.id,
            "project_id": body.project_id,
            "globaldata_id": body.globaldata_id,
            "project_name": body.project_name,
            "company_name": body.company_name,
        }).execute()
        return {"ok": True, "is_favorite": True}
