"""
summarize.py — generate a short AI summary of a project description.

Uses Claude Haiku (fast and cheap) to distil a GlobalData description
into 2-3 actionable sentences for the BD team.
"""

import logging
from fastapi import APIRouter, Depends

from app.config import CLAUDE_FAST_MODEL
from app.lib.auth import get_current_user
from app.lib.clients import get_anthropic_client
from app.schemas import SummarizeRequest, SummarizeResponse

logger = logging.getLogger(__name__)
router  = APIRouter()


@router.post("/summarize", response_model=SummarizeResponse)
def summarize(body: SummarizeRequest, user=Depends(get_current_user)):
    """
    Summarise a project description into 2-3 concise sentences.
    Focuses on: contractor status, engineer involvement, and project stage.
    """
    msg = get_anthropic_client().messages.create(
        model=CLAUDE_FAST_MODEL,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": (
                "You are a BD assistant for TWD, a marine engineering consultancy. "
                "Summarize this project description in 2-3 concise sentences. Focus on: "
                "Is a contractor selected? Is an engineer named? What is the project status? "
                "Skip generic sentences. Be direct.\n\n"
                f"Description:\n{body.description}"
            ),
        }],
    )
    return {"summary": msg.content[0].text}
