"""Integration tests for provider implementations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pramana.providers.anthropic import AnthropicProvider
from pramana.providers.openai import OpenAIProvider

try:
    from pramana.providers.claude_code import ClaudeCodeProvider

    _has_claude_sdk = True
except ImportError:
    _has_claude_sdk = False


class TestOpenAIProvider:
    """Test OpenAI provider integration."""

    @pytest.mark.asyncio
    @patch("pramana.providers.openai.AsyncOpenAI")
    async def test_complete_simple_prompt(self, mock_client_class):
        """Should complete a simple string prompt."""
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="The answer is 42"))]

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = OpenAIProvider(model_id="gpt-4", api_key="sk-test123")
        result = await provider.complete("What is the answer?", temperature=0.0, seed=42)

        assert result[0] == "The answer is 42"
        mock_client.chat.completions.create.assert_called_once()

        # Verify parameters
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4"
        assert call_kwargs["temperature"] == 0.0
        assert call_kwargs["seed"] == 42

    @pytest.mark.asyncio
    @patch("pramana.providers.openai.AsyncOpenAI")
    async def test_complete_with_system_prompt(self, mock_client_class):
        """Should handle system prompt."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = OpenAIProvider(model_id="gpt-4", api_key="sk-test")
        result = await provider.complete(
            "Hello", system_prompt="You are helpful", temperature=0.0, seed=42
        )

        assert result[0] == "Response"

        # Verify messages built correctly
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["messages"] == [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]

    @pytest.mark.asyncio
    @patch("pramana.providers.openai.AsyncOpenAI")
    async def test_uses_env_api_key(self, mock_client_class, monkeypatch):
        """Should use OPENAI_API_KEY from environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        OpenAIProvider(model_id="gpt-4")

        # Should have initialized with env key
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args[1]
        assert call_kwargs["api_key"] == "sk-env-key"

    @pytest.mark.asyncio
    async def test_requires_api_key(self, monkeypatch):
        """Should raise error if no API key provided."""
        # Clear env var
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with pytest.raises(ValueError, match="OPENAI_API_KEY not set"):
            OpenAIProvider(model_id="gpt-4")


class TestAnthropicProvider:
    """Test Anthropic provider integration."""

    @pytest.mark.asyncio
    @patch("pramana.providers.anthropic.AsyncAnthropic")
    async def test_complete_simple_prompt(self, mock_client_class):
        """Should complete with Anthropic API."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Claude response")]

        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = AnthropicProvider(model_id="claude-opus-4-6", api_key="sk-ant-test")
        result = await provider.complete("Test prompt", temperature=0.0, seed=42)

        assert result[0] == "Claude response"
        mock_client.messages.create.assert_called_once()

        # Verify Anthropic-specific format
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-opus-4-6"
        assert call_kwargs["temperature"] == 0.0
        assert call_kwargs["max_tokens"] == 1000

    @pytest.mark.asyncio
    @patch("pramana.providers.anthropic.AsyncAnthropic")
    async def test_converts_string_to_messages(self, mock_client_class):
        """Should convert string prompt to Anthropic message format."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]

        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = AnthropicProvider(model_id="claude-opus-4-6", api_key="sk-ant-test")
        await provider.complete("Hello", temperature=0.0, seed=42)

        # Should convert to messages format
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["messages"] == [{"role": "user", "content": "Hello"}]

    @pytest.mark.asyncio
    @patch("pramana.providers.anthropic.AsyncAnthropic")
    async def test_complete_with_system_prompt(self, mock_client_class):
        """Should pass system prompt via Anthropic's system parameter."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]

        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = AnthropicProvider(model_id="claude-opus-4-6", api_key="sk-ant-test")
        await provider.complete("Hello", system_prompt="Be helpful", temperature=0.0, seed=42)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["messages"] == [{"role": "user", "content": "Hello"}]
        assert call_kwargs["system"] == "Be helpful"

    @pytest.mark.asyncio
    @patch("pramana.providers.anthropic.AsyncAnthropic")
    async def test_uses_env_api_key(self, mock_client_class, monkeypatch):
        """Should use ANTHROPIC_API_KEY from environment."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        AnthropicProvider(model_id="claude-opus-4-6")

        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args[1]
        assert call_kwargs["api_key"] == "sk-ant-env"

    @pytest.mark.asyncio
    async def test_requires_api_key(self, monkeypatch):
        """Should raise error if no API key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not set"):
            AnthropicProvider(model_id="claude-opus-4-6")


class TestProviderParameterHandling:
    """Test that providers handle parameters correctly."""

    @pytest.mark.asyncio
    @patch("pramana.providers.openai.AsyncOpenAI")
    async def test_openai_temperature_zero(self, mock_client_class):
        """OpenAI should enforce temperature=0 for reproducibility."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = OpenAIProvider(model_id="gpt-4", api_key="sk-test")
        await provider.complete("Test", temperature=0.0, seed=42)

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.0
        assert call_kwargs["seed"] == 42

    @pytest.mark.asyncio
    @patch("pramana.providers.anthropic.AsyncAnthropic")
    async def test_anthropic_accepts_seed_but_ignores(self, mock_client_class):
        """Anthropic accepts seed parameter but doesn't guarantee reproducibility."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Test")]

        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = AnthropicProvider(model_id="claude-opus-4-6", api_key="sk-ant-test")
        await provider.complete("Test", temperature=0.0, seed=42)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["temperature"] == 0.0
        # Anthropic doesn't have seed parameter - should not error


class TestProviderErrorHandling:
    """Test provider error handling."""

    @pytest.mark.asyncio
    @patch("pramana.providers.openai.AsyncOpenAI")
    async def test_openai_api_error(self, mock_client_class):
        """Should propagate OpenAI API errors."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error: Rate limit exceeded")
        )
        mock_client_class.return_value = mock_client

        provider = OpenAIProvider(model_id="gpt-4", api_key="sk-test")

        with pytest.raises(Exception, match="API Error"):
            await provider.complete("Test", temperature=0.0, seed=42)

    @pytest.mark.asyncio
    @patch("pramana.providers.anthropic.AsyncAnthropic")
    async def test_anthropic_api_error(self, mock_client_class):
        """Should propagate Anthropic API errors."""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("Anthropic error: Invalid API key")
        )
        mock_client_class.return_value = mock_client

        provider = AnthropicProvider(model_id="claude-opus-4-6", api_key="sk-ant-test")

        with pytest.raises(Exception, match="Invalid API key"):
            await provider.complete("Test", temperature=0.0, seed=42)


@pytest.mark.skipif(not _has_claude_sdk, reason="claude_agent_sdk not installed")
class TestClaudeCodeProvider:
    """Test Claude Code provider SDK error handling."""

    @pytest.mark.asyncio
    async def test_sdk_error_after_response_returns_captured(self):
        """Should return captured response when ClaudeSDKError fires after streaming."""
        claude_sdk = pytest.importorskip("claude_agent_sdk")
        from claude_agent_sdk.types import AssistantMessage

        provider = ClaudeCodeProvider(model_id="claude-haiku-4-5")

        async def mock_streaming():
            msg = MagicMock(spec=AssistantMessage)
            block = MagicMock()
            block.text = "Complete answer"
            msg.content = [block]
            yield msg
            raise claude_sdk.ClaudeSDKError("Unknown event type: rate_limit_event")

        with patch.object(claude_sdk, "query", return_value=mock_streaming()):
            result_text, latency = await provider.complete("Test prompt")
            assert result_text == "Complete answer"
            assert latency >= 0

    @pytest.mark.asyncio
    async def test_sdk_error_before_response_raises(self):
        """Should raise RuntimeError when ClaudeSDKError fires before any response."""
        claude_sdk = pytest.importorskip("claude_agent_sdk")

        provider = ClaudeCodeProvider(model_id="claude-haiku-4-5")

        async def error_immediately():
            raise claude_sdk.ClaudeSDKError("Unknown event type: rate_limit_event")
            yield  # make it an async generator  # noqa: RUF027

        with patch.object(claude_sdk, "query", return_value=error_immediately()):
            with pytest.raises(RuntimeError, match="unknown message type"):
                await provider.complete("Test prompt")

    @pytest.mark.asyncio
    async def test_generic_exception_raises_runtime_error(self):
        """Should wrap non-SDK exceptions in RuntimeError."""
        claude_sdk = pytest.importorskip("claude_agent_sdk")

        provider = ClaudeCodeProvider(model_id="claude-haiku-4-5")

        async def network_error():
            raise ConnectionError("Connection refused")
            yield  # noqa: RUF027

        with patch.object(claude_sdk, "query", return_value=network_error()):
            with pytest.raises(RuntimeError, match="Claude Code query failed"):
                await provider.complete("Test prompt")

    @pytest.mark.asyncio
    async def test_no_response_raises(self):
        """Should raise RuntimeError when stream completes with no AssistantMessage."""
        claude_sdk = pytest.importorskip("claude_agent_sdk")

        provider = ClaudeCodeProvider(model_id="claude-haiku-4-5")

        async def empty_stream():
            return
            yield  # noqa: RUF027

        with patch.object(claude_sdk, "query", return_value=empty_stream()):
            with pytest.raises(RuntimeError, match="No response received"):
                await provider.complete("Test prompt")


class TestProviderResponseParsing:
    """Test that providers correctly parse API responses."""

    @pytest.mark.asyncio
    @patch("pramana.providers.openai.AsyncOpenAI")
    async def test_openai_extracts_content(self, mock_client_class):
        """Should extract text content from OpenAI response."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="First choice")),
        ]

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = OpenAIProvider(model_id="gpt-4", api_key="sk-test")
        result = await provider.complete("Test", temperature=0.0, seed=42)

        # Should extract first choice content
        assert result[0] == "First choice"

    @pytest.mark.asyncio
    @patch("pramana.providers.anthropic.AsyncAnthropic")
    async def test_anthropic_extracts_text(self, mock_client_class):
        """Should extract text from Anthropic content blocks."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="Response text")
        ]

        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = AnthropicProvider(model_id="claude-opus-4-6", api_key="sk-ant-test")
        result = await provider.complete("Test", temperature=0.0, seed=42)

        assert result[0] == "Response text"
