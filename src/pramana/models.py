"""Dynamic model registry with fallback to static list."""

from datetime import datetime, timedelta
from typing import Dict, List

import httpx

# Cache for model list (24h TTL)
_cache: Dict = {"models": None, "fetched_at": None}

# Fallback static list (updated Feb 2026)
FALLBACK_MODELS = {
    "openai": [
        "gpt-5.3-codex",
        "gpt-5.2",
        "gpt-5",
        "gpt-4o",
        "o4-mini",
        "o3",
        "o3-mini",
        "o3-pro",
    ],
    "anthropic": [
        "claude-opus-4.6",
        "claude-sonnet-5",
        "claude-sonnet-4.5",
        "claude-opus-4",
    ],
    "google": [
        "gemini-3.1-pro-preview",
        "gemini-3-pro-preview",
        "gemini-3-flash-preview",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
    ],
}


def get_available_models(force_refresh: bool = False) -> Dict[str, List[str]]:
    """
    Fetch available models from LiteLLM registry with 24h cache.

    Args:
        force_refresh: Skip cache and fetch fresh data

    Returns:
        Dict mapping provider name to list of model IDs
    """
    # Check cache
    if not force_refresh and _cache["models"]:
        age = datetime.now() - _cache["fetched_at"]
        if age < timedelta(hours=24):
            return _cache["models"]

    # Fetch from LiteLLM registry
    try:
        resp = httpx.get(
            "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()

        # Extract model IDs by provider
        models = {
            "openai": [
                k
                for k in data.keys()
                if k.startswith(("gpt-", "o1-", "o3-", "o4-", "chatgpt-"))
            ],
            "anthropic": [k for k in data.keys() if k.startswith("claude-")],
            "google": [k for k in data.keys() if k.startswith("gemini-")],
        }

        # Update cache
        _cache["models"] = models
        _cache["fetched_at"] = datetime.now()

        return models

    except Exception:
        # Fallback to static list on any error
        return FALLBACK_MODELS


def detect_provider(model_id: str) -> str:
    """
    Auto-detect provider from model ID.

    Args:
        model_id: Model identifier (e.g., "gpt-5.2", "claude-opus-4.6")

    Returns:
        Provider name ("openai", "anthropic", "google")

    Raises:
        ValueError: If model_id doesn't match any known provider
    """
    models = get_available_models()

    for provider, model_list in models.items():
        # Check if model_id exactly matches or starts with any known model prefix
        if model_id in model_list:
            return provider
        # Check prefixes for flexible matching
        for known_model in model_list:
            if model_id.startswith(known_model.split("-")[0]):
                return provider

    raise ValueError(
        f"Unknown model: {model_id}. Supported providers: {', '.join(models.keys())}"
    )


def get_example_models(count: int = 3) -> List[str]:
    """
    Get example model IDs for documentation/help text.

    Args:
        count: Number of examples to return (distributed across providers)

    Returns:
        List of example model IDs
    """
    models = get_available_models()
    examples = []

    # Get one from each provider
    for provider in ["openai", "anthropic", "google"]:
        if provider in models and models[provider]:
            examples.append(models[provider][0])

    return examples[:count]
