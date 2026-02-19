"""LLM provider adapters with auto-discovery."""

import importlib
import pkgutil
from pathlib import Path

from pramana.providers.base import BaseProvider
from pramana.providers.registry import _REGISTRY  # noqa: F401 — ensure registry populated

# Auto-discover all provider modules in this package
for _info in pkgutil.iter_modules([str(Path(__file__).parent)]):
    if _info.name not in ("base", "registry"):
        try:
            importlib.import_module(f"pramana.providers.{_info.name}")
        except ImportError:
            pass  # Optional SDK not installed (e.g. claude_agent_sdk)

__all__ = ["BaseProvider"]
