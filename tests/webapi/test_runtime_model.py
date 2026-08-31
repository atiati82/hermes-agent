import pytest

from webapi import deps


def test_runtime_model_uses_hermes_model_env_when_config_model_is_empty(monkeypatch):
    monkeypatch.setattr(deps, "load_config", lambda: {"model": "", "provider": ""})
    monkeypatch.setenv("HERMES_MODEL", "openrouter:deepseek/deepseek-chat")

    assert deps.get_runtime_model() == "deepseek/deepseek-chat"


def test_runtime_model_defaults_to_deepseek_openrouter_when_unconfigured(monkeypatch):
    monkeypatch.setattr(deps, "load_config", lambda: {"model": "", "provider": ""})
    monkeypatch.delenv("HERMES_MODEL", raising=False)

    assert deps.get_runtime_model() == "deepseek/deepseek-chat"


def test_runtime_provider_falls_back_to_hermes_model_prefix(monkeypatch):
    monkeypatch.setattr(deps, "load_config", lambda: {"model": "", "provider": ""})
    monkeypatch.setenv("HERMES_MODEL", "openrouter:deepseek/deepseek-chat")
    monkeypatch.setattr(deps, "_gateway_resolve_runtime_agent_kwargs", None)

    assert deps.get_runtime_agent_kwargs()["provider"] == "openrouter"


@pytest.mark.asyncio
async def test_v1_models_advertises_canonical_runtime_model(monkeypatch):
    from webapi.routes import models

    monkeypatch.setattr(deps, "load_config", lambda: {"model": "", "provider": ""})
    monkeypatch.setenv("HERMES_MODEL", "openrouter:deepseek/deepseek-chat")

    response = await models.list_models()

    assert response["data"][0]["runtime_model"] == "deepseek/deepseek-chat"
    assert response["data"][1]["id"] == "deepseek/deepseek-chat"
