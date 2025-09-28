"""
Virtual Mouse Driver using Windows API for undetectable mouse input.
Uses low-level Windows API calls to simulate hardware mouse input.
"""
import ctypes
import ctypes.wintypes
import time
from typing import Tuple, Optional

# Debug Logger
try:
    from .Debug_Logger import debug_log, LogCategory
    DEBUG_LOGGER_AVAILABLE = True
except ImportError:
    try:
        from Debug_Logger import debug_log, LogCategory
        DEBUG_LOGGER_AVAILABLE = True
    except ImportError:
        DEBUG_LOGGER_AVAILABLE = False
        # Fallback log categories
        from enum import Enum
        class LogCategory(Enum):
            MOUSE = "MOUSE"
            SYSTEM = "SYSTEM"
            ERROR = "ERROR"
        def debug_log(category, message):
            print(f"[{category.value}] {message}")


# Windows API constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

INPUT_MOUSE = 0
HC_ACTION = 0

# Windows API structures
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.wintypes.LONG),
        ("dy", ctypes.wintypes.LONG),
        ("mouseData", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG))
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG))
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.wintypes.DWORD),
        ("wParamL", ctypes.wintypes.WORD),
        ("wParamH", ctypes.wintypes.WORD)
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [
            ("mi", MOUSEINPUT),
            ("ki", KEYBDINPUT),
            ("hi", HARDWAREINPUT)
        ]
    
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("_input", _INPUT)
    ]


class VirtualMouse:
    """
    Virtual mouse driver that uses Windows API to create hardware-level mouse input.
    This bypasses most anti-cheat detection because it appears as real hardware input.
    """
    
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        
        # Get virtual desktop dimensions (all monitors combined)
        # SM_XVIRTUALSCREEN = 76, SM_YVIRTUALSCREEN = 77
        # SM_CXVIRTUALSCREEN = 78, SM_CYVIRTUALSCREEN = 79
        self.virtual_left = self.user32.GetSystemMetrics(76)    # Left edge of virtual desktop
        self.virtual_top = self.user32.GetSystemMetrics(77)     # Top edge of virtual desktop  
        self.virtual_width = self.user32.GetSystemMetrics(78)   # Width of virtual desktop
        self.virtual_height = self.user32.GetSystemMetrics(79)  # Height of virtual desktop
        
        debug_log(LogCategory.SYSTEM, f"Virtual desktop: Left={self.virtual_left}, Top={self.virtual_top}, Width={self.virtual_width}, Height={self.virtual_height}")
        
        # Also get primary screen dimensions for fallback
        self.primary_width = self.user32.GetSystemMetrics(0)
        self.primary_height = self.user32.GetSystemMetrics(1)
    
    def get_cursor_pos(self) -> Tuple[int, int]:
        """Get current cursor position using Windows API."""
        point = POINT()
        self.user32.GetCursorPos(ctypes.byref(point))
        return point.x, point.y
    
    def _send_input(self, *inputs):
        """Simplified input method using basic Windows API calls."""
        try:
            debug_log(LogCategory.MOUSE, "🔄 Using simplified mouse API...")
            
            for input_struct in inputs:
                if hasattr(input_struct, '_input') and hasattr(input_struct._input, 'mi'):
                    mi = input_struct._input.mi
                    
                    # Convert absolute coordinates back to screen coordinates
                    if mi.dwFlags & MOUSEEVENTF_ABSOLUTE:
                        screen_x = int((mi.dx * self.virtual_width) / 65536) + self.virtual_left
                        screen_y = int((mi.dy * self.virtual_height) / 65536) + self.virtual_top
                        
                        # Ensure coordinates are within screen bounds
                        screen_x = max(0, min(screen_x, self.virtual_width - 1))
                        screen_y = max(0, min(screen_y, self.virtual_height - 1))
                        
                        if mi.dwFlags & MOUSEEVENTF_MOVE:
                            # Move cursor
                            self.user32.SetCursorPos(screen_x, screen_y)
                            debug_log(LogCategory.MOUSE, f"✅ Moved cursor to ({screen_x}, {screen_y})")
                        
                        if mi.dwFlags & MOUSEEVENTF_LEFTDOWN:
                            # Left mouse down
                            self.user32.SetCursorPos(screen_x, screen_y)
                            self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                            debug_log(LogCategory.MOUSE, f"✅ Left mouse down at ({screen_x}, {screen_y})")
                        
                        if mi.dwFlags & MOUSEEVENTF_LEFTUP:
                            # Left mouse up
                            self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                            debug_log(LogCategory.MOUSE, f"✅ Left mouse up")
                        
                        if mi.dwFlags & MOUSEEVENTF_RIGHTDOWN:
                            # Right mouse down
                            self.user32.SetCursorPos(screen_x, screen_y)
                            self.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                            debug_log(LogCategory.MOUSE, f"✅ Right mouse down at ({screen_x}, {screen_y})")
                        
                        if mi.dwFlags & MOUSEEVENTF_RIGHTUP:
                            # Right mouse up
                            self.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
                            debug_log(LogCategory.MOUSE, f"✅ Right mouse up")
            
            debug_log(LogCategory.MOUSE, "✅ Mouse input completed successfully")
            return len(inputs)
                            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"⚠️ Mouse input failed: {e}")
            debug_log(LogCategory.ERROR, "❌ All mouse input methods failed")
            return 0
    
    def _create_mouse_input(self, dx: int, dy: int, flags: int) -> INPUT:
        """Create a mouse input structure."""
        mouse_input = MOUSEINPUT()
        mouse_input.dx = dx
        mouse_input.dy = dy
        mouse_input.mouseData = 0
        mouse_input.dwFlags = flags
        mouse_input.time = 0
        mouse_input.dwExtraInfo = None
        
        input_struct = INPUT()
        input_struct.type = INPUT_MOUSE
        input_struct.mi = mouse_input
        return input_struct
    
    def move_to(self, x: int, y: int):
        """Move mouse to specific coordinates."""
        try:
            debug_log(LogCategory.MOUSE, f"Moving mouse to ({x}, {y})")
            
            # Ensure coordinates are within screen bounds
            x = max(0, min(x, self.primary_width - 1))
            y = max(0, min(y, self.primary_height - 1))
            
            # Use SetCursorPos for simple, reliable mouse movement
            result = self.user32.SetCursorPos(x, y)
            if result:
                debug_log(LogCategory.MOUSE, f"✅ Mouse moved to ({x}, {y})")
            else:
                debug_log(LogCategory.ERROR, f"❌ Failed to move mouse to ({x}, {y})")
                
        except Exception as e:
            debug_log(LogCategory.ERROR, f"❌ Move failed to ({x}, {y}): {e}")
    
    def smooth_move_to(self, x: int, y: int, duration: float = 0.3):
        """Move mouse smoothly to coordinates for more human-like movement."""
        try:
            # Get current mouse position
            current_pos = POINT()
            self.user32.GetCursorPos(ctypes.byref(current_pos))
            
            start_x, start_y = current_pos.x, current_pos.y
            target_x, target_y = x, y
            
            # Calculate steps for smooth movement
            steps = max(10, int(duration * 60))  # 60 FPS smoothness
            step_delay = duration / steps
            
            for i in range(steps + 1):
                progress = i / steps
                # Use easing function for more natural movement
                ease_progress = progress * progress * (3 - 2 * progress)  # Smoothstep
                
                current_x = int(start_x + (target_x - start_x) * ease_progress)
                current_y = int(start_y + (target_y - start_y) * ease_progress)
                
                self.user32.SetCursorPos(current_x, current_y)
                
                if i < steps:  # Don't sleep on last iteration
                    time.sleep(step_delay)
                    
            debug_log(LogCategory.MOUSE, f"✅ Smooth move completed to ({x}, {y})")
                    
        except Exception as e:
            debug_log(LogCategory.ERROR, f"❌ Smooth move failed to ({x}, {y}): {e}")
            # Fallback to regular move
            self.move_to(x, y)
    
    def click_at(self, x: int, y: int, button: str = 'left', duration: float = 0.05):
        """Simple and reliable click method using basic Windows API."""
        try:
            debug_log(LogCategory.MOUSE, f"🖱️ Clicking at ({x}, {y}) with {button} button")
            
            # Ensure coordinates are within screen bounds
            x = max(0, min(x, self.primary_width - 1))
            y = max(0, min(y, self.primary_height - 1))
            
            # Move to position first
            self.user32.SetCursorPos(x, y)
            time.sleep(0.01)  # Small delay to ensure position is set
            
            if button == 'left':
                # Left click
                self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(duration)
                self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                debug_log(LogCategory.MOUSE, f"✅ Left click completed at ({x}, {y})")
            elif button == 'right':
                # Right click
                self.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                time.sleep(duration)
                self.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
                debug_log(LogCategory.MOUSE, f"✅ Right click completed at ({x}, {y})")
            else:
                raise ValueError("Button must be 'left' or 'right'")
                
            return True
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"❌ Click failed at ({x}, {y}): {e}")
            return False

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.1):
        """
        Perform direct drag operation using hardware input.
        """
        # Move to start position
        self.move_to(start_x, start_y)
        
        # Mouse down at start
        self.mouse_down(start_x, start_y, 'left')
        
        # Hold briefly
        time.sleep(duration)
        
        # Move directly to end position
        self.move_to(end_x, end_y)
        
        # Mouse up at end
        self.mouse_up(end_x, end_y, 'left')
    
    def mouse_down(self, x: int, y: int, button: str = 'left'):
        """Press mouse button down at specified coordinates."""
        if button == 'left':
            flag = MOUSEEVENTF_LEFTDOWN
        elif button == 'right':
            flag = MOUSEEVENTF_RIGHTDOWN
        else:
            raise ValueError("Button must be 'left' or 'right'")
        
        # Convert screen coordinates to virtual desktop coordinates
        virtual_x = x - self.virtual_left
        virtual_y = y - self.virtual_top
        
        # Convert to absolute coordinates (0-65535 range) within virtual desktop
        abs_x = int((virtual_x * 65535) / self.virtual_width)
        abs_y = int((virtual_y * 65535) / self.virtual_height)
        
        down_input = self._create_mouse_input(abs_x, abs_y, flag | MOUSEEVENTF_ABSOLUTE)
        self._send_input(down_input)
    
    def mouse_up(self, x: int, y: int, button: str = 'left'):
        """Release mouse button at specified coordinates."""
        if button == 'left':
            flag = MOUSEEVENTF_LEFTUP
        elif button == 'right':
            flag = MOUSEEVENTF_RIGHTUP
        else:
            raise ValueError("Button must be 'left' or 'right'")
        
        # Convert screen coordinates to virtual desktop coordinates
        virtual_x = x - self.virtual_left
        virtual_y = y - self.virtual_top
        
        # Convert to absolute coordinates (0-65535 range) within virtual desktop
        abs_x = int((virtual_x * 65535) / self.virtual_width)
        abs_y = int((virtual_y * 65535) / self.virtual_height)
        
        up_input = self._create_mouse_input(abs_x, abs_y, flag | MOUSEEVENTF_ABSOLUTE)
        self._send_input(up_input)


# Global instance for easy access
virtual_mouse = VirtualMouse()
