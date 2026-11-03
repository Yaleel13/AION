import json
from types import SimpleNamespace

import httpx
import pytest

from aion import main
from aion.moltbook.store import Phase2Store
from tests.test_capability_audit import audit_store

ID = "0123456789abcdef0123456789abcdef"


@pytest.fixture
def lookup_store(audit_store, monkeypatch):
    monkeypatch.setattr(main, "get_services", lambda: SimpleNamespace(store=audit_store))
    return audit_store


async def lookup(request_id=ID, token="private-owner-credential"):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as client:
        return await client.get("/owner/audit", params={"request_id": request_id},
                                headers={"Authorization": f"Bearer {token}"} if token else {})


async def test_exact_lookup_finds_older_events_and_projects_only_safe_fields(lookup_store):
    for event in ["policy", "job_started", "outcome"]:
        lookup_store.append_audit(module="capabilities", action=f"capability.{event}", success=True, detail={
            "request_id": ID, "capability": "runtime.syntax", "policy_decision": "allowed",
            "outcome": "succeeded" if event == "outcome" else None,
            "output": "private-output", "token": "private-owner-credential", "body": "private-body",
        })
    for _ in range(125):
        lookup_store.append_audit(module="capabilities", action="capability.outcome", success=True,
                                  detail={"request_id": "a" * 32, "outcome": "failed"})
    response = await lookup()
    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == ID
    assert [event["event"] for event in data["events"]] == ["policy", "job_started", "outcome"]
    assert data["events"][-1]["outcome"] == "succeeded"
    for event in data["events"]:
        assert set(event) == {"capability", "policy_decision", "event", "outcome", "timestamp"}
    for private in ["private-output", "private-body", "private-owner-credential"]:
        assert private not in response.text


@pytest.mark.parametrize("request_id", ["", "A" * 32, "a" * 31, "a" * 33, "' OR 1=1 --"])
async def test_malformed_id_rejected_before_read(request_id, lookup_store, monkeypatch):
    monkeypatch.setattr(main, "get_services", lambda: pytest.fail("Malformed key reached store"))
    assert (await lookup(request_id)).status_code == 400


@pytest.mark.parametrize("token,status", [(None, 401), ("wrong", 403)])
async def test_id_is_never_authorization(token, status, lookup_store, monkeypatch):
    monkeypatch.setattr(main, "get_services", lambda: pytest.fail("Anonymous request reached store"))
    assert (await lookup(token=token)).status_code == status


async def test_missing_records_are_empty(lookup_store):
    response = await lookup()
    assert response.status_code == 200
    assert response.json() == {"request_id": ID, "events": []}


async def test_unavailable_reader_redacts_failures(lookup_store, monkeypatch):
    def unavailable(**kwargs):
        raise RuntimeError("private-owner-credential")
    monkeypatch.setattr(lookup_store, "list_audit", unavailable)
    response = await lookup()
    assert response.status_code == 503
    assert response.json() == {"detail": "Capability audit unavailable"}


def test_exact_filter_is_parameterized_on_postgres():
    calls = []
    class Connection:
        def execute(self, query, params):
            calls.append((query, params))
            return SimpleNamespace(fetchall=lambda: [])
    store = Phase2Store.__new__(Phase2Store)
    store.backend = "postgres"
    store._conn = Connection()
    assert store.list_audit(request_id=ID) == []
    query, params = calls[0]
    assert "detail_json::jsonb ->> 'request_id'" in query
    assert ID not in query
    assert params == ("capabilities", ID, 100)


async def test_real_http_run_can_be_looked_up_without_output(lookup_store):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app, client=("127.0.0.1", 123)), base_url="http://test") as client:
        run = await client.post("/local-executive/validate", json={}, headers={"Authorization": "Bearer private-owner-credential"})
    assert run.json()["status"] == "succeeded"
    response = await lookup(run.headers["x-aion-request-id"])
    events = response.json()["events"]
    assert [event["event"] for event in events] == ["policy", "job_started", "outcome"]
    assert events[-1]["outcome"] == "succeeded"
    assert "Runtime syntax valid" not in json.dumps(events)
