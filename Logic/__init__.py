"""Logic package: importing helpers must not initialize the fishing engine."""
from importlib import import_module

__all__ = ["Fishing_Script"]


def __getattr__(name):
    if name == "Fishing_Script":
        module = import_module("Logic.fishing_Script")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
