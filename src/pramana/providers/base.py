"""Abstract provider interface for LLM APIs."""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Base class for LLM provider adapters."""

    @abstractmethod
    async def complete(
        self,
        input_text: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> tuple[str, int]:
        """Execute completion and return (output, latency_ms)."""
        ...

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        ...
