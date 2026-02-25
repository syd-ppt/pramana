"""Claude Code provider using Claude Agent SDK (for subscription users)."""

from __future__ import annotations

import logging
import time
from unittest.mock import patch

from pramana.providers.base import BaseProvider
from pramana.providers.registry import register

logger = logging.getLogger(__name__)


def _make_patched_parser() -> object:
    """Build a patched parse_message that skips unknown event types.

    The SDK raises MessageParseError on unrecognized message types like
    rate_limit_event. The patched version converts them to SystemMessage,
    making the parser forward-compatible with new CLI event types.

    Returns a callable that can replace parse_message via unittest.mock.patch.
    """
    from claude_agent_sdk._internal.message_parser import (
        MessageParseError,
    )
    from claude_agent_sdk._internal.message_parser import (
        parse_message as _original,
    )
    from claude_agent_sdk.types import SystemMessage

    def _patched(data: dict) -> object:
        try:
            return _original(data)
        except MessageParseError as exc:
            if "Unknown message type" in str(exc):
                msg_type = data.get("type", "unknown")
                logger.debug("Skipping unrecognized SDK event type: %s", msg_type)
                return SystemMessage(subtype=msg_type, data=data)
            raise

    return _patched


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
        from claude_agent_sdk import query
        from claude_agent_sdk.types import AssistantMessage, ClaudeAgentOptions

        if temperature != 1.0 or seed is not None:
            logger.warning(
                "Claude Code ignores temperature/seed — "
                "results will NOT be reproducible (model=%s)",
                self.model_id,
            )

        start_ms = int(time.time() * 1000)

        prompt = input_text
        opts_kwargs: dict[str, object] = {
            "model": self.model_id,
            "permission_mode": "bypassPermissions",
            "max_turns": 1,
        }
        if system_prompt:
            opts_kwargs["system_prompt"] = system_prompt
        options = ClaudeAgentOptions(**opts_kwargs)

        response_text = None
        try:
            with patch(
                "claude_agent_sdk._internal.client.parse_message",
                _make_patched_parser(),
            ):
                async for msg in query(prompt=prompt, options=options):
                    if isinstance(msg, AssistantMessage) and response_text is None:
                        if msg.content:
                            response_text = "".join(
                                block.text
                                for block in msg.content
                                if hasattr(block, "text")
                            )
        except Exception as e:
            raise RuntimeError(f"Claude Code query failed: {e}") from e

        if response_text is None:
            raise RuntimeError("No response received from Claude Code")

        latency_ms = int(time.time() * 1000) - start_ms
        return response_text, latency_ms

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars per token)."""
        return len(text) // 4
