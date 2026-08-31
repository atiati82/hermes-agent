import os
import uuid
from functools import lru_cache
from typing import Any

from fastapi import HTTPException

from hermes_cli.config import load_config

CANONICAL_HERMES_MODEL = "openrouter:deepseek/deepseek-chat"
DEFAULT_RUNTIME_MODEL = "deepseek/deepseek-chat"
KNOWN_PROVIDER_PREFIXES = {
    "anti-api",
    "anthropic",
    "local",
    "nvidia",
    "ollama",
    "openrouter",
}


def _clean_string(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _extract_model_string(model_value) -> str:
    """Extract the model string from config, handling both str and dict formats.

    Config can be either:
      model: "claude-opus-4-6"                    # flat string
      model: { default: "claude-opus-4-6", provider: "anthropic" }  # nested dict
    """
    if isinstance(model_value, str):
        return model_value.strip()
    if isinstance(model_value, dict):
        return _clean_string(model_value.get("default")) or _clean_string(model_value.get("model"))
    return ""


def _provider_prefix(value: str) -> str:
    if ":" not in value:
        return ""
    prefix = value.split(":", 1)[0].strip().lower()
    return prefix if prefix in KNOWN_PROVIDER_PREFIXES else ""


def _normalize_runtime_model(raw: str) -> str:
    """Convert app-level provider IDs to the upstream model ID."""
    model = (raw or "").strip()
    prefix = _provider_prefix(model)
    if prefix:
        model = model.split(":", 1)[1].strip()
    if model.startswith("deepseek:") and "/" not in model.split(":", 1)[0]:
        model = model.replace(":", "/", 1)
    return model


def _extract_provider_string(config: dict) -> str:
    """Extract provider from config/env, including provider-prefixed model IDs."""
    model_value = config.get("model")
    if isinstance(model_value, dict):
        provider = _clean_string(model_value.get("provider"))
        if provider:
            return provider
        provider = _provider_prefix(_extract_model_string(model_value))
        if provider:
            return provider

    provider = _clean_string(config.get("provider"))
    if provider:
        return provider

    for env_name in ("HERMES_INFERENCE_PROVIDER", "HERMES_PROVIDER"):
        provider = os.getenv(env_name, "").strip()
        if provider:
            return provider

    for candidate in (_extract_model_string(model_value), os.getenv("HERMES_MODEL", ""), CANONICAL_HERMES_MODEL):
        provider = _provider_prefix(candidate)
        if provider:
            return provider

    return "openrouter"


try:
    from gateway.run import _resolve_runtime_agent_kwargs as _gateway_resolve_runtime_agent_kwargs
except ImportError:
    _gateway_resolve_runtime_agent_kwargs = None


def _resolve_model() -> str:
    config = load_config()
    raw = _extract_model_string(config.get("model")) or os.getenv("HERMES_MODEL", "") or CANONICAL_HERMES_MODEL
    return _normalize_runtime_model(raw) or DEFAULT_RUNTIME_MODEL


def _resolve_runtime_agent_kwargs() -> dict:
    config = load_config()
    provider = _extract_provider_string(config)
    if _gateway_resolve_runtime_agent_kwargs is None:
        return {"provider": provider}

    runtime = dict(_gateway_resolve_runtime_agent_kwargs())
    if not _clean_string(runtime.get("provider")):
        runtime["provider"] = provider
    return runtime


from hermes_state import SessionDB
from run_agent import AIAgent
from tools.memory_tool import MemoryStore


WEB_SOURCE = "web"


@lru_cache(maxsize=1)
def get_session_db() -> SessionDB:
    return SessionDB()


@lru_cache(maxsize=1)
def get_memory_store() -> MemoryStore:
    store = MemoryStore()
    store.load_from_disk()
    return store


def reload_memory_store() -> MemoryStore:
    store = get_memory_store()
    store.load_from_disk()
    return store


def get_config() -> dict[str, Any]:
    return load_config()


def get_runtime_model() -> str:
    """Return the configured model as a plain string, re-reading config each time.

    Some code paths return a dict {'default': '...', 'provider': '...'} instead
    of a bare string. We normalize here so callers always get a usable model ID.
    """
    raw = _resolve_model()
    return _normalize_runtime_model(_extract_model_string(raw)) or DEFAULT_RUNTIME_MODEL


def get_runtime_agent_kwargs() -> dict[str, Any]:
    """Return runtime kwargs (provider, base_url, etc.), always fresh."""
    return _resolve_runtime_agent_kwargs()


def create_agent(
    *,
    session_id: str,
    session_db: SessionDB,
    model: str | None = None,
    ephemeral_system_prompt: str | None = None,
    enabled_toolsets: list[str] | None = None,
    disabled_toolsets: list[str] | None = None,
    skip_context_files: bool = False,
    skip_memory: bool = False,
    stream_callback=None,
    tool_progress_callback=None,
    thinking_callback=None,
    reasoning_callback=None,
    step_callback=None,
) -> AIAgent:
    runtime_kwargs = get_runtime_agent_kwargs()
    effective_model = model or get_runtime_model()
    max_iterations = int(os.getenv("HERMES_MAX_ITERATIONS", "90"))

    return AIAgent(
        model=effective_model,
        **runtime_kwargs,
        max_iterations=max_iterations,
        quiet_mode=True,
        verbose_logging=False,
        ephemeral_system_prompt=ephemeral_system_prompt,
        session_id=session_id,
        platform="webapi",
        session_db=session_db,
        enabled_toolsets=enabled_toolsets,
        disabled_toolsets=disabled_toolsets,
        skip_context_files=skip_context_files,
        skip_memory=skip_memory,
        tool_progress_callback=tool_progress_callback,
        thinking_callback=thinking_callback,
        reasoning_callback=reasoning_callback,
        step_callback=step_callback,
    )


def get_session_or_404(session_id: str, session_db: SessionDB | None = None) -> dict[str, Any]:
    db = session_db or get_session_db()
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return session


def ensure_session_title(session_db: SessionDB, title: str | None) -> str | None:
    cleaned = session_db.sanitize_title(title)
    if cleaned:
        return cleaned
    return session_db.get_next_title_in_lineage("New Chat")


def new_session_id() -> str:
    return f"sess_{uuid.uuid4().hex}"
