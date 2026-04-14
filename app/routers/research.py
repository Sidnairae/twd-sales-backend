"""
research.py — web research + AI intelligence report for a project.

Searches Bing for recent news on the project, then asks Claude to produce
a structured BD intelligence report.  Results are cached in the database
for RESEARCH_CACHE_MAX_AGE_DAYS days to avoid redundant API calls.

Requires BING_SEARCH_API_KEY to be set in the environment.
Returns HTTP 503 with a clear message if the key is not configured.
"""

import os
import logging
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import (
    TABLE_PROJECTS,
    TABLE_RESEARCH_CACHE,
    CLAUDE_SMART_MODEL,
    ENV_BING_KEY,
    RESEARCH_CACHE_MAX_AGE_DAYS,
)
from app.lib.auth import get_current_user
from app.lib.clients import get_admin_client, get_anthropic_client

logger = logging.getLogger(__name__)
router  = APIRouter()

BING_SEARCH_URL = "https://api.bing.microsoft.com/v7.0/search"


class ResearchRequest(BaseModel):
    project_id: str


def _run_bing_search(query: str, api_key: str) -> str:
    """
    Search Bing and return formatted snippet text for the top results.
    Raises HTTP 502/504 on network or API errors so the caller gets a
    clean error response rather than a 500.
    """
    try:
        resp = httpx.get(
            BING_SEARCH_URL,
            headers={"Ocp-Apim-Subscription-Key": api_key},
            params={"q": query, "count": 5, "responseFilter": "Webpages"},
            timeout=15,
        )
        resp.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Bing Search timed out — try again.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Bing Search returned an error ({e.response.status_code}).",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Bing Search unreachable: {e}")

    pages = resp.json().get("webPages", {}).get("value", [])
    if not pages:
        return "No recent web results found for this project."

    return "\n\n".join(
        f"**{p.get('name', 'Result')}**\n{p.get('snippet', '')}"
        for p in pages
    )


def _is_cache_fresh(searched_at: str | None) -> bool:
    """Return True if the cached result is still within the max age window."""
    if not searched_at:
        return False
    try:
        age = datetime.utcnow() - datetime.fromisoformat(searched_at.replace("Z", ""))
        return age < timedelta(days=RESEARCH_CACHE_MAX_AGE_DAYS)
    except (ValueError, TypeError):
        return False


@router.post("/research")
def research(body: ResearchRequest, user=Depends(get_current_user)):
    """
    Generate a BD intelligence report for a project.

    - Returns a cached report if one exists and is still fresh.
    - Otherwise runs a Bing search, generates a Claude report, and caches it.
    - Requires BING_SEARCH_API_KEY — returns 503 if not configured.
    """
    bing_key = os.getenv(ENV_BING_KEY, "").strip()
    if not bing_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "Research feature is not configured. "
                "Set BING_SEARCH_API_KEY in the environment to enable it."
            ),
        )

    supabase = get_admin_client()

    # Return cached result if still fresh
    cached = supabase.table(TABLE_RESEARCH_CACHE).select(
        "research_card, searched_at"
    ).eq("project_id", body.project_id).eq("user_id", user.id).maybe_single().execute()

    if cached.data and _is_cache_fresh(cached.data.get("searched_at")):
        return {
            "research_card": cached.data["research_card"],
            "cached":        True,
            "searched_at":   cached.data["searched_at"],
        }

    # Load project details
    project = supabase.table(TABLE_PROJECTS).select(
        "name, company_name, country, description, contractor_name"
    ).eq("id", body.project_id).eq("user_id", user.id).single().execute()

    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")

    p     = project.data
    query = f"{p['name']} {p['company_name']} marine engineering project {p['country']}"

    sources_text = _run_bing_search(query, bing_key)

    prompt = f"""You are a BD analyst for TWD, a marine engineering consultancy.
Based on the web research below, write a concise intelligence report on this project.

Project: {p['name']}
Company: {p['company_name']}
Country: {p['country']}

Web research findings:
{sources_text}

Write a structured report covering:
1. **Latest developments** (what is new or has changed recently)
2. **Contractor / engineering status** (who is involved)
3. **BD opportunity** (where TWD fits)
4. **Key intelligence** (signals useful for the BD team)

Be concise and factual. Flag anything that is uncertain or unverified.
"""

    msg = get_anthropic_client().messages.create(
        model=CLAUDE_SMART_MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    card = msg.content[0].text

    # Store / refresh cache
    supabase.table(TABLE_RESEARCH_CACHE).upsert(
        {
            "project_id":    body.project_id,
            "user_id":       user.id,
            "research_card": card,
        },
        on_conflict="project_id,user_id",
    ).execute()

    return {"research_card": card, "cached": False}
