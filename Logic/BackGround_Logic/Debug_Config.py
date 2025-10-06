"""
Debug Configuration for Blox Fruit Fishing Bot
Simple configuration file to switch between different logging presets.
"""

# Defensive import so the module can be used both as part of the package and directly via sys.path tweaks
try:
    from .Debug_Logger import set_preset, debug_log, LogCategory  # Package-relative import
    DEBUG_LOGGER_AVAILABLE = True
except ImportError:
    try:
        from Debug_Logger import set_preset, debug_log, LogCategory  # Absolute import fallback
        DEBUG_LOGGER_AVAILABLE = True
    except ImportError:  # pragma: no cover - extremely rare, but keep silent fallback
        DEBUG_LOGGER_AVAILABLE = False

        def set_preset(preset_name: str) -> None:  # type: ignore[empty-body]
            """Fallback preset setter when Debug_Logger is unavailable."""
            return None

        def debug_log(category, message: str, show_time: bool = False, show_category: bool = True) -> None:  # type: ignore[empty-body]
            """Fallback logger that quietly ignores messages when logger missing."""
            return None

        class _MissingLogCategory:
            SYSTEM = "SYSTEM"

        LogCategory = _MissingLogCategory

# Default logging preset - change this to switch debug modes
DEFAULT_PRESET = "normal"

# Available presets:
# "minimal"    - Only system and errors
# "normal"     - Basic operation logs
# "fish"       - Fish detection debugging
# "minigame"   - Minigame debugging  
# "performance" - Performance analysis
# "template"   - Template matching debug
# "full"       - Everything (very verbose)
# "silent"     - Errors only

def initialize_logging():
    """Initialize logging with the default preset"""
    if DEBUG_LOGGER_AVAILABLE:
        set_preset(DEFAULT_PRESET)
        debug_log(LogCategory.SYSTEM, f"Debug logging initialized with preset: {DEFAULT_PRESET}")

def switch_to_minigame_debug():
    """Quick function to switch to minigame debugging"""
    if DEBUG_LOGGER_AVAILABLE:
        set_preset("minigame")
        debug_log(LogCategory.SYSTEM, "Switched to minigame debug mode")

def switch_to_fish_debug():
    """Quick function to switch to fish detection debugging"""
    if DEBUG_LOGGER_AVAILABLE:
        set_preset("fish") 
        debug_log(LogCategory.SYSTEM, "Switched to fish detection debug mode")

def switch_to_minimal():
    """Quick function to switch to minimal logging"""
    if DEBUG_LOGGER_AVAILABLE:
        set_preset("minimal")
        debug_log(LogCategory.SYSTEM, "Switched to minimal logging mode")

def switch_to_silent():
    """Quick function to switch to silent mode (errors only)"""
    if DEBUG_LOGGER_AVAILABLE:
        set_preset("silent")

# Initialize on import
initialize_logging()