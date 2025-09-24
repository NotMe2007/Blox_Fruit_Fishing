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
            MOUSE_INPUT = "MOUSE_INPUT"
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
        """Send input using simplified Windows API approach - more reliable than complex buffer method."""
        import ctypes.wintypes
        
        try:
            # Simplified approach: Use only the basic SendInput call
            SendInput = ctypes.windll.user32.SendInput
            
            # Create array of INPUT structures
            nInputs = len(inputs)
            LPINPUT = INPUT * nInputs
            input_array = LPINPUT(*inputs)
            
            # Call SendInput with properly typed parameters
            result = SendInput(nInputs, input_array, ctypes.sizeof(INPUT))
            
            if result == nInputs:
                return result
            else:
                debug_log(LogCategory.ERROR, f"⚠️ SendInput returned {result} (expected {nInputs})")
                error_code = ctypes.windll.kernel32.GetLastError()
                debug_log(LogCategory.ERROR, f"⚠️ Windows error code: {error_code}")
                
        except Exception as e:
            debug_log(LogCategory.ERROR, f"⚠️ SendInput failed: {e}")
            
        # Fallback: Use direct Windows API calls (SetCursorPos + mouse_event)
        try:
            debug_log(LogCategory.MOUSE_INPUT, "🔄 Using direct API fallback...")
            
            for input_struct in inputs:
                if hasattr(input_struct, '_input') and hasattr(input_struct._input, 'mi'):
                    mi = input_struct._input.mi
                    
                    # Convert absolute coordinates back to screen coordinates
                    if mi.dwFlags & MOUSEEVENTF_ABSOLUTE:
                        screen_x = int((mi.dx * self.virtual_width) / 65536) + self.virtual_left
                        screen_y = int((mi.dy * self.virtual_height) / 65536) + self.virtual_top
                        
                        if mi.dwFlags & MOUSEEVENTF_MOVE:
                            # Move cursor
                            result = self.user32.SetCursorPos(screen_x, screen_y)
                            if result:
                                debug_log(LogCategory.MOUSE_INPUT, f"✅ Moved cursor to ({screen_x}, {screen_y})")
                                return 1
                        elif mi.dwFlags & MOUSEEVENTF_LEFTDOWN:
                            # Mouse button down
                            self.user32.SetCursorPos(screen_x, screen_y)
                            self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                            debug_log(LogCategory.MOUSE_INPUT, f"✅ Left mouse down at ({screen_x}, {screen_y})")
                            return 1
                        elif mi.dwFlags & MOUSEEVENTF_LEFTUP:
                            # Mouse button up
                            self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                            debug_log(LogCategory.MOUSE_INPUT, f"✅ Left mouse up")
                            return 1
                            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"⚠️ Direct API fallback failed: {e}")
        
        # If all methods fail
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
        """Move mouse to absolute position using hardware-level input."""
        # Convert screen coordinates to virtual desktop coordinates
        virtual_x = x - self.virtual_left
        virtual_y = y - self.virtual_top
        
        # Convert to absolute coordinates (0-65535 range) within virtual desktop
        abs_x = int((virtual_x * 65535) / self.virtual_width)
        abs_y = int((virtual_y * 65535) / self.virtual_height)
        
        # Create mouse move input
        mouse_input = self._create_mouse_input(
            abs_x, abs_y, 
            MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
        )
        
        self._send_input(mouse_input)
    
    def click_at(self, x: int, y: int, button: str = 'left', duration: float = 0.05):
        """Click at specific coordinates with hardware-level input."""
        # Move to position first
        self.move_to(x, y)
        
        if button == 'left':
            down_flag = MOUSEEVENTF_LEFTDOWN
            up_flag = MOUSEEVENTF_LEFTUP
        elif button == 'right':
            down_flag = MOUSEEVENTF_RIGHTDOWN
            up_flag = MOUSEEVENTF_RIGHTUP
        else:
            raise ValueError("Button must be 'left' or 'right'")
        
        # Convert screen coordinates to virtual desktop coordinates
        virtual_x = x - self.virtual_left
        virtual_y = y - self.virtual_top
        
        # Convert to absolute coordinates (0-65535 range) within virtual desktop
        abs_x = int((virtual_x * 65535) / self.virtual_width)
        abs_y = int((virtual_y * 65535) / self.virtual_height)
        
        # Mouse down
        down_input = self._create_mouse_input(abs_x, abs_y, down_flag | MOUSEEVENTF_ABSOLUTE)
        self._send_input(down_input)
        
        # Hold for duration
        time.sleep(duration)
        
        # Mouse up
        up_input = self._create_mouse_input(abs_x, abs_y, up_flag | MOUSEEVENTF_ABSOLUTE)
        self._send_input(up_input)
    


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