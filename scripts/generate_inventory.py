#!/usr/bin/env python3
"""Generate aion-inventory.yaml from repository surfaces and runtime capability registry."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aion.capabilities import capability_registry  # noqa: E402
from aion.main import app  # noqa: E402


def _next_api_routes() -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    for path in sorted(ROOT.glob("app/api/**/route.ts")):
        rel = path.relative_to(ROOT)
        route_path = "/" + str(rel.parent).replace("app", "").replace("\\", "/")
        routes.append(
            {
                "path": route_path,
                "handler": str(rel),
                "methods": "GET,POST,PATCH,DELETE",
                "owner": "nextjs",
            }
        )
    return routes


def _vercel_python_functions() -> list[dict[str, str]]:
    functions: list[dict[str, str]] = []
    for path in sorted(ROOT.glob("api/**/*.py")):
        if path.name == "__init__.py":
            continue
        rel = path.relative_to(ROOT)
        route_guess = "/" + str(rel.with_suffix("")).replace("\\", "/")
        functions.append(
            {
                "path": route_guess,
                "file": str(rel),
                "runtime": "python",
                "owner": "vercel-python",
            }
        )
    return functions


def main() -> int:
    openapi = app.openapi()
    fastapi_routes = []
    for path, methods in sorted(openapi.get("paths", {}).items()):
        for method, operation in sorted(methods.items()):
            if method.startswith("x-"):
                continue
            fastapi_routes.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "operation_id": operation.get("operationId"),
                    "summary": operation.get("summary"),
                    "owner": "fastapi",
                }
            )

    capabilities = capability_registry()
    integrations = []
    for name, entry in sorted(capabilities["capabilities"].items()):
        integrations.append(
            {
                "name": name,
                "configured": entry["configured"],
                "read": entry["read"],
                "propose": entry["propose"],
                "approve": entry["approve"],
                "execute": entry["execute"],
                "scope": entry["scope"],
                "note": entry["note"],
            }
        )

    inventory = {
        "version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "repository": "Yaleel13/AION",
        "surfaces": {
            "fastapi_routes": fastapi_routes,
            "next_api_routes": _next_api_routes(),
            "vercel_python_functions": _vercel_python_functions(),
        },
        "integrations": integrations,
        "policy": {
            "capability_model": capabilities["policy"],
            "global_autonomy_switch": capabilities["global_autonomy_switch"],
        },
        "webhooks": [],
        "ci_checks": [
            "npm ci",
            "npm run lint",
            "npm run build",
            "npx tsc --noEmit",
            "python -m compileall -q aion api",
            "pytest tests/ -q",
            "python scripts/check_openapi_contract.py",
            "python scripts/check_inventory_contract.py",
            "pip-audit",
            "npm audit --audit-level=high",
            "secret-pattern-check",
        ],
    }

    output = ROOT / "aion-inventory.yaml"
    output.write_text(
        yaml.safe_dump(inventory, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
