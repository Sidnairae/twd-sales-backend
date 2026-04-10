import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from anthropic import Anthropic
from tavily import TavilyClient
from app.lib.auth import get_current_user
from app.lib.supabase_client import get_admin_client

router = APIRouter()

class ResearchRequest(BaseModel):
    project_id: str

@router.post("/research")
def research(body: ResearchRequest, user=Depends(get_current_user)):
    supabase = get_admin_client()

    # Check cache first
    cached = supabase.table("research_cache").select("research_card, searched_at").eq(
        "project_id", body.project_id
    ).eq("user_id", user.id).maybe_single().execute()
    if cached.data:
        return {"research_card": cached.data["research_card"], "cached": True, "searched_at": cached.data["searched_at"]}

    project = supabase.table("projects").select(
        "name, company_name, country, description, contractor_name"
    ).eq("id", body.project_id).eq("user_id", user.id).single().execute()
    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")

    p = project.data
    query = f"{p['name']} {p['company_name']} marine engineering project {p['country']}"

    tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    results = tavily.search(query=query, search_depth="advanced", max_results=5)

    sources_text = "\n\n".join(
        f"**{r.get('title')}**\n{r.get('content', '')[:500]}"
        for r in results.get("results", [])
    )

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = f"""You are a BD analyst for TWD, a marine engineering consultancy.
Based on the web research below, write a concise intelligence report on this project.

Project: {p['name']}
Company: {p['company_name']}
Country: {p['country']}

Web research findings:
{sources_text}

Write a structured report covering:
1. **Latest developments** (what's new since GlobalData)
2. **Contractor/engineering status** (who is involved)
3. **BD opportunity** (where TWD fits)
4. **Key intelligence** (any useful signals for the BD team)

Be concise and factual. Flag anything uncertain.
"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    card = msg.content[0].text

    supabase.table("research_cache").upsert({
        "project_id": body.project_id,
        "user_id": user.id,
        "research_card": card,
    }, on_conflict="project_id,user_id").execute()

    return {"research_card": card, "cached": False}
