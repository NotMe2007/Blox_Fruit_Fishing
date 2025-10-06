"""
Centralized Debug Logger for Blox Fruit Fishing Bot
Allows selective enabling/disabling of different debug categories for cleaner testing.

Usage:
    from BackGround_Logic.Debug_Logger import debug_log, LogCategory, set_log_categories
    
    # Log with specific category
    debug_log(LogCategory.MINIGAME, "Minigame action executed")
    
    # Enable only specific categories
    set_log_categories([LogCategory.MINIGAME, LogCategory.FISH_DETECTION])
"""

from enum import Enum
from typing import Set, List, Optional
import time
from datetime import datetime


class LogCategory(Enum):
    """Debug log categories for selective filtering"""
    # Core system logs
    SYSTEM = "SYSTEM"           # System startup, errors, critical events
    ROBLOX = "ROBLOX"          # Roblox window detection, API calls
    CONFIG = "CONFIG"          # Configuration loading, settings
    
    # Detection categories
    FISH_DETECTION = "FISH"    # Fish on hook detection, template matching
    ROD_DETECTION = "ROD"      # Fishing rod state detection
    MINIGAME_DETECT = "GAME_DETECT"  # Minigame UI detection
    
    # Action categories
    MINIGAME = "MINIGAME"      # Minigame actions, decisions, movements
    MOUSE = "MOUSE"           # Mouse movements, clicks, virtual mouse
    CASTING = "CASTING"       # Casting actions, power detection
    
    # Window and UI management
    WINDOW_MANAGEMENT = "WINDOW"  # Window detection, focus, coordinates
    UI = "UI"                 # User interface, GUI events
    
    # Data analysis
    TEMPLATE = "TEMPLATE"     # Template matching scores, image analysis
    COLOR = "COLOR"          # Color-based detection methods
    COORDINATES = "COORDS"   # Position calculations, coordinates
    
    # Performance and timing
    TIMING = "TIMING"        # Execution times, delays, performance
    STATS = "STATS"         # Statistics, counters, success rates
    
    # Screen capture
    SCREEN_CAPTURE = "SCREEN_CAPTURE"  # Screen capture operations, image processing
    
    # Development and debugging
    DEBUG = "DEBUG"          # General debug information
    VERBOSE = "VERBOSE"      # Very detailed/spammy logs
    ERROR = "ERROR"         # Error handling, exceptions


class DebugLogger:
    """Centralized debug logging system with category filtering"""
    
    def __init__(self):
        # By default, enable common categories
        self.enabled_categories: Set[LogCategory] = {
            LogCategory.SYSTEM,
            LogCategory.FISH_DETECTION,
            LogCategory.MINIGAME,
            LogCategory.ERROR,
            LogCategory.ROBLOX
        }
        
        # Color mapping for different categories
        self.category_colors = {
            LogCategory.SYSTEM: "🖥️",
            LogCategory.ROBLOX: "🎮",
            LogCategory.CONFIG: "⚙️",
            LogCategory.FISH_DETECTION: "🐟",
            LogCategory.ROD_DETECTION: "🎣",
            LogCategory.MINIGAME_DETECT: "🔍",
            LogCategory.MINIGAME: "🎯",
            LogCategory.MOUSE: "🖱️",
            LogCategory.CASTING: "⚡",
            LogCategory.TEMPLATE: "🖼️",
            LogCategory.COLOR: "🎨",
            LogCategory.COORDINATES: "📍",
            LogCategory.TIMING: "⏱️",
            LogCategory.STATS: "📊",
            LogCategory.DEBUG: "🔧",
            LogCategory.VERBOSE: "📝",
            LogCategory.ERROR: "❌"
        }
        
        # Track last log time for performance monitoring
        self.last_log_times = {}
        
    def is_enabled(self, category: LogCategory) -> bool:
        """Check if a category is enabled for logging"""
        return category in self.enabled_categories
    
    def enable_categories(self, categories: List[LogCategory]):
        """Enable specific log categories"""
        self.enabled_categories.update(categories)
    
    def disable_categories(self, categories: List[LogCategory]):
        """Disable specific log categories"""
        self.enabled_categories.difference_update(categories)
    
    def set_categories(self, categories: List[LogCategory]):
        """Set exactly which categories should be enabled (disables all others)"""
        self.enabled_categories = set(categories)
    
    def enable_all(self):
        """Enable all log categories"""
        self.enabled_categories = set(LogCategory)
    
    def disable_all(self):
        """Disable all log categories (except ERROR)"""
        self.enabled_categories = {LogCategory.ERROR}
    
    def log(self, category: LogCategory, message: str, show_time: bool = False, show_category: bool = True):
        """
        Log a message if the category is enabled
        
        Args:
            category: LogCategory enum value
            message: The message to log
            show_time: Whether to show timestamp
            show_category: Whether to show category name
        """
        if not self.is_enabled(category):
            return
            
        # Build log prefix
        prefix_parts = []
        
        # Add emoji for category
        emoji = self.category_colors.get(category, "📄")
        prefix_parts.append(emoji)
        
        # Add timestamp if requested
        if show_time:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
            prefix_parts.append(f"[{timestamp}]")
        
        # Add category name if requested
        if show_category and category != LogCategory.SYSTEM:
            prefix_parts.append(f"[{category.value}]")
        
        # Build final message
        if prefix_parts:
            prefix = " ".join(prefix_parts) + " "
        else:
            prefix = emoji + " "
            
        print(f"{prefix}{message}")
        
        # Track timing for performance monitoring
        self.last_log_times[category] = time.time()
    
    def get_status(self) -> str:
        """Get current logger status for debugging"""
        enabled_list = [cat.value for cat in sorted(self.enabled_categories, key=lambda x: x.value)]
        return f"Debug Logger: {len(self.enabled_categories)}/{len(LogCategory)} categories enabled: {', '.join(enabled_list)}"


# Global logger instance
_logger = DebugLogger()

# Convenience functions for easy importing
def debug_log(category: LogCategory, message: str, show_time: bool = False, show_category: bool = True):
    """Log a debug message with specified category"""
    _logger.log(category, message, show_time, show_category)

def set_log_categories(categories: List[LogCategory]):
    """Set which categories should be enabled (disables others)"""
    _logger.set_categories(categories)

def enable_log_categories(categories: List[LogCategory]):
    """Enable additional categories"""
    _logger.enable_categories(categories)

def disable_log_categories(categories: List[LogCategory]):
    """Disable specific categories"""
    _logger.disable_categories(categories)

def enable_all_logs():
    """Enable all log categories"""
    _logger.enable_all()

def disable_all_logs():
    """Disable all logs except errors"""
    _logger.disable_all()

def is_log_enabled(category: LogCategory) -> bool:
    """Check if a category is enabled"""
    return _logger.is_enabled(category)

def get_logger_status() -> str:
    """Get current logger configuration"""
    return _logger.get_status()


# Preset configurations for common debugging scenarios
class LogPresets:
    """Predefined log category sets for common debugging scenarios"""
    
    # Basic operation - minimal logs
    MINIMAL = [LogCategory.SYSTEM, LogCategory.ERROR]
    
    # Normal operation - moderate detail
    NORMAL = [
        LogCategory.SYSTEM, 
        LogCategory.FISH_DETECTION, 
        LogCategory.MINIGAME, 
        LogCategory.ERROR,
        LogCategory.ROBLOX
    ]
    
    # Fish detection debugging
    FISH_DEBUG = [
        LogCategory.FISH_DETECTION, 
        LogCategory.TEMPLATE, 
        LogCategory.COLOR, 
        LogCategory.COORDINATES,
        LogCategory.ERROR
    ]
    
    # Minigame debugging
    MINIGAME_DEBUG = [
        LogCategory.MINIGAME, 
        LogCategory.MINIGAME_DETECT, 
        LogCategory.MOUSE, 
        LogCategory.COORDINATES,
        LogCategory.TIMING,
        LogCategory.ERROR
    ]
    
    # Performance analysis
    PERFORMANCE = [
        LogCategory.TIMING, 
        LogCategory.STATS, 
        LogCategory.SYSTEM,
        LogCategory.ERROR
    ]
    
    # Template matching analysis
    TEMPLATE_DEBUG = [
        LogCategory.TEMPLATE, 
        LogCategory.COLOR, 
        LogCategory.FISH_DETECTION,
        LogCategory.ROD_DETECTION,
        LogCategory.MINIGAME_DETECT,
        LogCategory.ERROR
    ]
    
    # Everything (full debug)
    FULL_DEBUG = list(LogCategory)
    
    # Silent (errors only)
    SILENT = [LogCategory.ERROR]


def set_preset(preset_name: str):
    """Set a predefined logging preset"""
    preset_map = {
        "minimal": LogPresets.MINIMAL,
        "normal": LogPresets.NORMAL,
        "fish": LogPresets.FISH_DEBUG,
        "minigame": LogPresets.MINIGAME_DEBUG,
        "performance": LogPresets.PERFORMANCE,
        "template": LogPresets.TEMPLATE_DEBUG,
        "full": LogPresets.FULL_DEBUG,
        "all_enabled": LogPresets.FULL_DEBUG,
        "all": LogPresets.FULL_DEBUG,
        "full_debug": LogPresets.FULL_DEBUG,
        "fish_debug": LogPresets.FISH_DEBUG,
        "minigame_debug": LogPresets.MINIGAME_DEBUG,
        "silent": LogPresets.SILENT
    }
    
    preset = preset_map.get(preset_name.lower())
    if preset:
        set_log_categories(preset)
        debug_log(LogCategory.SYSTEM, f"Set logging preset: {preset_name}")
        debug_log(LogCategory.SYSTEM, get_logger_status())
    else:
        available = ", ".join(preset_map.keys())
        debug_log(LogCategory.ERROR, f"Unknown preset '{preset_name}'. Available: {available}")


# Example usage and testing
if __name__ == "__main__":
    print("=== Debug Logger Testing ===")
    
    # Test different categories
    debug_log(LogCategory.SYSTEM, "System starting up")
    debug_log(LogCategory.FISH_DETECTION, "Looking for fish...")
    debug_log(LogCategory.MINIGAME, "Executing minigame action")
    debug_log(LogCategory.VERBOSE, "This won't show (verbose disabled by default)")
    
    print("\n=== Testing Presets ===")
    
    # Test preset switching
    print("\nSwitching to FISH_DEBUG preset:")
    set_preset("fish")
    
    debug_log(LogCategory.FISH_DETECTION, "Fish detection message")
    debug_log(LogCategory.TEMPLATE, "Template matching result")
    debug_log(LogCategory.MINIGAME, "This won't show (minigame disabled in fish preset)")
    
    print("\nSwitching to MINIMAL preset:")
    set_preset("minimal")
    
    debug_log(LogCategory.SYSTEM, "System message")
    debug_log(LogCategory.FISH_DETECTION, "This won't show (fish disabled in minimal)")
    debug_log(LogCategory.ERROR, "Error message")
    
    print("\nLogger status:")
    print(get_logger_status())