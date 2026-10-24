from __future__ import annotations

from fastapi.testclient import TestClient

from aion.local_memory import LocalMemoryRequest, handle_local_memory, local_memory_path
from run import app as local_app


client = TestClient(local_app, client=("127.0.0.1", 50000))
SESSION = "local-memory-test-session-0001"


def _request(action: str, **kwargs) -> LocalMemoryRequest:
    return LocalMemoryRequest(action=action, client_session_id=SESSION, **kwargs)


def test_append_and_load_local_conversation(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_DATA_DIR", str(tmp_path / "aion"))

    saved = handle_local_memory(
        _request(
            "append",
            messages=[
                {"role": "user", "content": "hello local AION"},
                {"role": "assistant", "content": "local memory online"},
            ],
            model="aion:latest",
            runtime="ollama-local",
        )
    )
    assert saved == {"saved": True, "message_count": 2}

    loaded = handle_local_memory(_request("load"))
    assert loaded["found"] is True
    assert loaded["model"] == "aion:latest"
    assert loaded["runtime"] == "ollama-local"
    assert loaded["messages"] == [
        {"role": "user", "content": "hello local AION"},
        {"role": "assistant", "content": "local memory online"},
    ]
    assert local_memory_path().exists()


def test_remember_search_replace_and_forget(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_DATA_DIR", str(tmp_path / "aion"))

    remembered = handle_local_memory(
        _request(
            "remember",
            content="The owner prefers local-first operation.",
            category="preference",
            source_message_content="Remember that I prefer local-first operation.",
        )
    )
    assert remembered["remembered"] is True

    duplicate = handle_local_memory(
        _request(
            "remember",
            content="The owner prefers local-first operation.",
            category="preference",
        )
    )
    assert duplicate["deduplicated"] is True

    search = handle_local_memory(_request("search", query="local-first", limit=8))
    assert any("local-first" in fact["content"] for fact in search["facts"])

    replaced = handle_local_memory(
        _request(
            "replace",
            content="The owner prefers local-first operation.",
            replacement="The owner requires local-first operation for AION OS.",
            category="constraint",
        )
    )
    assert replaced["replaced"] is True
    assert replaced["exact_match"] is True

    forgotten = handle_local_memory(
        _request(
            "forget",
            content="The owner requires local-first operation for AION OS.",
        )
    )
    assert forgotten["exact_match"] is True
    assert forgotten["forgotten"] == 1

    active = handle_local_memory(_request("facts"))
    assert active["facts"] == []

    all_facts = handle_local_memory(_request("facts", include_inactive=True))
    statuses = {fact["status"] for fact in all_facts["facts"]}
    assert statuses == {"superseded", "forgotten"}


def test_local_memory_endpoint_is_secretless_in_local_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_DATA_DIR", str(tmp_path / "aion"))
    monkeypatch.delenv("AION_OWNER_TOKEN", raising=False)

    response = client.post(
        "/local-memory",
        json={"action": "load", "client_session_id": SESSION},
    )

    assert response.status_code == 200
    assert response.json() == {
        "found": False,
        "messages": [],
        "previous_response_id": None,
    }


def test_local_memory_endpoint_disabled_outside_local_mode(tmp_path, monkeypatch):
    monkeypatch.delenv("AION_RUNTIME_MODE", raising=False)
    monkeypatch.setenv("AION_DATA_DIR", str(tmp_path / "aion"))

    response = client.post(
        "/local-memory",
        json={"action": "load", "client_session_id": SESSION},
    )

    assert response.status_code == 503
