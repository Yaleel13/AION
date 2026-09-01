import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient


def _load_main():
    project_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(project_dir))
    spec = importlib.util.spec_from_file_location("opportunity_navigator_main", project_dir / "main.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeSessionService:
    async def create_session(self, **_kwargs):
        return SimpleNamespace(id="test-session")


class _FakeRunner:
    async def run_async(self, **_kwargs):
        yield SimpleNamespace(
            content=SimpleNamespace(parts=[SimpleNamespace(text="Ranked opportunity response")]),
            is_final_response=lambda: True,
        )


def test_agent_messages_returns_final_agent_response():
    module = _load_main()
    module.session_service = _FakeSessionService()
    module.runner = _FakeRunner()

    response = TestClient(module.app).post(
        "/agents/opportunity_navigator/messages",
        json={"messages": [{"role": "user", "content": "Rank safe opportunities."}]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "agent": "opportunity_navigator",
        "session_id": "test-session",
        "response": "Ranked opportunity response",
    }