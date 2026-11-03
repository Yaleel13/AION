"""Exercise the reused owner handlers through the actual local runtime router."""

import importlib

import httpx
import pytest

from aion.local_owner_api import OWNER_APIS, OWNER_METHODS
from aion.main import app


@pytest.fixture(autouse=True)
def local_owner(monkeypatch, tmp_path):
    from aion.phase2_services import reset_services_cache

    reset_services_cache()
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "test-owner")
    monkeypatch.setenv("AION_DATABASE_URL", "")
    monkeypatch.setenv("AION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AION_PHASE2_DB", str(tmp_path / "phase2.sqlite"))
    monkeypatch.setenv("AION_PAPER_DB", str(tmp_path / "paper.sqlite"))
    monkeypatch.setenv("MOLTBOOK_MODE", "mock")
    monkeypatch.setenv("MOLTBOOK_OUTBOUND_ENABLED", "false")
    monkeypatch.setenv("MOLTBOOK_EXECUTE_ENABLED", "false")
    monkeypatch.setenv("MOLTBOOK_CONTROLLED_AUTONOMY", "false")
    monkeypatch.setenv("MOLTBOOK_AUTONOMY_DRY_RUN", "true")
    yield
    reset_services_cache()


@pytest.mark.parametrize("name", OWNER_APIS)
async def test_authorized_local_reads(name):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/internal/" + name, headers={"Authorization": "Bearer test-owner"})
    if name == "acceptance":
        assert response.status_code == 503
        assert response.json()["detail"] == "Durable Postgres is not configured"
    else:
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


@pytest.mark.parametrize("name", OWNER_APIS)
async def test_unauthorized_never_enters_services(name, monkeypatch):
    module = importlib.import_module("api.internal." + name)

    def forbidden(*args, **kwargs):
        pytest.fail("Unauthorized request entered a service")

    for key in ["get_services", "build_runtime_status", "capability_registry", "build_outbound_gate_status", "database_url"]:
        if hasattr(module, key):
            monkeypatch.setattr(module, key, forbidden)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/internal/" + name)
        invalid = await client.get("/api/internal/" + name, headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
    assert invalid.status_code == 401


@pytest.mark.parametrize("mode,host,status", [("cloud", "127.0.0.1", 503), ("local", "192.0.2.1", 403)])
async def test_local_registration_fails_closed(mode, host, status, monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", mode)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(host, 123)), base_url="http://test") as client:
        for name in OWNER_APIS:
            response = await client.get("/api/internal/" + name, headers={"Authorization": "Bearer test-owner"})
            assert response.status_code == status


async def test_raw_post_still_requires_owner_token():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        for name in OWNER_APIS[3:]:
            response = await client.post("/api/internal/" + name, json={})
            assert response.status_code == 401


@pytest.mark.parametrize("method,name", [(method,name) for name,methods in OWNER_METHODS.items() for method in sorted(methods)] + [("POST","conversation")])
async def test_every_reachable_method_requires_runtime_authorization(method, name, monkeypatch):
    import aion.local_owner_api

    def forbidden(*args, **kwargs):
        pytest.fail("Unauthorized internal memory service reached")

    monkeypatch.setattr(aion.local_owner_api, "handle_local_memory", forbidden)
    body = {"action":"load","client_session_id":"test-internal-session-0001"} if name == "conversation" else {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        for token in [None, "Bearer invalid"]:
            response = await client.request(method, "/api/internal/"+name, headers={"Authorization":token} if token else {}, **({"json":body} if method=="POST" else {}))
            assert response.status_code == 401
            assert response.headers['content-type'].startswith('application/json')


async def test_authenticated_internal_conversation_uses_existing_local_service():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post('/api/internal/conversation', headers={"Authorization":"Bearer test-owner"}, json={"action":"load","client_session_id":"test-internal-session-0001"})
    assert response.status_code == 200
    assert response.json()['found'] is False


@pytest.mark.parametrize("action", ['load','append','search','remember','forget','replace','facts'])
async def test_every_internal_memory_action_requires_bearer(action, monkeypatch):
    import aion.local_owner_api

    def forbidden(*args, **kwargs):
        pytest.fail('Unauthorized internal memory operation reached the service')

    monkeypatch.setattr(aion.local_owner_api,'handle_local_memory',forbidden)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        response=await client.post('/api/internal/conversation',json={
            'action':action,'client_session_id':'test-internal-session-0001',
            'content':'test','replacement':'replacement','query':'test',
        })
    assert response.status_code==401


@pytest.mark.parametrize("method,name", [(method,name) for name,methods in OWNER_METHODS.items() for method in sorted(methods)] + [("POST","conversation")])
async def test_unexpected_upstream_errors_are_structured_and_redacted(method, name, monkeypatch):
    module = importlib.import_module('aion.local_owner_api' if name == 'conversation' else 'api.internal.'+name)

    def unavailable(*args, **kwargs):
        raise RuntimeError('private credential/connection details')

    for key in ['get_services','capability_registry','build_outbound_gate_status','database_url','handle_local_memory']:
        if hasattr(module,key):
            monkeypatch.setattr(module,key,unavailable)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        body = {'action':'load','client_session_id':'test-internal-session-0001'} if name=='conversation' else {}
        response = await client.request(method,'/api/internal/'+name,headers={'Authorization':'Bearer test-owner'},**({'json':body} if method=='POST' else {}))
    assert response.status_code == 500
    assert response.json() == {'detail':'Local owner service is temporarily unavailable.'}
    assert 'private' not in response.text


def test_registration_does_not_duplicate_docs_or_expose_unlisted_handlers():
    assert sum(getattr(route, "path", None) == "/openapi.json" for route in app.routes) == 1
    assert sum(getattr(route, "path", None) == "/docs" for route in app.routes) == 1
    internal = {path:set(methods) for path,methods in app.openapi()['paths'].items() if path.startswith('/api/internal/')}
    expected = {'/api/internal/'+name:{method.lower() for method in methods} for name,methods in OWNER_METHODS.items()}
    expected['/api/internal/conversation']={'post'}
    assert internal == expected
