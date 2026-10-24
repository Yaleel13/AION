"""Secretless local reasoning-provider discovery for AION OS."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_LOCAL_MODEL = "aion:latest"
DEFAULT_LOCAL_CONTEXT = 4096
STATUS_TIMEOUT_SECONDS = 0.35


def local_runtime_enabled() -> bool:
    """Return whether AION is explicitly running in local OS mode."""
    return (os.getenv("AION_RUNTIME_MODE") or "").strip().lower() == "local"


def ollama_base_url() -> str:
    """Return the configured Ollama base URL with a secretless loopback default."""
    return (os.getenv("AION_OLLAMA_URL") or DEFAULT_OLLAMA_URL).strip().rstrip("/")


def local_model_name() -> str:
    """Return the selected local model name."""
    return (os.getenv("AION_LOCAL_MODEL") or DEFAULT_LOCAL_MODEL).strip() or DEFAULT_LOCAL_MODEL


def local_context_size() -> int:
    """Return a bounded positive context size, falling back safely on invalid input."""
    raw = (os.getenv("AION_LOCAL_CONTEXT") or str(DEFAULT_LOCAL_CONTEXT)).strip()
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_LOCAL_CONTEXT
    return value if value > 0 else DEFAULT_LOCAL_CONTEXT


def _safe_endpoint(value: str) -> str:
    """Return a display-safe endpoint that cannot leak URL credentials or paths."""
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.hostname:
        return DEFAULT_OLLAMA_URL
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{host}{port}"


def _probe_models(base_url: str, timeout: float = STATUS_TIMEOUT_SECONDS) -> tuple[bool, list[str], str | None]:
    request = Request(f"{base_url}/api/tags", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL is owner-controlled runtime config
            payload = json.load(response)
    except Exception as exc:  # noqa: BLE001 - status must fail closed without crashing
        return False, [], f"{type(exc).__name__}: {exc}"

    models = payload.get("models") if isinstance(payload, dict) else None
    names: list[str] = []
    if isinstance(models, list):
        for item in models:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("model")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
    return True, names, None


def local_intelligence_status() -> dict[str, Any]:
    """Return a truthful, non-secret snapshot of local Ollama readiness.

    The probe is intentionally skipped outside ``AION_RUNTIME_MODE=local`` so
    cloud/serverless status calls never attempt to contact a developer laptop.
    """
    enabled = local_runtime_enabled()
    base_url = ollama_base_url()
    model = local_model_name()
    context = local_context_size()

    reachable = False
    installed_models: list[str] = []
    error: str | None = None
    if enabled:
        reachable, installed_models, error = _probe_models(base_url)

    model_installed = model in installed_models
    actionable = enabled and reachable and model_installed
    return {
        "enabled": enabled,
        "configured": True,
        "reachable": reachable,
        "model": model,
        "model_installed": model_installed,
        "actionable": actionable,
        "context": context,
        "secret_required": False,
        "endpoint": _safe_endpoint(base_url),
        "error": error,
    }
