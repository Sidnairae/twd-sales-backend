from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.lib.auth import get_current_user
from app.lib.supabase_client import get_admin_client

router = APIRouter()

class ContactUpdate(BaseModel):
    is_main_contact: Optional[bool] = None
    is_contractor_contact: Optional[bool] = None
    outreach_sentiment: Optional[str] = None
    outreach_notes: Optional[str] = None
    outreach_date: Optional[str] = None

@router.patch("/contacts/{contact_id}")
def update_contact(contact_id: str, body: ContactUpdate, user=Depends(get_current_user)):
    supabase = get_admin_client()

    contact = supabase.table("contacts").select("id, project_id").eq("id", contact_id).single().execute()
    if not contact.data:
        raise HTTPException(status_code=404, detail="Contact not found")

    project = supabase.table("projects").select("id").eq(
        "id", contact.data["project_id"]
    ).eq("user_id", user.id).single().execute()
    if not project.data:
        raise HTTPException(status_code=403, detail="Forbidden")

    if body.is_main_contact is True:
        supabase.table("contacts").update({"is_main_contact": False}).eq(
            "project_id", contact.data["project_id"]
        ).execute()

    update = {k: v for k, v in body.model_dump().items() if v is not None}
    if body.is_main_contact is False:
        update["is_main_contact"] = False

    supabase.table("contacts").update(update).eq("id", contact_id).execute()
    return {"ok": True}
