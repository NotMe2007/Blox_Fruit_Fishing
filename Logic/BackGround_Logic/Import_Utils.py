"""
Centralized Import Utilities for Blox Fruit Fishing Bot
Single source of truth for all defensive imports and fallback implementations.

This module provides standardized import patterns for all BackGround_Logic modules,
ensuring consistent behavior across the entire codebase.

Usage:
    from BackGround_Logic.Import_Utils import (
        debug_log, LogCategory, DEBUG_LOGGER_AVAILABLE,
        virtual_mouse, VIRTUAL_MOUSE_AVAILABLE,
        virtual_keyboard, VIRTUAL_KEYBOARD_AVAILABLE,
        screenshot, SCREEN_CAPTURE_AVAILABLE,
        get_roblox_coordinates, get_roblox_window_region, 
        ensure_roblox_focused, WINDOW_MANAGER_AVAILABLE
    )
"""

from enum import Enum
from typing import Optional, Tuple, Any
import sys
import os

# ============================================================================
# DEBUG LOGGER - PRIMARY IMPORT WITH FALLBACK
# ============================================================================

DEBUG_LOGGER_AVAILABLE = False
debug_log = None  # type: ignore
LogCategory = None  # type: ignore

try:
    from .Debug_Logger import debug_log, LogCategory  # type: ignore
    DEBUG_LOGGER_AVAILABLE = True
except ImportError:
    try:
        from Debug_Logger import debug_log, LogCategory  # type: ignore
        DEBUG_LOGGER_AVAILABLE = True
    except ImportError:
        # Fallback LogCategory - matches Debug_Logger.py exactly
        class LogCategory(Enum):
            """Debug log categories for selective filtering"""
            # Core system logs
            SYSTEM = "SYSTEM"
            ROBLOX = "ROBLOX"
            CONFIG = "CONFIG"
            
            # Detection categories
            FISH_DETECTION = "FISH"
            ROD_DETECTION = "ROD"
            MINIGAME_DETECT = "GAME_DETECT"
            
            # Action categories
            MINIGAME = "MINIGAME"
            MINIGAME_ACTIONS = "MINIGAME_ACTIONS"
            MOUSE = "MOUSE"
            CASTING = "CASTING"
            
            # Window and UI management
            WINDOW_MANAGEMENT = "WINDOW"
            UI = "UI"
            FISHING_MAIN = "FISHING_MAIN"
            
            # Data analysis
            TEMPLATE = "TEMPLATE"
            COLOR = "COLOR"
            COORDINATES = "COORDS"
            
            # Performance and timing
            TIMING = "TIMING"
            STATS = "STATS"
            
            # Screen capture
            SCREEN_CAPTURE = "SCREEN_CAPTURE"
            
            # Development and debugging
            DEBUG = "DEBUG"
            VERBOSE = "VERBOSE"
            ERROR = "ERROR"
        
        def debug_log(category, message, show_time=False, show_category=True):
            """Fallback debug_log function"""
            print(f"[{category.value}] {message}")


# ============================================================================
# VIRTUAL MOUSE - PRIMARY IMPORT WITH FALLBACK
# ============================================================================

VIRTUAL_MOUSE_AVAILABLE = False
virtual_mouse = None

try:
    from .Virtual_Mouse import VirtualMouse
    virtual_mouse = VirtualMouse()
    VIRTUAL_MOUSE_AVAILABLE = True
except ImportError:
    try:
        # Add current directory to path and try absolute import
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        from Virtual_Mouse import VirtualMouse
        virtual_mouse = VirtualMouse()
        VIRTUAL_MOUSE_AVAILABLE = True
    except ImportError:
        virtual_mouse = None
        VIRTUAL_MOUSE_AVAILABLE = False


# ============================================================================
# VIRTUAL KEYBOARD - PRIMARY IMPORT WITH FALLBACK
# ============================================================================

VIRTUAL_KEYBOARD_AVAILABLE = False
virtual_keyboard = None

try:
    from .Virtual_Keyboard import VirtualKeyboard
    virtual_keyboard = VirtualKeyboard()
    VIRTUAL_KEYBOARD_AVAILABLE = True
except ImportError:
    try:
        from Virtual_Keyboard import VirtualKeyboard
        virtual_keyboard = VirtualKeyboard()
        VIRTUAL_KEYBOARD_AVAILABLE = True
    except ImportError:
        virtual_keyboard = None
        VIRTUAL_KEYBOARD_AVAILABLE = False


# ============================================================================
# SCREEN CAPTURE - PRIMARY IMPORT WITH FALLBACK
# ============================================================================

SCREEN_CAPTURE_AVAILABLE = False
screenshot = None

try:
    from .Screen_Capture import screenshot
    SCREEN_CAPTURE_AVAILABLE = True
except ImportError:
    try:
        from Screen_Capture import screenshot
        SCREEN_CAPTURE_AVAILABLE = True
    except ImportError:
        screenshot = None
        SCREEN_CAPTURE_AVAILABLE = False


# ============================================================================
# HELPER FUNCTIONS (DEFINED BEFORE WINDOW MANAGER IMPORT)
# ============================================================================

def is_virtual_mouse_available() -> bool:
    """Check if virtual mouse is available and ready to use."""
    return VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None


def is_virtual_keyboard_available() -> bool:
    """Check if virtual keyboard is available and ready to use."""
    return VIRTUAL_KEYBOARD_AVAILABLE and virtual_keyboard is not None


def is_screen_capture_available() -> bool:
    """Check if screen capture is available."""
    return SCREEN_CAPTURE_AVAILABLE and screenshot is not None


# ============================================================================
# WINDOW MANAGER - PRIMARY IMPORT WITH FALLBACK
# ============================================================================

WINDOW_MANAGER_AVAILABLE = False
roblox_window_manager = None  # type: ignore
get_roblox_coordinates = None  # type: ignore
get_roblox_window_region = None  # type: ignore
ensure_roblox_focused = None  # type: ignore

try:
    from .Window_Manager import (  # type: ignore
        RobloxWindowManager,
        get_roblox_coordinates,  # type: ignore
        get_roblox_window_region,  # type: ignore
        ensure_roblox_focused  # type: ignore
    )
    roblox_window_manager = RobloxWindowManager()
    WINDOW_MANAGER_AVAILABLE = True
except ImportError:
    try:
        from Window_Manager import (  # type: ignore
            RobloxWindowManager,
            get_roblox_coordinates,  # type: ignore
            get_roblox_window_region,  # type: ignore
            ensure_roblox_focused  # type: ignore
        )
        roblox_window_manager = RobloxWindowManager()
        WINDOW_MANAGER_AVAILABLE = True
    except ImportError:
        WINDOW_MANAGER_AVAILABLE = False

        # Fallback dummy functions
        def get_roblox_coordinates():  # type: ignore
            """Fallback function when Window_Manager not available"""
            return None, None

        def get_roblox_window_region():  # type: ignore
            """Fallback function when Window_Manager not available"""
            return None

        def ensure_roblox_focused():  # type: ignore
            """Fallback function when Window_Manager not available"""
            return False


def is_window_manager_available() -> bool:
    """Check if window manager is available."""
    return WINDOW_MANAGER_AVAILABLE and roblox_window_manager is not None


def log_import_status():
    """Log the status of all imports for debugging purposes."""
    if DEBUG_LOGGER_AVAILABLE:
        debug_log(LogCategory.SYSTEM, "=== Import Status ===")
        debug_log(LogCategory.SYSTEM, f"Debug Logger: {'✅ Available' if DEBUG_LOGGER_AVAILABLE else '❌ Unavailable'}")
        debug_log(LogCategory.SYSTEM, f"Virtual Mouse: {'✅ Available' if is_virtual_mouse_available() else '❌ Unavailable'}")
        debug_log(LogCategory.SYSTEM, f"Virtual Keyboard: {'✅ Available' if is_virtual_keyboard_available() else '❌ Unavailable'}")
        debug_log(LogCategory.SYSTEM, f"Screen Capture: {'✅ Available' if is_screen_capture_available() else '❌ Unavailable'}")
        debug_log(LogCategory.SYSTEM, f"Window Manager: {'✅ Available' if is_window_manager_available() else '❌ Unavailable'}")
    else:
        print("=== Import Status ===")
        print(f"Debug Logger: {'✅ Available' if DEBUG_LOGGER_AVAILABLE else '❌ Unavailable'}")
        print(f"Virtual Mouse: {'✅ Available' if is_virtual_mouse_available() else '❌ Unavailable'}")
        print(f"Virtual Keyboard: {'✅ Available' if is_virtual_keyboard_available() else '❌ Unavailable'}")
        print(f"Screen Capture: {'✅ Available' if is_screen_capture_available() else '❌ Unavailable'}")
        print(f"Window Manager: {'✅ Available' if is_window_manager_available() else '❌ Unavailable'}")
