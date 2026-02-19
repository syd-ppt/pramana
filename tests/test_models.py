"""Tests for dynamic model registry."""

import pytest

from pramana.models import (
    FALLBACK_MODELS,
    detect_provider,
    get_available_models,
    get_example_models,
)


def test_get_available_models_returns_dict():
    """Should return dict with provider keys."""
    models = get_available_models()
    assert isinstance(models, dict)
    assert "openai" in models
    assert "anthropic" in models
    assert "google" in models


def test_get_available_models_contains_lists():
    """Each provider should have a list of model IDs."""
    models = get_available_models()
    for provider, model_list in models.items():
        assert isinstance(model_list, list)
        assert len(model_list) > 0
        for model_id in model_list:
            assert isinstance(model_id, str)


def test_detect_provider_openai():
    """Should detect OpenAI models."""
    assert detect_provider("gpt-5.2") == "openai"
    assert detect_provider("gpt-4o") == "openai"
    assert detect_provider("o3-mini") == "openai"


def test_detect_provider_anthropic():
    """Should detect Anthropic models."""
    assert detect_provider("claude-opus-4.6") == "anthropic"
    assert detect_provider("claude-sonnet-5") == "anthropic"


def test_detect_provider_google():
    """Should detect Google models."""
    assert detect_provider("gemini-3-flash") == "google"
    assert detect_provider("gemini-2.5-pro") == "google"


def test_detect_provider_unknown():
    """Should raise ValueError for unknown models."""
    with pytest.raises(ValueError, match="Unknown model"):
        detect_provider("llama-3.3-70b")


def test_get_example_models():
    """Should return list of example model IDs."""
    examples = get_example_models()
    assert isinstance(examples, list)
    assert len(examples) > 0
    assert len(examples) <= 3


def test_get_example_models_count():
    """Should respect count parameter."""
    examples = get_example_models(count=2)
    assert len(examples) <= 2


def test_fallback_models_structure():
    """Fallback models should have correct structure."""
    assert isinstance(FALLBACK_MODELS, dict)
    assert "openai" in FALLBACK_MODELS
    assert "anthropic" in FALLBACK_MODELS
    assert "google" in FALLBACK_MODELS

    # Should contain current Feb 2026 models
    assert "gpt-5.2" in FALLBACK_MODELS["openai"]
    assert "claude-opus-4.6" in FALLBACK_MODELS["anthropic"]
    assert "gemini-3-flash" in FALLBACK_MODELS["google"]


def test_cache_behavior():
    """Should cache results for 24h."""
    # First call fetches
    models1 = get_available_models()

    # Second call uses cache
    models2 = get_available_models()

    # Should return same object (cached)
    assert models1 is models2

    # Force refresh should fetch new
    models3 = get_available_models(force_refresh=True)

    # May or may not be same depending on upstream changes
    assert isinstance(models3, dict)
