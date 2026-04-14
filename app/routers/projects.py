"""
projects.py — retrieve the ranked project list for the current week.

Returns priority scores joined with full project details, contacts,
favourite flags, and the previous week's rank for comparison.

Supports pagination via ?limit and ?offset query parameters.
"""

import logging
from fastapi import APIRouter, Depends, Query

from app.config import (
    TABLE_SCORES,
    TABLE_CONTACTS,
    TABLE_SNAPSHOTS,
    TABLE_FAVORITES,
    TABLE_SYNC_LOGS,
)
from app.lib.auth import get_current_user
from app.lib.clients import get_admin_client
from app.lib.scoring import get_week_start

logger = logging.getLogger(__name__)
router  = APIRouter()


@router.get("/projects")
def get_projects(
    limit:  int = Query(default=100, ge=1, le=500, description="Max projects to return."),
    offset: int = Query(default=0,   ge=0,          description="Number of projects to skip."),
    user=Depends(get_current_user),
):
    """
    Return the ranked project list for the current week.

    Each item includes the project details, all contacts, the previous
    week's rank, and whether the project is marked as a favourite.
    Run POST /api/sync first if the list is empty.
    """
    supabase   = get_admin_client()
    week_start = get_week_start()

    scores = supabase.table(TABLE_SCORES).select(
        "id, rank, score, breakdown, project_id, "
        "projects(id, name, company_name, sector, country, region, world_region, "
        "stage_normalized, project_value_usd, execution_date, description, status, "
        "project_url, key_contacts, globaldata_id, fid_detected, contractor_detected, "
        "contractor_name)"
    ).eq("user_id", user.id).eq("week_start", week_start).order("rank").range(
        offset, offset + limit - 1
    ).execute()

    if not scores.data:
        return {"scores": [], "week_start": week_start, "last_sync": None}

    project_ids = [s["project_id"] for s in scores.data]

    # Fetch all contacts for these projects in one query
    contacts = supabase.table(TABLE_CONTACTS).select(
        "id, project_id, name, title, email, linkedin_url, source, role_type, "
        "is_contractor_contact, is_main_contact, outreach_sentiment, outreach_notes, outreach_date"
    ).in_("project_id", project_ids).execute()

    contacts_by_project: dict[str, list] = {}
    for c in contacts.data or []:
        contacts_by_project.setdefault(c["project_id"], []).append(c)

    # Previous week's snapshot for rank-change comparison
    prev_snaps = supabase.table(TABLE_SNAPSHOTS).select(
        "project_id, rank, breakdown"
    ).eq("user_id", user.id).eq("week_start", week_start).execute()

    prev_rank      = {s["project_id"]: s["rank"]      for s in prev_snaps.data or []}
    prev_breakdown = {s["project_id"]: s["breakdown"] for s in prev_snaps.data or []}

    # Favourite project IDs for this user
    favorites = supabase.table(TABLE_FAVORITES).select("project_id").eq("user_id", user.id).execute()
    fav_ids   = {f["project_id"] for f in favorites.data or [] if f["project_id"]}

    # Timestamp of the last sync run
    sync_log  = supabase.table(TABLE_SYNC_LOGS).select("completed_at").order(
        "completed_at", desc=True
    ).limit(1).execute()
    last_sync = sync_log.data[0]["completed_at"] if sync_log.data else None

    result = [
        {
            **s,
            "contacts":           contacts_by_project.get(s["project_id"], []),
            "previous_rank":      prev_rank.get(s["project_id"]),
            "previous_breakdown": prev_breakdown.get(s["project_id"]),
            "is_favorite":        s["project_id"] in fav_ids,
        }
        for s in scores.data
    ]

    return {"scores": result, "week_start": week_start, "last_sync": last_sync}
