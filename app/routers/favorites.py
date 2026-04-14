"""
favorites.py — toggle and retrieve a user's favourite projects.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import TABLE_FAVORITES
from app.lib.auth import get_current_user
from app.lib.clients import get_admin_client

logger = logging.getLogger(__name__)
router  = APIRouter()


class FavoriteToggle(BaseModel):
    project_id:   Optional[str] = None
    globaldata_id: str
    project_name: Optional[str] = None
    company_name: Optional[str] = None


@router.get("/favorites")
def get_favorites(user=Depends(get_current_user)):
    """Return all favourited projects for the authenticated user, newest first."""
    supabase = get_admin_client()
    data = supabase.table(TABLE_FAVORITES).select(
        "id, globaldata_id, project_name, company_name, created_at, project_id, "
        "projects(id, name, company_name, country, status, project_value_usd, "
        "execution_date, sector, world_region, stage_normalized, project_url, "
        "description, key_contacts, globaldata_id)"
    ).eq("user_id", user.id).order("created_at", desc=True).execute()
    return {"favorites": data.data or []}


@router.post("/favorites")
def toggle_favorite(body: FavoriteToggle, user=Depends(get_current_user)):
    """
    Toggle the favourite state for a project.
    Returns is_favorite=true if added, is_favorite=false if removed.
    """
    supabase = get_admin_client()
    existing = supabase.table(TABLE_FAVORITES).select("id").eq(
        "user_id", user.id
    ).eq("globaldata_id", body.globaldata_id).maybe_single().execute()

    if existing.data:
        supabase.table(TABLE_FAVORITES).delete().eq("id", existing.data["id"]).execute()
        return {"ok": True, "is_favorite": False}

    supabase.table(TABLE_FAVORITES).insert({
        "user_id":      user.id,
        "project_id":   body.project_id,
        "globaldata_id": body.globaldata_id,
        "project_name": body.project_name,
        "company_name": body.company_name,
    }).execute()
    return {"ok": True, "is_favorite": True}
