"""统一 LLM 客户端：openai / anthropic / deepseek 三 backend。

设计上完全独立于本仓库其余部分，方便单独单测。
"""
from __future__ import annotations

import os
from typing import Literal, Optional


LLMBackend = Literal["openai", "anthropic", "deepseek"]


class LLMNotAvailable(RuntimeError):
    pass


class LLMClient:
    def __init__(
        self,
        backend: LLMBackend = "deepseek",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.backend = backend
        self.timeout = timeout
        self.api_key = api_key or self._default_key(backend)
        self.base_url = base_url or self._default_base_url(backend)
        self.model = model or self._default_model(backend)

    @staticmethod
    def _default_key(backend: LLMBackend) -> Optional[str]:
        return {
            "openai": os.getenv("OPENAI_API_KEY"),
            "anthropic": os.getenv("ANTHROPIC_API_KEY"),
            "deepseek": os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"),
        }.get(backend)

    @staticmethod
    def _default_base_url(backend: LLMBackend) -> Optional[str]:
        return {"deepseek": "https://api.deepseek.com/v1"}.get(backend)

    @staticmethod
    def _default_model(backend: LLMBackend) -> str:
        return {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-haiku-20241022",
            "deepseek": "deepseek-chat",
        }.get(backend, "gpt-4o-mini")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def chat(self, system: str, user: str, temperature: float = 0.2) -> str:
        if not self.is_available():
            raise LLMNotAvailable(
                f"{self.backend} backend 缺 API key（环境变量 "
                f"{self.backend.upper()}_API_KEY）"
            )
        if self.backend == "anthropic":
            return self._call_anthropic(system, user, temperature)
        return self._call_openai_compat(system, user, temperature)

    def _call_openai_compat(self, system: str, user: str, temperature: float) -> str:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise LLMNotAvailable("缺 openai SDK：pip install openai") from e
        client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""

    def _call_anthropic(self, system: str, user: str, temperature: float) -> str:
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise LLMNotAvailable("缺 anthropic SDK：pip install anthropic") from e
        client = Anthropic(api_key=self.api_key, timeout=self.timeout)
        resp = client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text if resp.content else ""
