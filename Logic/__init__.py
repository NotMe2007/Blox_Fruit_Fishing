"""Logic package initializer.

Provides convenience re-exports so external code can access the main fishing
script via ``from Logic import Fishing_Script`` while keeping the canonical
implementation inside ``Logic.fishing_Script``.
"""

from importlib import import_module
from types import ModuleType
from typing import Optional

Fishing_Script: Optional[ModuleType]
try:
    Fishing_Script = import_module("Logic.fishing_Script")
except ImportError:  # pragma: no cover - defensive fallback when module unavailable
    Fishing_Script = None

__all__ = ["Fishing_Script"]
