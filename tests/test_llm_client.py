"""llm_client.py 测试 —— 不发真请求。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.llm_client import LLMClient, LLMNotAvailable


def test_default_models():
    assert LLMClient(backend="openai", api_key="x").model == "gpt-4o-mini"
    assert LLMClient(backend="anthropic", api_key="x").model == "claude-3-5-haiku-20241022"
    assert LLMClient(backend="deepseek", api_key="x").model == "deepseek-chat"


def test_deepseek_base_url():
    c = LLMClient(backend="deepseek", api_key="x")
    assert c.base_url == "https://api.deepseek.com/v1"


def test_openai_no_base_url():
    c = LLMClient(backend="openai", api_key="x")
    assert c.base_url is None


def test_is_available_with_key():
    assert LLMClient(backend="deepseek", api_key="sk-test").is_available()


def test_is_available_without_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert not LLMClient(backend="deepseek").is_available()


def test_chat_raises_without_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    c = LLMClient(backend="deepseek")
    with pytest.raises(LLMNotAvailable):
        c.chat("system", "user")


def test_env_key_picked_up(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-env")
    c = LLMClient(backend="deepseek")
    assert c.api_key == "sk-from-env"


def test_anthropic_uses_anthropic_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anth")
    c = LLMClient(backend="anthropic")
    assert c.api_key == "sk-anth"


def test_deepseek_falls_back_to_openai_env(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-shared")
    c = LLMClient(backend="deepseek")
    assert c.api_key == "sk-openai-shared"


def test_explicit_model_overrides_default():
    c = LLMClient(backend="openai", api_key="x", model="gpt-4o")
    assert c.model == "gpt-4o"
