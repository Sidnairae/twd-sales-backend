"""
meeting_prep.py — generate a BD meeting preparation card for a project.

Uses Claude Sonnet to produce a structured card covering situation summary,
key questions, TWD value proposition, red flags, and next steps.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException

from app.config import TABLE_PROJECTS, TABLE_CONTACTS, CLAUDE_SMART_MODEL
from app.lib.auth import get_current_user
from app.lib.clients import get_admin_client, get_anthropic_client

logger = logging.getLogger(__name__)
router  = APIRouter()


@router.post("/meeting-prep/{project_id}")
def meeting_prep(project_id: str, user=Depends(get_current_user)):
    """
    Generate a meeting prep card for a specific project.
    Includes project context, key contacts, and AI-generated BD guidance.
    """
    supabase = get_admin_client()

    project = supabase.table(TABLE_PROJECTS).select("*").eq(
        "id", project_id
    ).eq("user_id", user.id).single().execute()

    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")

    p        = project.data
    contacts = supabase.table(TABLE_CONTACTS).select(
        "name, title, email"
    ).eq("project_id", project_id).execute()

    def fmt_contact(c: dict) -> str:
        email_part = f" — {c['email']}" if c.get("email") else ""
        return f"- {c['name']} ({c['title']}){email_part}"

    contact_list = (
        "\n".join(fmt_contact(c) for c in contacts.data or [])
        or "No contacts available"
    )

    prompt = f"""You are a BD strategist for TWD, a marine and offshore engineering consultancy.
Generate a meeting preparation card for this project.

Project: {p.get('name')}
Company: {p.get('company_name')}
Country: {p.get('country')}
Value: ${(p.get('project_value_usd') or 0) / 1e6:.1f}M
Status: {p.get('status')}
Execution: {p.get('execution_date') or 'Unknown'}
FID confirmed: {'Yes' if p.get('fid_detected') else 'No'}
Contractor: {p.get('contractor_name') or ('Selected' if p.get('contractor_detected') else 'Not selected')}

Description: {p.get('description') or 'No description available'}

Key Contacts:
{contact_list}

Provide:
1. **Situation** (2-3 sentences on project status and TWD opportunity)
2. **Key questions to ask**
3. **TWD value proposition** for this specific project
4. **Red flags / watch-outs**
5. **Suggested next steps**
"""

    msg = get_anthropic_client().messages.create(
        model=CLAUDE_SMART_MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return {"prep_card": msg.content[0].text}
