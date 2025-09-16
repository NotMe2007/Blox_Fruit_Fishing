"""
Virtual Mouse Driver using Windows API for undetectable mouse input.
Uses low-level Windows API calls to simulate hardware mouse input.
"""
import ctypes
import ctypes.wintypes
import time
import random
import math
from typing import Tuple, Optional


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

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    
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
        
        print(f"Virtual desktop: Left={self.virtual_left}, Top={self.virtual_top}, Width={self.virtual_width}, Height={self.virtual_height}")
        
        # Also get primary screen dimensions for fallback
        self.primary_width = self.user32.GetSystemMetrics(0)
        self.primary_height = self.user32.GetSystemMetrics(1)
    
    def get_cursor_pos(self) -> Tuple[int, int]:
        """Get current cursor position using Windows API."""
        point = POINT()
        self.user32.GetCursorPos(ctypes.byref(point))
        return point.x, point.y
    
    def _send_input(self, *inputs):
        """Send input using Windows API."""
        nInputs = len(inputs)
        LPINPUT = INPUT * nInputs
        pInputs = LPINPUT(*inputs)
        cbSize = ctypes.c_int(ctypes.sizeof(INPUT))
        return self.user32.SendInput(nInputs, pInputs, cbSize)
    
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
        time.sleep(random.uniform(0.01, 0.03))  # Small random delay
        
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
    
    def smooth_move_to(self, target_x: int, target_y: int, duration: Optional[float] = None):
        """
        Smoothly move mouse to target position with human-like curves.
        Uses hardware-level input for maximum stealth.
        """
        start_x, start_y = self.get_cursor_pos()
        
        # Calculate distance and auto-adjust duration if not specified
        distance = math.sqrt((target_x - start_x) ** 2 + (target_y - start_y) ** 2)
        if duration is None:
            # Fast but natural movement timing
            duration = min(0.05 + distance * 0.0003, 0.25)
        
        # Add slight random variation
        duration = duration * random.uniform(0.9, 1.1)
        
        # Calculate number of steps for smooth movement
        steps = max(8, int(duration * 80))  # Higher frequency for smoother movement
        
        # Generate bezier curve control points for natural movement
        control_factor = random.uniform(0.05, 0.12)
        mid_x = (start_x + target_x) / 2 + random.randint(-8, 8) * control_factor
        mid_y = (start_y + target_y) / 2 + random.randint(-8, 8) * control_factor
        
        for i in range(steps + 1):
            progress = i / steps
            
            # Smooth acceleration/deceleration (ease-in-out)
            smooth_progress = 0.5 - 0.5 * math.cos(progress * math.pi)
            
            # Quadratic bezier curve
            t = smooth_progress
            x = (1-t)**2 * start_x + 2*(1-t)*t * mid_x + t**2 * target_x
            y = (1-t)**2 * start_y + 2*(1-t)*t * mid_y + t**2 * target_y
            
            # Add micro-jitter for realism
            jitter_x = random.uniform(-0.3, 0.3)
            jitter_y = random.uniform(-0.3, 0.3)
            
            final_x = int(x + jitter_x)
            final_y = int(y + jitter_y)
            
            # Use hardware-level movement
            self.move_to(final_x, final_y)
            
            # Variable timing for natural movement
            step_delay = duration / steps
            step_delay *= random.uniform(0.8, 1.2)
            time.sleep(step_delay)
    
    def human_click(self, x: int, y: int, button: str = 'left'):
        """
        Perform human-like click with random patterns using hardware input.
        """
        # Add small random offset
        offset_x = random.randint(-2, 2)
        offset_y = random.randint(-2, 2)
        final_x = x + offset_x
        final_y = y + offset_y
        
        # Smooth movement to target
        self.smooth_move_to(final_x, final_y)
        
        # Random pre-click pause
        time.sleep(random.uniform(0.03, 0.08))
        
        # Random click pattern
        click_pattern = random.randint(1, 4)
        
        if click_pattern == 1:
            # Quick single click
            self.click_at(final_x, final_y, button, random.uniform(0.04, 0.07))
            
        elif click_pattern == 2:
            # Double click (sometimes humans do this)
            self.click_at(final_x, final_y, button, random.uniform(0.03, 0.05))
            time.sleep(random.uniform(0.02, 0.04))
            self.click_at(final_x, final_y, button, random.uniform(0.03, 0.05))
            
        elif click_pattern == 3:
            # Held click
            self.click_at(final_x, final_y, button, random.uniform(0.08, 0.14))
            
        else:
            # Normal click with variation
            self.click_at(final_x, final_y, button, random.uniform(0.05, 0.09))
        
        # Random post-click pause
        time.sleep(random.uniform(0.08, 0.15))
        
        return True
    
    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 1.0):
        """
        Perform drag operation using hardware input.
        """
        # Move to start position
        self.smooth_move_to(start_x, start_y)
        time.sleep(random.uniform(0.05, 0.1))
        
        # Convert to absolute coordinates for start position
        virtual_start_x = start_x - self.virtual_left
        virtual_start_y = start_y - self.virtual_top
        abs_start_x = int((virtual_start_x * 65535) / self.virtual_width)
        abs_start_y = int((virtual_start_y * 65535) / self.virtual_height)
        
        # Mouse down at start
        down_input = self._create_mouse_input(
            abs_start_x, abs_start_y, 
            MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE
        )
        self._send_input(down_input)
        
        # Drag to end position
        steps = max(10, int(duration * 60))
        
        for i in range(steps):
            progress = (i + 1) / steps
            # Smooth progress curve
            smooth_progress = 0.5 - 0.5 * math.cos(progress * math.pi)
            
            x = start_x + (end_x - start_x) * smooth_progress
            y = start_y + (end_y - start_y) * smooth_progress
            
            # Add slight jitter during drag
            jitter_x = random.uniform(-0.5, 0.5)
            jitter_y = random.uniform(-0.5, 0.5)
            
            final_x = int(x + jitter_x)
            final_y = int(y + jitter_y)
            
            self.move_to(final_x, final_y)
            time.sleep(duration / steps * random.uniform(0.8, 1.2))
        
        # Mouse up at end
        virtual_end_x = end_x - self.virtual_left
        virtual_end_y = end_y - self.virtual_top
        abs_end_x = int((virtual_end_x * 65535) / self.virtual_width)
        abs_end_y = int((virtual_end_y * 65535) / self.virtual_height)
        
        up_input = self._create_mouse_input(
            abs_end_x, abs_end_y, 
            MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE
        )
        self._send_input(up_input)
    
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