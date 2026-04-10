from fastapi import APIRouter, Depends
from app.lib.auth import get_current_user
from app.lib.supabase_client import get_admin_client

router = APIRouter()

@router.delete("/clear")
def clear_user_data(user=Depends(get_current_user)):
    supabase = get_admin_client()
    supabase.table("priority_scores").delete().eq("user_id", user.id).execute()
    supabase.table("weekly_snapshots").delete().eq("user_id", user.id).execute()
    supabase.table("favorites").delete().eq("user_id", user.id).execute()
    projects = supabase.table("projects").select("id").eq("user_id", user.id).execute()
    if projects.data:
        ids = [p["id"] for p in projects.data]
        supabase.table("contacts").delete().in_("project_id", ids).execute()
        supabase.table("research_cache").delete().in_("project_id", ids).execute()
    supabase.table("projects").delete().eq("user_id", user.id).execute()
    return {"ok": True}
