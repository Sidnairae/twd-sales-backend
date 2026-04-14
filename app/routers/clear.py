"""
clear.py — delete all data for the authenticated user.

This is a destructive, irreversible operation.
A confirmation flag is required to prevent accidental calls.

Usage:
  DELETE /api/clear            → dry run: returns a count of what would be deleted
  DELETE /api/clear?confirm=true → actually deletes everything
"""

import logging
from fastapi import APIRouter, Depends, Query

from app.config import (
    TABLE_PROJECTS,
    TABLE_CONTACTS,
    TABLE_FAVORITES,
    TABLE_SCORES,
    TABLE_SNAPSHOTS,
    TABLE_RESEARCH_CACHE,
)
from app.lib.auth import get_current_user
from app.lib.clients import get_admin_client

logger = logging.getLogger(__name__)
router  = APIRouter()


@router.delete("/clear")
def clear_user_data(
    confirm: bool = Query(
        default=False,
        description="Must be true to actually delete data. Omit for a dry-run preview.",
    ),
    user=Depends(get_current_user),
):
    """
    Delete all projects, contacts, scores, snapshots, favourites, and research
    cache for the authenticated user.

    - Without ?confirm=true  → returns counts of what would be deleted (safe preview).
    - With    ?confirm=true  → permanently deletes everything (irreversible).
    """
    supabase = get_admin_client()

    # Count what exists before touching anything
    project_rows  = supabase.table(TABLE_PROJECTS).select("id").eq("user_id", user.id).execute()
    project_ids   = [p["id"] for p in project_rows.data or []]
    project_count = len(project_ids)

    score_count    = len(supabase.table(TABLE_SCORES).select("id").eq("user_id", user.id).execute().data or [])
    snapshot_count = len(supabase.table(TABLE_SNAPSHOTS).select("id").eq("user_id", user.id).execute().data or [])
    fav_count      = len(supabase.table(TABLE_FAVORITES).select("id").eq("user_id", user.id).execute().data or [])

    preview = {
        "projects":          project_count,
        "scores":            score_count,
        "snapshots":         snapshot_count,
        "favorites":         fav_count,
        "contacts_and_cache": "all linked to above projects",
    }

    if not confirm:
        return {
            "dry_run": True,
            "message": "Pass ?confirm=true to permanently delete the data below.",
            "would_delete": preview,
        }

    # Perform deletion — child records first, then parent projects
    if project_ids:
        supabase.table(TABLE_CONTACTS).delete().in_("project_id", project_ids).execute()
        supabase.table(TABLE_RESEARCH_CACHE).delete().in_("project_id", project_ids).execute()

    supabase.table(TABLE_SCORES).delete().eq("user_id", user.id).execute()
    supabase.table(TABLE_SNAPSHOTS).delete().eq("user_id", user.id).execute()
    supabase.table(TABLE_FAVORITES).delete().eq("user_id", user.id).execute()
    supabase.table(TABLE_PROJECTS).delete().eq("user_id", user.id).execute()

    logger.info("User %s cleared all data (%d projects).", user.id, project_count)

    return {"ok": True, "deleted": preview}
