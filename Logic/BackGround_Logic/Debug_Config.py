"""
Debug Configuration for Blox Fruit Fishing Bot
Simple configuration file to switch between different logging presets.
"""

from .Debug_Logger import set_preset, debug_log, LogCategory

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
    set_preset(DEFAULT_PRESET)
    debug_log(LogCategory.SYSTEM, f"Debug logging initialized with preset: {DEFAULT_PRESET}")

def switch_to_minigame_debug():
    """Quick function to switch to minigame debugging"""
    set_preset("minigame")
    debug_log(LogCategory.SYSTEM, "Switched to minigame debug mode")

def switch_to_fish_debug():
    """Quick function to switch to fish detection debugging"""
    set_preset("fish") 
    debug_log(LogCategory.SYSTEM, "Switched to fish detection debug mode")

def switch_to_minimal():
    """Quick function to switch to minimal logging"""
    set_preset("minimal")
    debug_log(LogCategory.SYSTEM, "Switched to minimal logging mode")

def switch_to_silent():
    """Quick function to switch to silent mode (errors only)"""
    set_preset("silent")

# Initialize on import
initialize_logging()