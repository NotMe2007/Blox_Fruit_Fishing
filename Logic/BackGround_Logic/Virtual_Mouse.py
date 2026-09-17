"""
Mouse input through the documented Windows SendInput API.
Success means Windows accepted an event, not that the game acted on it.
"""
import ctypes
import ctypes.wintypes
import time
import math
import random
from typing import Tuple, Optional

# Win32 helpers for checking the target window
try:
    import win32api
    import win32con
    import win32gui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

# Debug Logger - Import from centralized Import_Utils
try:
    from .Import_Utils import debug_log, LogCategory, DEBUG_LOGGER_AVAILABLE  # type: ignore
except ImportError:
    try:
        from Import_Utils import debug_log, LogCategory, DEBUG_LOGGER_AVAILABLE  # type: ignore
    except ImportError:
        # Final fallback if Import_Utils not available
        from enum import Enum
        class LogCategory(Enum):  # type: ignore
            MOUSE = "MOUSE"
            SYSTEM = "SYSTEM"
            ERROR = "ERROR"
        def debug_log(category, message):  # type: ignore
            print(f"[{category.value}] {message}")
        DEBUG_LOGGER_AVAILABLE = False


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

try:
    from .Windows_Input import INPUT, MOUSEINPUT, KEYBDINPUT, HARDWAREINPUT
except ImportError:
    from Windows_Input import INPUT, MOUSEINPUT, KEYBDINPUT, HARDWAREINPUT


class VirtualMouse:
    """
    Foreground mouse input with checked SendInput results.
    """
    
    def __init__(self):
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.user32.SendInput.argtypes = [ctypes.wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
        self.user32.SendInput.restype = ctypes.wintypes.UINT
        self.kernel32 = ctypes.windll.kernel32
        debug_log(LogCategory.SYSTEM, "Mouse backend: Windows SendInput (foreground input)")
        
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

        # Lazy-loaded window manager helpers (avoid circular import during startup)
        self._window_manager_resolved = False
        self._window_manager_warning_logged = False
        self._get_hwnd_func = None
        self._ensure_focus_func = None

    def _resolve_window_manager(self) -> bool:
        """Resolve Roblox window helpers lazily to avoid circular imports."""
        if self._window_manager_resolved and self._get_hwnd_func:
            return True
        try:
            from .Window_Manager import get_roblox_hwnd, ensure_roblox_focused  # type: ignore
        except ImportError:
            try:
                from Window_Manager import get_roblox_hwnd, ensure_roblox_focused  # type: ignore
            except ImportError:
                if not self._window_manager_warning_logged:
                    debug_log(LogCategory.MOUSE, "⚠️ Window Manager not available for stealth input routing")
                    self._window_manager_warning_logged = True
                return False
        self._get_hwnd_func = get_roblox_hwnd  # type: ignore
        self._ensure_focus_func = ensure_roblox_focused  # type: ignore
        self._window_manager_resolved = True
        debug_log(LogCategory.MOUSE, "🔗 Window Manager linked for stealth mouse input")
        return True

    def _screen_to_client(self, hwnd, x: int, y: int) -> Optional[Tuple[int, int]]:
        """Convert screen coordinates to Roblox client-area coordinates using Win32 helper."""
        if not WIN32_AVAILABLE:
            return None
        try:
            client_x, client_y = win32gui.ScreenToClient(hwnd, (x, y))  # type: ignore
            left, top, right, bottom = win32gui.GetClientRect(hwnd)  # type: ignore
            client_x = max(left, min(client_x, right - 1))
            client_y = max(top, min(client_y, bottom - 1))
            return client_x, client_y
        except Exception as e:
            debug_log(LogCategory.ERROR, f"❌ ScreenToClient conversion failed: {e}")
            return None

    def get_cursor_pos(self) -> Tuple[int, int]:
        """Get current cursor position using Windows API."""
        point = POINT()
        self.user32.GetCursorPos(ctypes.byref(point))
        return point.x, point.y
    
    def _send_input(self, *inputs):
        """Return the actual number of events accepted by Windows."""
        if not inputs:
            return 0
        try:
            buffer = (INPUT * len(inputs))(*inputs)
            ctypes.set_last_error(0)
            sent = self.user32.SendInput(len(inputs), buffer, ctypes.sizeof(INPUT))
            if sent != len(inputs):
                debug_log(LogCategory.ERROR,
                          f"SendInput accepted {sent}/{len(inputs)} events; "
                          f"Windows error={ctypes.get_last_error()}. "
                          "Check focus and run Roblox and the launcher at the same privilege level.")
            return sent
        except (OSError, ctypes.ArgumentError) as exc:
            debug_log(LogCategory.ERROR, f"SendInput failed: {exc}")
            return 0

    def _target_ready(self, x, y):
        """Do not press a button in another app or outside the game client."""
        if not WIN32_AVAILABLE or not self._resolve_window_manager():
            return False
        hwnd = self._get_hwnd_func()
        if not hwnd or win32gui.GetForegroundWindow() != hwnd or win32gui.IsIconic(hwnd):
            debug_log(LogCategory.ERROR, "Mouse input skipped: bring Roblox to the foreground.")
            return False
        cx, cy = win32gui.ScreenToClient(hwnd, (int(x), int(y)))
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        return left <= cx < right and top <= cy < bottom

    def _create_mouse_input(self, dx: int, dy: int, flags: int) -> INPUT:
        """Create a mouse input structure."""
        mouse_input = MOUSEINPUT()
        mouse_input.dx = dx
        mouse_input.dy = dy
        mouse_input.mouseData = 0
        mouse_input.dwFlags = flags
        mouse_input.time = 0
        mouse_input.dwExtraInfo = 0
        
        input_struct = INPUT()
        input_struct.type = INPUT_MOUSE
        input_struct.mi = mouse_input
        return input_struct
    
    def move_to(self, x: int, y: int):
        """Move mouse to specific coordinates using reliable Windows API."""
        try:
            debug_log(LogCategory.MOUSE, f"🖱️ [STEALTH] Moving to ({x}, {y})")
            
            # Ensure coordinates are within screen bounds
            x = max(self.virtual_left, min(x, self.virtual_left + self.virtual_width - 1))
            y = max(self.virtual_top, min(y, self.virtual_top + self.virtual_height - 1))
            
            # Use reliable SetCursorPos for movement
            result = self.user32.SetCursorPos(x, y)
            
            if result:
                debug_log(LogCategory.MOUSE, f"✅ [STEALTH] Move completed to ({x}, {y})")
            else:
                debug_log(LogCategory.ERROR, f"❌ Move failed to ({x}, {y})")
                
        except Exception as e:
            debug_log(LogCategory.ERROR, f"❌ Move failed to ({x}, {y}): {e}")
    
    def smooth_move_to(self, x: int, y: int, duration: float = 0.22):
        """Fast interpolated movement; never fall back to teleporting on failure."""
        point = POINT()
        if not self.user32.GetCursorPos(ctypes.byref(point)):
            return False
        steps = max(8, round(max(0, duration) * 60))
        for step in range(1, steps + 1):
            progress = step / steps
            eased = progress * progress * (3 - 2 * progress)
            px = round(point.x + (x - point.x) * eased)
            py = round(point.y + (y - point.y) * eased)
            if not self.user32.SetCursorPos(px, py):
                return False
            time.sleep(max(0, duration) / steps)
        return True

    def _prepare_click(self, x, y):
        """Move first, allow the game to update hover, then recheck focus."""
        if not self._target_ready(x, y):
            return False
        if not self.smooth_move_to(x, y, duration=0.22):
            return False
        time.sleep(0.15)
        return self._target_ready(x, y)

    def _press_button(self, button):
        flags = {'left': MOUSEEVENTF_LEFTDOWN, 'right': MOUSEEVENTF_RIGHTDOWN}
        if button not in flags:
            raise ValueError("Button must be 'left' or 'right'")
        return self._send_input(self._create_mouse_input(0, 0, flags[button])) == 1

    def cast_hold(self, x, y, duration=0.93, observe=None):
        """A settled left-button hold, with movement separate from button input."""
        if not self._target_ready(x, y):
            return False
        # Clear a leftover synthetic hold before beginning a new cast.
        if not self.mouse_up(x, y, 'left'):
            return False
        if not self._prepare_click(x, y):
            print("Cast input failed: movement or foreground check failed.")
            return False
        if not self._press_button('left'):
            return False
        try:
            # Give Windows time to update its asynchronous button state.
            time.sleep(0.03)
            held = bool(self.user32.GetAsyncKeyState(0x01) & 0x8000)
            print(f"Cast input: left DOWN accepted; Windows held={held}; hold={duration:.2f}s")
            if observe is None:
                time.sleep(max(0, duration - 0.03))
            else:
                # Observe while the button is down: the meter disappears on release.
                deadline = time.monotonic() + max(0, duration - 0.03)
                while True:
                    observe()
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    time.sleep(min(0.05, remaining))
        finally:
            released = self.mouse_up(x, y, 'left')
            print(f"Cast input: left UP accepted={released}")
        return held and released

    def relative_drag(self, x, y, dx, dy, button='right', duration=0.8):
        """Relative motion works with games that lock/recenter the cursor."""
        if not self.mouse_down(x, y, button):
            return False
        moved = True
        try:
            steps = max(1, int(duration * 60))
            previous_x = previous_y = 0
            for i in range(1, steps + 1):
                if not self._target_ready(x, y):
                    moved = False
                    break
                next_x, next_y = round(dx*i/steps), round(dy*i/steps)
                event = self._create_mouse_input(next_x-previous_x, next_y-previous_y, MOUSEEVENTF_MOVE)
                if self._send_input(event) != 1:
                    moved = False
                    break
                previous_x, previous_y = next_x, next_y
                time.sleep(max(0, duration)/steps)
        finally:
            released = self.mouse_up(x, y, button)
        return moved and released

    def ultimate_stealth_click(self, x: int, y: int, button: str = 'left', duration: float = 0.05):
        """Compatibility alias for callers using the previous method name."""
        return self.click_at(x, y, button, duration)

    def click_at(self, x: int, y: int, button: str = 'left', duration: float = 0.05):
        """Press, hold, and always attempt release, even if the wait is interrupted."""
        if not self._prepare_click(x, y) or not self._press_button(button):
            return False
        try:
            time.sleep(max(0.05, duration))
        finally:
            released = self.mouse_up(x, y, button)
        return released

    def stealth_click_window(self, hwnd, x: int, y: int, button: str = 'left', *, duration: float = 0.05):
        """Compatibility for client-coordinate callers; requires the foreground target."""
        if not WIN32_AVAILABLE or win32gui.GetForegroundWindow() != hwnd:
            return False
        sx, sy = win32gui.ClientToScreen(hwnd, (x, y))
        return self.click_at(sx, sy, button, duration)

    def human_like_move(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.3):
        """Move mouse with human-like curved path and variable speed."""
        try:
            import random
            import math
            
            # Calculate steps for smooth movement with variable speed
            steps = max(8, int(duration * 30))  # 30 FPS base with minimum steps
            
            # Add curve to movement for more human-like behavior
            curve_intensity = random.uniform(0.1, 0.4)  # How much curve to add
            curve_direction = random.choice([-1, 1])  # Curve left or right
            
            for i in range(steps + 1):
                progress = i / steps
                
                # Use variable speed (slow start, fast middle, slow end)
                ease_progress = self.ease_in_out_cubic(progress)
                
                # Calculate base position
                current_x = start_x + (end_x - start_x) * ease_progress
                current_y = start_y + (end_y - start_y) * ease_progress
                
                # Add curve to make movement more human-like
                if i > 0 and i < steps:  # Don't curve at start/end points
                    curve_offset = math.sin(progress * math.pi) * curve_intensity * curve_direction
                    # Apply curve perpendicular to movement direction
                    dx = end_x - start_x
                    dy = end_y - start_y
                    length = math.sqrt(dx*dx + dy*dy)
                    if length > 0:
                        # Perpendicular vector for curve
                        perp_x = -dy / length
                        perp_y = dx / length
                        current_x += perp_x * curve_offset * 20  # Scale curve
                        current_y += perp_y * curve_offset * 20
                
                # Ensure coordinates are valid
                current_x = int(max(self.virtual_left, min(current_x, self.virtual_left + self.virtual_width - 1)))
                current_y = int(max(self.virtual_top, min(current_y, self.virtual_top + self.virtual_height - 1)))
                
                self.user32.SetCursorPos(current_x, current_y)
                
                if i < steps:  # Don't sleep on last iteration
                    # Variable speed timing with small random variations
                    step_delay = (duration / steps) * random.uniform(0.7, 1.3)
                    time.sleep(step_delay)
                    
        except Exception as e:
            debug_log(LogCategory.ERROR, f"❌ Human-like move failed: {e}")
            # Fallback to direct movement
            self.user32.SetCursorPos(end_x, end_y)
    
    def ease_in_out_cubic(self, t: float) -> float:
        """Easing function for natural acceleration/deceleration."""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2

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
        """Move and press using physical coordinates on the virtual desktop."""
        flags = {'left': MOUSEEVENTF_LEFTDOWN, 'right': MOUSEEVENTF_RIGHTDOWN}
        if button not in flags:
            raise ValueError("Button must be 'left' or 'right'")
        if not self._target_ready(x, y):
            return False
        left, top, width, height = (self.user32.GetSystemMetrics(i) for i in (76,77,78,79))
        if width <= 0 or height <= 0 or not (left <= x < left+width and top <= y < top+height):
            return False
        # Map pixel centers into SendInput's 0..65535 virtual-desktop space.
        dx = min(65535, int(((x-left)+0.5)*65536/width))
        dy = min(65535, int(((y-top)+0.5)*65536/height))
        event = self._create_mouse_input(dx, dy, flags[button] | MOUSEEVENTF_MOVE |
                                         MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK)
        return self._send_input(event) == 1

    def mouse_up(self, x: int, y: int, button: str = 'left'):
        """Release without moving the cursor, even if focus changed during a hold."""
        flags = {'left': MOUSEEVENTF_LEFTUP, 'right': MOUSEEVENTF_RIGHTUP}
        if button not in flags:
            raise ValueError("Button must be 'left' or 'right'")
        event = self._create_mouse_input(0, 0, flags[button])
        return self._send_input(event) == 1

# Global instance for easy access
virtual_mouse = VirtualMouse()
