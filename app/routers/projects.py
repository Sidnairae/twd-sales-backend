from fastapi import APIRouter, Depends
from app.lib.auth import get_current_user
from app.lib.supabase_client import get_admin_client
from app.lib.scoring import get_week_start

router = APIRouter()

@router.get("/projects")
def get_projects(user=Depends(get_current_user)):
    supabase = get_admin_client()
    week_start = get_week_start()

    scores = supabase.table("priority_scores").select(
        "id, rank, score, breakdown, project_id, "
        "projects(id, name, company_name, sector, country, region, world_region, stage_normalized, "
        "project_value_usd, execution_date, description, status, project_url, "
        "key_contacts, globaldata_id, fid_detected, contractor_detected, contractor_name)"
    ).eq("user_id", user.id).eq("week_start", week_start).order("rank").execute()

    if not scores.data:
        return {"scores": [], "week_start": week_start}

    project_ids = [s["project_id"] for s in scores.data]

    contacts = supabase.table("contacts").select(
        "id, project_id, name, title, email, linkedin_url, source, role_type, "
        "is_contractor_contact, is_main_contact, outreach_sentiment, outreach_notes, outreach_date"
    ).in_("project_id", project_ids).execute()

    contacts_by_project: dict[str, list] = {}
    for c in contacts.data or []:
        pid = c["project_id"]
        contacts_by_project.setdefault(pid, []).append(c)

    prev_snaps = supabase.table("weekly_snapshots").select(
        "project_id, rank, breakdown"
    ).eq("user_id", user.id).eq("week_start", week_start).execute()

    prev_rank = {s["project_id"]: s["rank"] for s in prev_snaps.data or []}
    prev_breakdown = {s["project_id"]: s["breakdown"] for s in prev_snaps.data or []}

    favorites = supabase.table("favorites").select("project_id").eq("user_id", user.id).execute()
    fav_ids = {f["project_id"] for f in favorites.data or [] if f["project_id"]}

    sync_log = supabase.table("sync_logs").select("completed_at").order(
        "completed_at", desc=True
    ).limit(1).execute()
    last_sync = sync_log.data[0]["completed_at"] if sync_log.data else None

    result = []
    for s in scores.data:
        pid = s["project_id"]
        result.append({
            **s,
            "contacts": contacts_by_project.get(pid, []),
            "previous_rank": prev_rank.get(pid),
            "previous_breakdown": prev_breakdown.get(pid),
            "is_favorite": pid in fav_ids,
        })

    return {"scores": result, "week_start": week_start, "last_sync": last_sync}
