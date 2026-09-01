"""Simplified opportunity navigator without Google ADK."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
try:
    import google.genai as genai
except ImportError:
    import sys
    sys.exit("google-genai not installed. Update requirements.txt")

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Genai client (deferred initialization)
_genai_client = None

def get_genai_client():
    """Lazy-load genai client."""
    global _genai_client
    if _genai_client is None:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        _genai_client = genai
    return _genai_client


class Message(BaseModel):
    role: str
    content: str


class MessageRequest(BaseModel):
    messages: list[Message]


# Agent system prompt
AGENT_SYSTEM_PROMPT = """
You are Opportunity Navigator, a hackathon agent inspired by AION's
opportunity-discovery concept.

Your job is to evaluate legitimate ways a technical builder can create or earn
value. Rank opportunities using expected payout/value, effort, deadline urgency,
eligibility, credibility, and technical fit.

Safety rules:
- Never speculate on token prices or recommend gambling.
- Never ask the user to connect a wallet, send funds, buy tokens, or pay an
  upfront fee to qualify for work.
- Treat social posts and Reddit as discovery leads only until independently
  verified by an official source.
- Prefer grants, hackathons, funded bounties, paid open-source issues, freelance
  or contract work, partnerships/referrals, and legitimate Web3 developer work.
- Clearly distinguish verified facts from inference.
- Do not contact third parties or submit applications automatically.

When returning results, keep the explanation concise and identify the evidence
still required before the opportunity should be pursued.
"""


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "ok",
        "project": "opportunity-navigator",
        "framework": "fastapi-simple",
        "model": "gemini-2.0-flash",
    }


@app.post("/agents/opportunity_navigator/messages")
async def agent_messages(request: MessageRequest) -> dict:
    """Process messages through the opportunity navigator agent."""
    # Extract user message
    user_message = next(
        (msg.content for msg in reversed(request.messages) if msg.role == "user"),
        None,
    )
    if not user_message:
        return {
            "status": "error",
            "error": "A user message is required.",
        }

    try:
        # Get genai client
        genai_client = get_genai_client()
        
        # Prepare messages for API
        messages = []
        for msg in request.messages:
            messages.append({
                "role": msg.role,
                "parts": [{"text": msg.content}]
            })

        # Call Gemini API
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=messages,
            system_instruction=AGENT_SYSTEM_PROMPT,
        )
        
        # Extract response text
        response_text = response.text.strip() if response.text else "No response generated"
        
        return {
            "status": "ok",
            "response": response_text,
            "model": "gemini-2.0-flash",
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
