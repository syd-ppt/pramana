"""OpenAI API provider."""

import logging
import os
import time

import httpx
import openai
from openai import AsyncOpenAI

from pramana.providers.base import BaseProvider
from pramana.providers.registry import register

logger = logging.getLogger(__name__)

# Models that reject temperature/seed — learned at runtime, avoids repeat 400s
_UNSUPPORTED_PARAMS_MODELS: set[str] = set()


@register("openai", "api", env_key="OPENAI_API_KEY")
class OpenAIProvider(BaseProvider):
    """OpenAI API adapter."""

    def __init__(self, model_id: str, api_key: str | None = None):
        self.model_id = model_id
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        self.client = AsyncOpenAI(
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
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": input_text})

        start_ms = int(time.time() * 1000)

        kwargs: dict[str, object] = {
            "model": self.model_id,
            "messages": messages,
            "max_completion_tokens": 1000,
        }

        if self.model_id in _UNSUPPORTED_PARAMS_MODELS:
            # Already know this model rejects temperature/seed
            pass
        else:
            kwargs["temperature"] = temperature
            kwargs["seed"] = seed

        try:
            response = await self.client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
        except openai.BadRequestError as exc:
            if "temperature" in str(exc) or "seed" in str(exc):
                _UNSUPPORTED_PARAMS_MODELS.add(self.model_id)
                logger.warning(
                    "Model %s rejected temperature/seed params — "
                    "results will NOT be reproducible",
                    self.model_id,
                )
                kwargs.pop("temperature", None)
                kwargs.pop("seed", None)
                response = await self.client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
            else:
                raise

        latency_ms = int(time.time() * 1000) - start_ms
        output = response.choices[0].message.content or ""

        return output, latency_ms

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars per token)."""
        return len(text) // 4
