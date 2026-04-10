import os
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from anthropic import Anthropic
from app.lib.auth import get_current_user

router = APIRouter()

class SummarizeRequest(BaseModel):
    description: str

@router.post("/summarize")
def summarize(body: SummarizeRequest, user=Depends(get_current_user)):
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
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
