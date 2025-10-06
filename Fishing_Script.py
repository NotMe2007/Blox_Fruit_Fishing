"""Compatibility wrapper for the main fishing automation script.

This keeps legacy imports like ``import Fishing_Script`` working by exposing the
contents of ``Logic.fishing_Script`` at the project root.
"""

from importlib import import_module
from types import ModuleType
from typing import Any, Dict

_fishing_mod: ModuleType = import_module("Logic.fishing_Script")


def _export_public_attributes(source: ModuleType) -> Dict[str, Any]:
    exports: Dict[str, Any] = {}
    for attr in dir(source):
        if attr.startswith("_"):
            continue
        exports[attr] = getattr(source, attr)
    return exports

globals().update(_export_public_attributes(_fishing_mod))
