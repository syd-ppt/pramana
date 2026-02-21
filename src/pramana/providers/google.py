"""Google Gemini API provider."""

from __future__ import annotations

import os
import time

from google import genai
from google.genai import types

from pramana.providers.base import BaseProvider
from pramana.providers.registry import register


@register("google", "api", env_key="GEMINI_API_KEY")
class GoogleProvider(BaseProvider):
    """Google Gemini API adapter."""

    def __init__(self, model_id: str, api_key: str | None = None) -> None:
        self.model_id = model_id
        api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")

        self.client = genai.Client(api_key=api_key)

    async def complete(
        self,
        input_text: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> tuple[str, int]:
        """Execute completion via Gemini API."""
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=1000,
        )

        if system_prompt:
            config.system_instruction = system_prompt

        if seed is not None:
            config.seed = seed

        start_ms = int(time.time() * 1000)

        response = await self.client.aio.models.generate_content(
            model=self.model_id,
            contents=input_text,
            config=config,
        )

        latency_ms = int(time.time() * 1000) - start_ms
        output = response.text or ""

        return output, latency_ms

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars per token)."""
        return len(text) // 4
