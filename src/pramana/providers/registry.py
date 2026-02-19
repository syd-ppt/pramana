"""Provider registry with auto-discovery."""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pramana.providers.base import BaseProvider


@dataclass
class ProviderEntry:
    cls: type[BaseProvider]
    provider_name: str  # "openai", "anthropic", "google"
    mode: str  # "api" | "subscription"
    env_key: str | None  # "OPENAI_API_KEY" or None
    sdk_package: str | None  # "claude_agent_sdk" or None


_REGISTRY: dict[tuple[str, str], ProviderEntry] = {}


def register(
    provider_name: str,
    mode: str,
    *,
    env_key: str | None = None,
    sdk_package: str | None = None,
):
    """Class decorator that registers a provider."""

    def decorator(cls):
        _REGISTRY[(provider_name, mode)] = ProviderEntry(
            cls=cls,
            provider_name=provider_name,
            mode=mode,
            env_key=env_key,
            sdk_package=sdk_package,
        )
        return cls

    return decorator


def is_available(entry: ProviderEntry, api_key: str | None = None) -> bool:
    """Check if a provider entry is usable right now."""
    if entry.mode == "api":
        if api_key:
            return True
        return bool(entry.env_key and os.environ.get(entry.env_key))

    if entry.mode == "subscription":
        if not entry.sdk_package:
            return False
        try:
            importlib.import_module(entry.sdk_package)
            return True
        except ImportError:
            return False

    return False


def resolve_provider(
    provider_name: str,
    mode: str | None = None,
    api_key: str | None = None,
    preferred_mode: str = "subscription",
) -> ProviderEntry | None:
    """Find the best available provider entry.

    If mode is explicit, return that entry (if available).
    Otherwise auto-detect: try preferred_mode first, then the other.
    """
    if mode:
        entry = _REGISTRY.get((provider_name, mode))
        if entry and is_available(entry, api_key=api_key):
            return entry
        return None

    # Auto-detect: try preferred first
    other_mode = "api" if preferred_mode == "subscription" else "subscription"
    for m in (preferred_mode, other_mode):
        entry = _REGISTRY.get((provider_name, m))
        if entry and is_available(entry, api_key=api_key):
            return entry

    return None


def list_unavailable_hints(provider_name: str) -> list[str]:
    """Return human-readable hints for making a provider available."""
    hints = []
    for (pname, mode), entry in _REGISTRY.items():
        if pname != provider_name:
            continue
        hints.append(get_install_hint(entry))
    return hints


def get_install_hint(entry: ProviderEntry) -> str:
    """Return a single install/setup hint for an entry."""
    if entry.mode == "api" and entry.env_key:
        return f"API mode: export {entry.env_key}=your-key"
    if entry.mode == "subscription" and entry.sdk_package:
        return f"Subscription mode: uv pip install {entry.sdk_package}"
    return f"{entry.mode} mode: check provider docs"
