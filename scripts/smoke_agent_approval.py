"""Run the isolated local agent approval and MCP redemption smoke check."""

from __future__ import annotations

import argparse
import asyncio
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys
import tempfile
from collections.abc import Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from aion.mcp_server import agent_stdio_environment
from smoke_owner_audit import (
    REQUEST_ID,
    assert_audit,
    local_environment,
    owner_audit,
    owner_session,
    owner_token,
    require_available_port,
    start_service,
    stop_service,
    wait_for,
    wait_for_port_release,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-port", type=int, default=8000)
    parser.add_argument("--boardroom-port", type=int, default=3001)
    return parser.parse_args()


def smoke_agent_credentials(owner: str) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    while hmac.compare_digest(token, owner):
        token = secrets.token_urlsafe(32)
    return token, "agent:smoke"


async def discover_tools(environment: Mapping[str, str]) -> list[str]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "aion.mcp_server"],
        env=dict(environment),
    )
    async with stdio_client(parameters) as streams:
        read, write = streams
        async with ClientSession(read, write) as mcp:
            await mcp.initialize()
            return [tool.name for tool in (await mcp.list_tools()).tools]


async def call_agent_tool(
    environment: Mapping[str, str],
    name: str,
    arguments: dict[str, str],
):
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "aion.mcp_server"],
        env=dict(environment),
    )
    async with stdio_client(parameters) as streams:
        read, write = streams
        async with ClientSession(read, write) as mcp:
            await mcp.initialize()
            return await mcp.call_tool(name, arguments)


def job_start_count(database: Path) -> int:
    with sqlite3.connect(database) as connection:
        return int(
            connection.execute(
                """
                SELECT COUNT(*) FROM audit_events
                WHERE module = 'capabilities' AND action = 'capability.job_started'
                """
            ).fetchone()[0]
        )


def assert_approval_audit(
    database: Path,
    approval_request_id: str,
    runtime_request_id: str,
) -> None:
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            """
            SELECT action, detail_json FROM audit_events
            WHERE module = 'capabilities'
            ORDER BY id ASC
            """
        ).fetchall()
    matching = [
        (action, json.loads(detail))
        for action, detail in rows
        if json.loads(detail).get("request_id") == runtime_request_id
    ]
    if [action for action, _ in matching] != [
        "capability.policy",
        "capability.job_started",
        "capability.outcome",
    ] or any(
        detail.get("approval_request_id") != approval_request_id
        for _, detail in matching
    ):
        raise RuntimeError("Approval and runtime audit records did not correlate.")


def assert_redemption_result(result: object, owner: str, agent: str) -> str:
    if getattr(result, "is_error", True):
        raise RuntimeError("Approved MCP redemption returned an error.")
    content = getattr(result, "structured_content", None)
    metadata = getattr(result, "meta", None) or {}
    request_id = metadata.get("aion/request_id")
    serialized = result.model_dump_json()
    if (
        not isinstance(content, dict)
        or content.get("ok") is not True
        or content.get("status") != "succeeded"
        or content.get("truncated") is not False
        or not isinstance(request_id, str)
        or not REQUEST_ID.fullmatch(request_id)
        or owner in serialized
        or agent in serialized
        or "output" in serialized
    ):
        raise RuntimeError("MCP redemption returned an invalid or unsafe response.")
    return request_id


async def approve(
    boardroom_url: str,
    cookie: str,
    execution_request_id: str,
) -> None:
    async with httpx.AsyncClient(base_url=boardroom_url, timeout=15, trust_env=False) as client:
        response = await client.post(
            f"/api/owner/runtime/syntax/approvals/{execution_request_id}",
            json={"approved": True},
            headers={
                "Cookie": cookie,
                "Origin": boardroom_url,
                "X-AION-Request": "1",
            },
        )
    data = response.json()
    if (
        response.status_code != 200
        or not isinstance(data, dict)
        or data.get("execution_request_id") != execution_request_id
        or data.get("decision") != "approved"
    ):
        raise RuntimeError("Boardroom did not approve the exact syntax request.")


async def run_check(
    runtime_port: int,
    boardroom_port: int,
    runtime_environment: Mapping[str, str],
    boardroom_environment: Mapping[str, str],
) -> dict[str, object]:
    runtime_url = f"http://127.0.0.1:{runtime_port}"
    boardroom_url = f"http://127.0.0.1:{boardroom_port}"
    owner = owner_token(runtime_environment, ".env")
    if not hmac.compare_digest(owner, owner_token(boardroom_environment, ".env.local")):
        raise RuntimeError(".env and .env.local must use the same AION_OWNER_TOKEN.")
    agent, principal = smoke_agent_credentials(owner)

    with tempfile.TemporaryDirectory(prefix="aion-agent-approval-smoke-") as directory:
        temporary = Path(directory)
        database = temporary / "phase2.sqlite3"
        runtime_env = dict(runtime_environment)
        runtime_env.pop("AION_DATABASE_URL", None)
        runtime_env.update(
            {
                "AION_DATA_DIR": str(temporary),
                "AION_LOCAL_AGENT_TOKEN": agent,
                "AION_LOCAL_AGENT_PRINCIPAL": principal,
                "AION_PHASE2_DB": str(database),
                "AION_PAPER_DB": str(temporary / "paper.sqlite3"),
            }
        )
        boardroom_env = dict(boardroom_environment)
        boardroom_env.pop("AION_LOCAL_AGENT_TOKEN", None)
        boardroom_env.pop("AION_LOCAL_AGENT_PRINCIPAL", None)
        runtime = start_service(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "run:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(runtime_port),
            ],
            runtime_env,
            temporary / "runtime.log",
        )
        boardroom = None
        try:
            await wait_for(f"{runtime_url}/docs", "Runtime")
            boardroom = start_service(
                ["npm", "run", "dev", "--", "--port", str(boardroom_port)],
                boardroom_env,
                temporary / "boardroom.log",
            )
            if boardroom.poll() is not None:
                raise RuntimeError("Boardroom exited before becoming ready.")
            await wait_for(f"{boardroom_url}/owner", "Boardroom")

            agent_env = agent_stdio_environment({"AION_LOCAL_AGENT_TOKEN": agent})
            if set(agent_env) != {"AION_MCP_MODE", "AION_LOCAL_AGENT_TOKEN"}:
                raise RuntimeError("Agent MCP environment contains unexpected variables.")
            owner_tools = await discover_tools(
                {"AION_MCP_MODE": "owner", "AION_OWNER_TOKEN": owner}
            )
            agent_tools = await discover_tools(agent_env)
            if owner_tools != ["runtime_status"] or agent_tools != [
                "runtime_syntax_approval_request",
                "runtime_syntax_approval_redeem",
            ]:
                raise RuntimeError("MCP discovery exposed an unexpected tool surface.")

            submission = await call_agent_tool(
                agent_env, "runtime_syntax_approval_request", {}
            )
            submission_data = submission.structured_content
            if (
                submission.is_error
                or not isinstance(submission_data, dict)
                or not isinstance(
                    execution_request_id := submission_data.get("execution_request_id"), str
                )
                or not REQUEST_ID.fullmatch(execution_request_id)
                or submission_data.get("state") != "pending"
            ):
                raise RuntimeError("Agent MCP submission did not create a pending request.")

            pending = await call_agent_tool(
                agent_env,
                "runtime_syntax_approval_redeem",
                {"execution_request_id": execution_request_id},
            )
            pending_request_id = (pending.meta or {}).get("aion/request_id")
            if (
                not pending.is_error
                or not isinstance(pending_request_id, str)
                or not REQUEST_ID.fullmatch(pending_request_id)
                or job_start_count(database) != 0
            ):
                raise RuntimeError("Pending MCP redemption was not safely denied.")

            cookie = owner_session(owner)
            pending_audit = assert_audit(
                await owner_audit(boardroom_url, cookie, pending_request_id),
                pending_request_id,
                "runtime.syntax",
                ["policy", "outcome"],
            )
            if pending_audit[-1].get("outcome") != "rejected":
                raise RuntimeError("Pending redemption audit did not record rejection.")

            await approve(boardroom_url, cookie, execution_request_id)
            redeemed = await call_agent_tool(
                agent_env,
                "runtime_syntax_approval_redeem",
                {"execution_request_id": execution_request_id},
            )
            runtime_request_id = assert_redemption_result(redeemed, owner, agent)
            if job_start_count(database) != 1:
                raise RuntimeError("Approved MCP redemption did not start exactly one job.")

            successful_audit = assert_audit(
                await owner_audit(boardroom_url, cookie, runtime_request_id),
                runtime_request_id,
                "runtime.syntax",
                ["policy", "job_started", "outcome"],
            )
            if successful_audit[-1].get("outcome") != "succeeded":
                raise RuntimeError("Approved redemption audit did not record success.")
            assert_approval_audit(database, execution_request_id, runtime_request_id)

            replay = await call_agent_tool(
                agent_env,
                "runtime_syntax_approval_redeem",
                {"execution_request_id": execution_request_id},
            )
            if not replay.is_error or job_start_count(database) != 1:
                raise RuntimeError("Replayed MCP redemption was not safely denied.")
            return {
                "owner_mcp_discovery": owner_tools,
                "agent_mcp_discovery": agent_tools,
                "pending_redemption": "denied_without_job",
                "approved_redemption": "succeeded_once",
                "replay_redemption": "denied_without_second_job",
                "audit_correlation": "verified",
            }
        finally:
            if boardroom is not None:
                stop_service(boardroom)
            stop_service(runtime)
            await wait_for_port_release(boardroom_port)
            await wait_for_port_release(runtime_port)


def main() -> None:
    args = parse_args()
    if args.runtime_port == args.boardroom_port:
        raise RuntimeError("Runtime and Boardroom ports must differ.")
    require_available_port(args.runtime_port)
    require_available_port(args.boardroom_port)
    runtime_environment = local_environment(
        ".env",
        {
            "AION_RUNTIME_MODE": "local",
            "APP_HOST": "127.0.0.1",
            "APP_PORT": str(args.runtime_port),
            "PORT": str(args.runtime_port),
        },
    )
    boardroom_environment = local_environment(
        ".env.local",
        {
            "AION_RUNTIME_MODE": "local",
            "AION_RUNTIME_URL": f"http://127.0.0.1:{args.runtime_port}",
        },
    )
    print(
        json.dumps(
            asyncio.run(
                run_check(
                    args.runtime_port,
                    args.boardroom_port,
                    runtime_environment,
                    boardroom_environment,
                )
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
