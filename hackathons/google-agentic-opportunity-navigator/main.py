from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from opportunity_navigator.agent import root_agent

app = FastAPI()
session_service = InMemorySessionService()
runner = Runner(
    app_name="opportunity_navigator",
    agent=root_agent,
    session_service=session_service,
)

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
    user_message = next(
        (message.content for message in reversed(request.messages) if message.role == "user"),
        None,
    )
    if not user_message:
        return {
            "status": "error",
            "error": "A user message is required.",
        }

    session = await session_service.create_session(
        app_name="opportunity_navigator",
        user_id="api_user",
    )
    response_text = None
    try:
        async for event in runner.run_async(
            user_id="api_user",
            session_id=session.id,
            new_message=types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_message)],
            ),
        ):
            if event.is_final_response() and event.content:
                response_text = "".join(
                    part.text for part in event.content.parts if part.text
                ).strip()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    if not response_text:
        return {
            "status": "error",
            "error": "The agent did not return a final response.",
        }

    return {
        "status": "ok",
        "agent": "opportunity_navigator",
        "session_id": session.id,
        "response": response_text,
    }
