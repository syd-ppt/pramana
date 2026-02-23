"""Claude Code provider using Claude Agent SDK (for subscription users)."""

import logging
import time

from pramana.providers.base import BaseProvider
from pramana.providers.registry import register

logger = logging.getLogger(__name__)


@register("anthropic", "subscription", sdk_package="claude_agent_sdk")
class ClaudeCodeProvider(BaseProvider):
    """Provider that uses Claude Agent SDK (Claude Code subscription)."""

    def __init__(self, model_id: str = "claude-opus-4-6", api_key: str | None = None):
        self.model_id = model_id
        # api_key ignored — subscription auth, kept for uniform constructor

    async def complete(
        self,
        input_text: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> tuple[str, int]:
        """Generate completion using Claude Code.

        Note: Claude Code uses temperature=1.0 by default and does not support
        parameter control. Results are non-deterministic.
        """
        from claude_agent_sdk import ClaudeSDKError, query
        from claude_agent_sdk.types import AssistantMessage

        start_ms = int(time.time() * 1000)

        prompt = input_text
        if system_prompt:
            prompt = f"System: {system_prompt}\n\nUser: {input_text}"

        response_text = None
        try:
            async for msg in query(prompt=prompt):
                if isinstance(msg, AssistantMessage) and response_text is None:
                    if msg.content:
                        response_text = "".join(
                            block.text for block in msg.content if hasattr(block, "text")
                        )
        except ClaudeSDKError as e:
            # SDK doesn't recognize newer event types (e.g. rate_limit_event).
            # If we already captured a response, use it; otherwise re-raise.
            if response_text is None:
                raise RuntimeError(
                    "Claude Code query failed: SDK encountered an unknown message type "
                    "before receiving a response. Upgrade claude_agent_sdk."
                ) from e
            logger.warning("ClaudeSDKError after response captured, returning partial result: %s", e)
        except Exception as e:
            raise RuntimeError(f"Claude Code query failed: {e}") from e

        if response_text is None:
            raise RuntimeError("No response received from Claude Code")

        latency_ms = int(time.time() * 1000) - start_ms
        return response_text, latency_ms

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars per token)."""
        return len(text) // 4
