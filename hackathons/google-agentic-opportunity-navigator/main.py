from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from opportunity_navigator.agent import root_agent

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str
    content: str


class MessageRequest(BaseModel):
    messages: list[Message]


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "project": "opportunity-navigator",
        "framework": "fastapi-direct",
        "model": "gemini-3.7-flash",
    }


@app.post("/agents/opportunity_navigator/messages")
async def agent_messages(request: MessageRequest) -> dict:
    """Process messages through the opportunity navigator agent."""
    try:
        # Convert messages to format expected by the agent
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # For now, return a simple response indicating the agent is working
        return {
            "status": "ok",
            "agent": "opportunity_navigator",
            "message_count": len(messages),
            "response": "Agent endpoint is ready. Please implement agent.agenerate() call here."
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
