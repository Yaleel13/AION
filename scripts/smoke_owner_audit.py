"""Run the local Boardroom capability-audit smoke check."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx
from dotenv import dotenv_values
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REQUEST_ID = re.compile(r"[0-9a-f]{32}\Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-port", type=int, default=8000)
    parser.add_argument("--boardroom-port", type=int, default=3001)
    return parser.parse_args()


def require_available_port(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(f"Port {port} is already occupied; choose a free port.") from exc


async def wait_for_port_release(port: int) -> None:
    for _ in range(10):
        try:
            require_available_port(port)
            return
        except RuntimeError:
            await asyncio.sleep(1)
    raise RuntimeError(f"Check-owned service did not release port {port}.")


def local_environment(filename: str, overrides: Mapping[str, str]) -> dict[str, str]:
    path = ROOT / filename
    if not path.is_file():
        raise RuntimeError(f"{filename} is required for this local smoke check.")
    values = dotenv_values(path)
    environment = dict(os.environ)
    environment.update({key: value for key, value in values.items() if value is not None})
    environment.update(overrides)
    return environment


def owner_token(environment: Mapping[str, str], filename: str) -> str:
    token = environment.get("AION_OWNER_TOKEN", "").strip()
    if not token:
        raise RuntimeError(f"{filename} must configure AION_OWNER_TOKEN.")
    return token


def start_service(command: list[str], environment: Mapping[str, str], log: Path) -> subprocess.Popen[bytes]:
    with log.open("wb") as output:
        return subprocess.Popen(
            command,
            cwd=ROOT,
            env=dict(environment),
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )


def stop_service(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    # Each service has its own session, so this targets only check-owned children.
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)


async def wait_for(url: str, label: str) -> None:
    async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
        for _ in range(30):
            try:
                response = await client.get(url)
                if response.is_success:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(1)
    raise RuntimeError(f"{label} did not become ready.")


def owner_session(token: str) -> str:
    expires_at = int(time.time()) + 60
    signature = hmac.new(
        token.encode(),
        f"aion-owner-session-v1:{expires_at}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"aion_owner_session={expires_at}.{signature}"


def assert_audit(
    payload: object,
    request_id: str,
    capability: str,
    expected_events: list[str],
) -> list[dict[str, object]]:
    if not isinstance(payload, dict) or payload.get("request_id") != request_id:
        raise RuntimeError("Audit lookup did not return the requested runtime ID.")
    events = payload.get("events")
    if not isinstance(events, list):
        raise RuntimeError("Audit lookup returned an invalid events collection.")
    if [event.get("event") for event in events if isinstance(event, dict)] != expected_events:
        raise RuntimeError("Audit lookup events did not match the runtime operation.")
    if len(events) != len(expected_events) or any(
        not isinstance(event, dict)
        or event.get("capability") != capability
        or event.get("policy_decision") != "allowed"
        for event in events
    ):
        raise RuntimeError("Audit lookup returned invalid capability or policy records.")
    return events


async def owner_audit(
    boardroom_url: str,
    cookie: str,
    request_id: str,
) -> object:
    async with httpx.AsyncClient(base_url=boardroom_url, timeout=10, trust_env=False) as client:
        response = await client.get(
            "/api/owner/audit",
            params={"request_id": request_id},
            headers={"Cookie": cookie},
        )
    response.raise_for_status()
    return response.json()


async def run_check(
    runtime_port: int,
    boardroom_port: int,
    runtime_environment: Mapping[str, str],
    boardroom_environment: Mapping[str, str],
) -> dict[str, object]:
    runtime_url = f"http://127.0.0.1:{runtime_port}"
    boardroom_url = f"http://127.0.0.1:{boardroom_port}"
    token = owner_token(runtime_environment, ".env")
    if not hmac.compare_digest(token, owner_token(boardroom_environment, ".env.local")):
        raise RuntimeError(".env and .env.local must use the same AION_OWNER_TOKEN.")

    with tempfile.TemporaryDirectory(prefix="aion-owner-audit-smoke-") as logs:
        log_dir = Path(logs)
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
            runtime_environment,
            log_dir / "runtime.log",
        )
        boardroom: subprocess.Popen[bytes] | None = None
        try:
            boardroom = start_service(
                ["npm", "run", "dev", "--", "--port", str(boardroom_port)],
                boardroom_environment,
                log_dir / "boardroom.log",
            )
            await wait_for(f"{runtime_url}/docs", "Runtime")
            if boardroom.poll() is not None:
                raise RuntimeError("Boardroom exited before becoming ready.")
            await wait_for(f"{boardroom_url}/owner", "Boardroom")
            cookie = owner_session(token)
            async with httpx.AsyncClient(base_url=boardroom_url, timeout=45, trust_env=False) as client:
                syntax = await client.post(
                    "/api/owner/runtime/syntax",
                    content=b"{}",
                    headers={
                        "Content-Type": "application/json",
                        "Cookie": cookie,
                        "Origin": boardroom_url,
                        "X-AION-Request": "1",
                    },
                )
            request_id = syntax.headers.get("x-aion-request-id", "")
            data = syntax.json()
            if (
                syntax.status_code != 200
                or not REQUEST_ID.fullmatch(request_id)
                or not isinstance(data, dict)
                or data.get("status") != "succeeded"
            ):
                raise RuntimeError("Boardroom syntax bridge did not return a successful correlated response.")
            syntax_audit = assert_audit(
                await owner_audit(boardroom_url, cookie, request_id),
                request_id,
                "runtime.syntax",
                ["policy", "job_started", "outcome"],
            )
            if syntax_audit[-1].get("outcome") != "succeeded":
                raise RuntimeError("Boardroom syntax audit did not record a successful outcome.")

            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-m", "aion.mcp_server"],
                env=dict(runtime_environment),
            )
            async with stdio_client(parameters) as streams:
                read, write = streams
                async with ClientSession(read, write) as mcp:
                    await mcp.initialize()
                    discovery = await mcp.list_tools()
                    tools = [tool.name for tool in discovery.tools]
                    if tools != ["runtime_status"]:
                        raise RuntimeError("MCP discovery exposed tools other than runtime_status.")
                    status = await mcp.call_tool("runtime_status", {})
            if status.is_error:
                raise RuntimeError("runtime_status returned an MCP error.")
            mcp_request_id = (status.meta or {}).get("aion/request_id")
            if not isinstance(mcp_request_id, str) or not REQUEST_ID.fullmatch(mcp_request_id):
                raise RuntimeError("runtime_status did not return a valid metadata request ID.")
            mcp_audit = assert_audit(
                await owner_audit(boardroom_url, cookie, mcp_request_id),
                mcp_request_id,
                "runtime_status",
                ["policy", "outcome"],
            )
            if mcp_audit[-1].get("outcome") != "succeeded":
                raise RuntimeError("runtime_status audit did not record a successful outcome.")
            return {
                "boardroom_syntax_request_id": request_id,
                "boardroom_syntax_events": [event["event"] for event in syntax_audit],
                "mcp_discovery": tools,
                "mcp_request_id": mcp_request_id,
                "mcp_audit_request_id": mcp_request_id,
                "mcp_events": [event["event"] for event in mcp_audit],
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
    result = asyncio.run(
        run_check(
            args.runtime_port,
            args.boardroom_port,
            runtime_environment,
            boardroom_environment,
        )
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
