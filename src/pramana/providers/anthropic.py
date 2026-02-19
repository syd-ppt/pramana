"""Anthropic API provider."""

import os
import time

import httpx
from anthropic import AsyncAnthropic

from pramana.providers.base import BaseProvider
from pramana.providers.registry import register


@register("anthropic", "api", env_key="ANTHROPIC_API_KEY")
class AnthropicProvider(BaseProvider):
    """Anthropic API adapter."""

    def __init__(self, model_id: str, api_key: str | None = None):
        self.model_id = model_id
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.client = AsyncAnthropic(
            api_key=api_key,
            http_client=httpx.AsyncClient(
                timeout=httpx.Timeout(60.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            ),
        )

    async def complete(
        self,
        input_text: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> tuple[str, int]:
        """Execute completion."""
        start_ms = int(time.time() * 1000)

        kwargs = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": input_text}],
            "temperature": temperature,
            "max_tokens": 1000,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        # IMPORTANT: Anthropic API does NOT support seed parameter (as of Feb 2026)
        # Parameter is accepted but silently ignored by API
        # Even with temperature=0, outputs are non-deterministic per official docs
        # See: https://docs.anthropic.com/en/api/messages
        # Keeping parameter in signature for API compatibility, but functionality is NO-OP
        if seed is not None:
            pass  # Seed parameter not supported by Anthropic API

        response = await self.client.messages.create(**kwargs)

        latency_ms = int(time.time() * 1000) - start_ms
        output = response.content[0].text if response.content else ""

        return output, latency_ms

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars per token)."""
        return len(text) // 4
