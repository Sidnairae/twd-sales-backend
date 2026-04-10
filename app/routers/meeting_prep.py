import os
from fastapi import APIRouter, Depends, HTTPException
from anthropic import Anthropic
from app.lib.auth import get_current_user
from app.lib.supabase_client import get_admin_client

router = APIRouter()

@router.post("/meeting-prep/{project_id}")
def meeting_prep(project_id: str, user=Depends(get_current_user)):
    supabase = get_admin_client()
    project = supabase.table("projects").select("*").eq("id", project_id).eq(
        "user_id", user.id
    ).single().execute()
    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")

    p = project.data
    contacts = supabase.table("contacts").select("name, title, email").eq(
        "project_id", project_id
    ).execute()

    contact_list = "\n".join(
        f"- {c['name']} ({c['title']}){f' — {c[\"email\"]}' if c.get('email') else ''}"
        for c in contacts.data or []
    ) or "No contacts available"

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = f"""You are a BD strategist for TWD, a marine and offshore engineering consultancy.
Generate a meeting preparation card for this project.

Project: {p.get('name')}
Company: {p.get('company_name')}
Country: {p.get('country')}
Value: ${(p.get('project_value_usd') or 0) / 1e6:.1f}M
Status: {p.get('status')}
Execution: {p.get('execution_date') or 'Unknown'}
FID: {'Yes' if p.get('fid_detected') else 'No'}
Contractor: {p.get('contractor_name') or ('Selected' if p.get('contractor_detected') else 'Not selected')}

Description: {p.get('description') or 'No description'}

Key Contacts:
{contact_list}

Provide:
1. **Situation** (2-3 sentences on project status and TWD opportunity)
2. **Key questions to ask**
3. **TWD value proposition** for this specific project
4. **Red flags / watch-outs**
5. **Suggested next steps**
"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return {"prep_card": msg.content[0].text}
