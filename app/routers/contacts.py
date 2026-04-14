"""
contacts.py — update contact metadata (main contact flag, outreach tracking).

Ownership is enforced: a contact can only be updated if it belongs to a
project owned by the authenticated user.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.config import TABLE_CONTACTS, TABLE_PROJECTS
from app.lib.auth import get_current_user
from app.lib.clients import get_admin_client
from app.schemas import ContactUpdate, OkResponse

logger = logging.getLogger(__name__)
router  = APIRouter()


@router.patch("/contacts/{contact_id}", response_model=OkResponse)
def update_contact(contact_id: str, body: ContactUpdate, user=Depends(get_current_user)):
    """
    Update outreach tracking or contact flags for a single contact.

    Setting is_main_contact=true automatically clears that flag on all
    other contacts in the same project (only one main contact per project).
    Only fields explicitly included in the request body are updated —
    omitted fields are left unchanged.
    """
    supabase = get_admin_client()

    # Verify contact exists
    contact = supabase.table(TABLE_CONTACTS).select(
        "id, project_id"
    ).eq("id", contact_id).maybe_single().execute()

    if not contact.data:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Verify the contact's project belongs to this user
    project = supabase.table(TABLE_PROJECTS).select("id").eq(
        "id", contact.data["project_id"]
    ).eq("user_id", user.id).maybe_single().execute()

    if not project.data:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Enforce single main contact per project
    if body.is_main_contact is True:
        supabase.table(TABLE_CONTACTS).update({"is_main_contact": False}).eq(
            "project_id", contact.data["project_id"]
        ).execute()

    # Only update fields that were explicitly sent in the request
    update = body.model_dump(exclude_unset=True)
    if not update:
        return {"ok": True}

    supabase.table(TABLE_CONTACTS).update(update).eq("id", contact_id).execute()
    return {"ok": True}
