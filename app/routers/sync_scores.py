from fastapi import APIRouter, Depends
from app.lib.auth import get_current_user
from app.lib.supabase_client import get_admin_client
from app.lib.scoring import score_project, get_week_start
from datetime import datetime

router = APIRouter()

def chunk(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

@router.post("/sync")
def sync_scores(user=Depends(get_current_user)):
    supabase = get_admin_client()
    week_start = get_week_start()

    projects = supabase.table("projects").select(
        "id, globaldata_id, company_name, project_value_usd, execution_date, status, "
        "key_contacts, momentum_score, fid_detected, contractor_detected, contractor_name"
    ).eq("user_id", user.id).execute()

    if not projects.data:
        return {"ok": True, "synced": 0, "week_start": week_start}

    # Load HubSpot history (table may not exist — handle gracefully)
    hs_map = {}
    try:
        hs_companies = supabase.table("hubspot_companies").select(
            "name, deals_count, total_deal_value, last_deal_date"
        ).execute()
        for h in hs_companies.data or []:
            if h.get("name"):
                hs_map[h["name"].lower()] = h
    except Exception:
        pass  # HubSpot data not available, continue without it

    def find_history(company_name: str | None):
        if not company_name:
            return None
        cn = company_name.lower()
        for key, val in hs_map.items():
            if key in cn or cn in key:
                return val
        return None

    score_rows = []
    snap_rows = []

    for p in projects.data:
        history = find_history(p.get("company_name"))
        contacts_list = p.get("key_contacts") or []
        key_contacts_count = len(contacts_list) if isinstance(contacts_list, list) else 0

        breakdown = score_project(
            project_value_usd=p.get("project_value_usd"),
            execution_date_str=p.get("execution_date"),
            status=p.get("status") or "",
            key_contacts_count=key_contacts_count,
            momentum_score=p.get("momentum_score"),
            fid_detected=bool(p.get("fid_detected")),
            contractor_detected=bool(p.get("contractor_detected")),
            contractor_name=p.get("contractor_name"),
            history_deals=history.get("deals_count", 0) if history else 0,
            history_last_deal=history.get("last_deal_date") if history else None,
        )
        base = {
            "project_id": p["id"],
            "user_id":    user.id,
            "week_start": week_start,
            "score":      breakdown.total,
            "breakdown":  breakdown.to_dict(),
            "rank":       0,
        }
        score_rows.append(dict(base))
        snap_rows.append(dict(base))

    # Sort descending, assign ranks
    score_rows.sort(key=lambda r: r["score"], reverse=True)
    snap_rows.sort(key=lambda r: r["score"], reverse=True)
    for i, row in enumerate(score_rows):
        row["rank"] = i + 1
    for i, row in enumerate(snap_rows):
        row["rank"] = i + 1

    # Replace scores for this week
    supabase.table("priority_scores").delete().eq("user_id", user.id).eq("week_start", week_start).execute()
    for batch in chunk(score_rows, 200):
        supabase.table("priority_scores").insert(batch).execute()

    # Upsert snapshots
    for batch in chunk(snap_rows, 200):
        supabase.table("weekly_snapshots").upsert(
            batch, on_conflict="project_id,user_id,week_start"
        ).execute()

    # Log sync
    supabase.table("sync_logs").insert({
        "triggered_by":    "manual",
        "user_id":         user.id,
        "completed_at":    datetime.utcnow().isoformat(),
        "projects_synced": len(score_rows),
    }).execute()

    return {"ok": True, "synced": len(score_rows), "week_start": week_start}
