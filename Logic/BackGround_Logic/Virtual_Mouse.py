"""
Virtual Mouse Driver using Windows API for undetectable mouse input.
Uses low-level Windows API calls to simulate hardware mouse input.
"""
import ctypes
import ctypes.wintypes
import time
import math
import random
from typing import Tuple, Optional

# Win32 API for PostMessage stealth clicking (bypasses anti-cheat)
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

    def _postmessage_mouse_event(self, x: int, y: int, button: str, is_down: bool) -> bool:
        """Attempt stealth mouse button event via PostMessage."""
        if not WIN32_AVAILABLE:
            return False
        if not self._resolve_window_manager() or self._get_hwnd_func is None:
            return False
        hwnd = self._get_hwnd_func()
        if not hwnd:
            return False
        client_coords = self._screen_to_client(hwnd, x, y)
        if client_coords is None:
            return False
        client_x, client_y = client_coords
        jitter_x = random.randint(-1, 1)
        jitter_y = random.randint(-1, 1)
        final_x = max(0, client_x + jitter_x)
        final_y = max(0, client_y + jitter_y)
        message = None
        wparam = 0
        if button == 'left':
            message = win32con.WM_LBUTTONDOWN if is_down else win32con.WM_LBUTTONUP  # type: ignore
            wparam = win32con.MK_LBUTTON if is_down else 0  # type: ignore
        elif button == 'right':
            message = win32con.WM_RBUTTONDOWN if is_down else win32con.WM_RBUTTONUP  # type: ignore
            wparam = win32con.MK_RBUTTON if is_down else 0  # type: ignore
        else:
            raise ValueError("Button must be 'left' or 'right'")
        lparam = win32api.MAKELONG(final_x, final_y)  # type: ignore
        try:
            win32gui.PostMessage(hwnd, message, wparam, lparam)  # type: ignore
            phase = "DOWN" if is_down else "UP"
            debug_log(LogCategory.MOUSE, f"🕵️ [STEALTH-POSTMSG] {button.title()} {phase} via PostMessage at ({final_x}, {final_y})")
            if is_down:
                time.sleep(random.uniform(0.01, 0.03))
            return True
        except Exception as e:
            debug_log(LogCategory.ERROR, f"❌ PostMessage mouse event failed: {e}")
            return False
    
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
        """Move mouse to specific coordinates using reliable Windows API."""
        try:
            debug_log(LogCategory.MOUSE, f"🖱️ [STEALTH] Moving to ({x}, {y})")
            
            # Ensure coordinates are within screen bounds
            x = max(0, min(x, self.primary_width - 1))
            y = max(0, min(y, self.primary_height - 1))
            
            # Use reliable SetCursorPos for movement
            result = self.user32.SetCursorPos(x, y)
            
            if result:
                debug_log(LogCategory.MOUSE, f"✅ [STEALTH] Move completed to ({x}, {y})")
            else:
                debug_log(LogCategory.ERROR, f"❌ Move failed to ({x}, {y})")
                
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
    
    def ultimate_stealth_click(self, x: int, y: int, button: str = 'left', duration: float = 0.05):
        """
        ULTIMATE STEALTH CLICK: Automatically chooses the best clicking method.
        Priority: PostMessage stealth > Regular enhanced click
        """
        try:
            # Try to get Roblox window handle for stealth clicking
            if WIN32_AVAILABLE:
                try:
                    from .Window_Manager import get_roblox_hwnd
                    hwnd = get_roblox_hwnd()
                    
                    if hwnd:
                        debug_log(LogCategory.MOUSE, f"🎯 [ULTIMATE-STEALTH] Using PostMessage stealth click")
                        
                        # Convert screen coordinates to window-relative coordinates
                        # For PostMessage, we need coordinates relative to the window client area
                        import win32gui
                        window_rect = win32gui.GetWindowRect(hwnd)
                        client_rect = win32gui.GetClientRect(hwnd)
                        
                        # Calculate the offset for window borders/title bar
                        border_x = (window_rect[2] - window_rect[0] - client_rect[2]) // 2
                        title_height = window_rect[3] - window_rect[1] - client_rect[3] - border_x
                        
                        # Convert to window-relative coordinates
                        window_x = x - window_rect[0] - border_x
                        window_y = y - window_rect[1] - title_height
                        
                        # Ensure coordinates are within the client area
                        window_x = max(0, min(window_x, client_rect[2] - 1))
                        window_y = max(0, min(window_y, client_rect[3] - 1))
                        
                        debug_log(LogCategory.MOUSE, f"🕵️ [ULTIMATE-STEALTH] Screen ({x},{y}) -> Window ({window_x},{window_y})")
                        
                        # Use stealth PostMessage clicking
                        return self.stealth_click_window(hwnd, window_x, window_y, button)
                        
                except ImportError:
                    debug_log(LogCategory.MOUSE, "⚠️ Window Manager not available, using regular enhanced click")
                except Exception as e:
                    debug_log(LogCategory.MOUSE, f"⚠️ Stealth click setup failed: {e}, falling back to enhanced click")
            
            # Fallback to regular enhanced clicking
            debug_log(LogCategory.MOUSE, f"🎯 [ULTIMATE-STEALTH] Using enhanced hardware click as fallback")
            return self.click_at(x, y, button, duration)
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"❌ Ultimate stealth click failed: {e}")
            return False
    
    def click_at(self, x: int, y: int, button: str = 'left', duration: float = 0.05):
        """
        Enhanced stealth click method with AHK-style window focus.
        Based on Reddit post: Window focus before clicking is CRITICAL for Roblox automation.
        """
        try:
            debug_log(LogCategory.MOUSE, f"🎯 [ULTRA-STEALTH] Initiating enhanced click at ({x}, {y})")
            
            # CRITICAL: Ensure Roblox window is focused before clicking (AHK-style)
            # This was the key insight from the Reddit post that made automation work
            self._ensure_window_focus_before_click()
            
            # Ensure coordinates are within screen bounds
            x = max(0, min(x, self.primary_width - 1))
            y = max(0, min(y, self.primary_height - 1))
            
            # Get current mouse position for natural movement
            current_pos = POINT()
            self.user32.GetCursorPos(ctypes.byref(current_pos))
            start_x, start_y = current_pos.x, current_pos.y
            
            # Add stronger anti-detection randomization
            import random
            jitter_x = random.randint(-5, 5)  # Increased jitter range
            jitter_y = random.randint(-5, 5)
            final_x = max(0, min(x + jitter_x, self.primary_width - 1))
            final_y = max(0, min(y + jitter_y, self.primary_height - 1))
            
            # Phase 1: Natural approach movement (critical for anti-detection)
            distance = ((final_x - start_x) ** 2 + (final_y - start_y) ** 2) ** 0.5
            if distance > 10:  # Only do approach if movement is significant
                # Calculate intermediate positions for human-like movement
                approach_distance = random.randint(15, 35)  # Distance from target for approach
                angle = random.uniform(0, 2 * 3.14159)  # Random approach angle
                
                approach_x = final_x + int(approach_distance * math.cos(angle))
                approach_y = final_y + int(approach_distance * math.sin(angle))
                
                # Ensure approach point is on screen
                approach_x = max(0, min(approach_x, self.primary_width - 1))
                approach_y = max(0, min(approach_y, self.primary_height - 1))
                
                debug_log(LogCategory.MOUSE, f"🛡️ [ULTRA-STEALTH] Natural approach via ({approach_x}, {approach_y})")
                
                # Move to approach position with human-like curve
                self.human_like_move(start_x, start_y, approach_x, approach_y, random.uniform(0.2, 0.5))
                
                # Brief pause at approach position (human hesitation)
                time.sleep(random.uniform(0.1, 0.3))
                
                # Final approach to target with slight curve
                self.human_like_move(approach_x, approach_y, final_x, final_y, random.uniform(0.1, 0.25))
            else:
                # Short distance - just add slight randomized movement
                self.user32.SetCursorPos(final_x, final_y)
            
            # Phase 2: Pre-click stabilization (critical anti-detection)
            time.sleep(random.uniform(0.05, 0.15))  # Human stabilization delay
            
            # Phase 3: Enhanced click execution with variable timing
            click_duration = duration + random.uniform(-0.03, 0.08)  # More variable duration
            click_duration = max(0.02, click_duration)  # Minimum reasonable duration
            
            if button == 'left':
                debug_log(LogCategory.MOUSE, f"🛡️ [ULTRA-STEALTH] Hardware left click (duration: {click_duration:.3f}s)")
                self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(click_duration)
                self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                
            elif button == 'right':
                debug_log(LogCategory.MOUSE, f"🛡️ [ULTRA-STEALTH] Hardware right click (duration: {click_duration:.3f}s)")
                self.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                time.sleep(click_duration)
                self.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
                
            else:
                raise ValueError("Button must be 'left' or 'right'")
            
            # Phase 4: Post-click natural behavior
            post_click_delay = random.uniform(0.1, 0.4)  # Human post-click delay
            time.sleep(post_click_delay)
            
            # Optional: Small post-click movement to simulate natural mouse behavior
            if random.choice([True, False]):  # 50% chance of small post-click movement
                small_move_x = final_x + random.randint(-3, 3)
                small_move_y = final_y + random.randint(-3, 3)
                small_move_x = max(0, min(small_move_x, self.primary_width - 1))
                small_move_y = max(0, min(small_move_y, self.primary_height - 1))
                self.user32.SetCursorPos(small_move_x, small_move_y)
                debug_log(LogCategory.MOUSE, f"🛡️ [ULTRA-STEALTH] Natural post-click movement to ({small_move_x}, {small_move_y})")
            
            debug_log(LogCategory.MOUSE, f"✅ [ULTRA-STEALTH] Enhanced click sequence completed at ({final_x}, {final_y})")
            return True
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"❌ Enhanced click failed at ({x}, {y}): {e}")
            return False
    
    def stealth_click_window(self, hwnd, x: int, y: int, button: str = 'left'):
        """
        ULTIMATE STEALTH: PostMessage clicking that bypasses anti-cheat.
        Key insight: Click BEFORE bringing window to front = Undetectable
        This method clicks while window is in background, then optionally brings to front.
        """
        if not WIN32_AVAILABLE:
            debug_log(LogCategory.ERROR, "❌ Win32 API not available for stealth clicking")
            return False
            
        try:
            debug_log(LogCategory.MOUSE, f"🕵️ [STEALTH-CLICK] PostMessage click at ({x}, {y}) in background window")
            
            # Convert screen coordinates to window client coordinates
            # Note: For PostMessage, we might need to adjust coordinates based on window position
            
            if not WIN32_AVAILABLE:
                debug_log(LogCategory.ERROR, "Win32 API not available for PostMessage clicks")
                return
            
            # Add human-like randomization
            jitter_x = random.randint(-2, 2)
            jitter_y = random.randint(-2, 2)
            final_x = x + jitter_x
            final_y = y + jitter_y
            
            # Create lParam for coordinates (win32api is checked via WIN32_AVAILABLE)
            lParam = win32api.MAKELONG(final_x, final_y)  # type: ignore
            
            if button == 'left':
                debug_log(LogCategory.MOUSE, f"🕵️ [STEALTH-CLICK] Background left click via PostMessage")
                # Send mouse down
                win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)  # type: ignore
                # Human-like click duration
                time.sleep(random.uniform(0.03, 0.08))
                # Send mouse up
                win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)  # type: ignore
                
            elif button == 'right':
                debug_log(LogCategory.MOUSE, f"🕵️ [STEALTH-CLICK] Background right click via PostMessage")
                # Send mouse down
                win32gui.PostMessage(hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lParam)  # type: ignore
                # Human-like click duration
                time.sleep(random.uniform(0.03, 0.08))
                # Send mouse up
                win32gui.PostMessage(hwnd, win32con.WM_RBUTTONUP, 0, lParam)  # type: ignore
            else:
                raise ValueError("Button must be 'left' or 'right'")
            
            # Small delay for message processing
            time.sleep(random.uniform(0.02, 0.05))
            
            debug_log(LogCategory.MOUSE, f"✅ [STEALTH-CLICK] PostMessage click completed successfully")
            return True
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"❌ Stealth click failed: {e}")
            return False
    
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
                current_x = int(max(0, min(current_x, self.primary_width - 1)))
                current_y = int(max(0, min(current_y, self.primary_height - 1)))
                
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
        """Press mouse button down at specified coordinates."""
        if self._postmessage_mouse_event(x, y, button, True):
            return True
        if button == 'left':
            flag = MOUSEEVENTF_LEFTDOWN
        elif button == 'right':
            flag = MOUSEEVENTF_RIGHTDOWN
        else:
            raise ValueError("Button must be 'left' or 'right'")
        virtual_x = x - self.virtual_left
        virtual_y = y - self.virtual_top
        abs_x = int((virtual_x * 65535) / self.virtual_width)
        abs_y = int((virtual_y * 65535) / self.virtual_height)
        debug_log(LogCategory.MOUSE, "⚙️ Falling back to hardware mouse down event")
        down_input = self._create_mouse_input(abs_x, abs_y, flag | MOUSEEVENTF_ABSOLUTE)
        self._send_input(down_input)
        return True
    
    def mouse_up(self, x: int, y: int, button: str = 'left'):
        """Release mouse button at specified coordinates."""
        if self._postmessage_mouse_event(x, y, button, False):
            return True
        if button == 'left':
            flag = MOUSEEVENTF_LEFTUP
        elif button == 'right':
            flag = MOUSEEVENTF_RIGHTUP
        else:
            raise ValueError("Button must be 'left' or 'right'")
        virtual_x = x - self.virtual_left
        virtual_y = y - self.virtual_top
        abs_x = int((virtual_x * 65535) / self.virtual_width)
        abs_y = int((virtual_y * 65535) / self.virtual_height)
        debug_log(LogCategory.MOUSE, "⚙️ Falling back to hardware mouse up event")
        up_input = self._create_mouse_input(abs_x, abs_y, flag | MOUSEEVENTF_ABSOLUTE)
        self._send_input(up_input)
        return True

    def _ensure_window_focus_before_click(self):
        """
        Ensure Roblox window is properly focused before clicking.
        
        Based on Reddit post: This AHK-style window focus is CRITICAL for Roblox automation.
        Without proper focus, clicks are detected/blocked by Roblox anti-automation.
        """
        try:
            if not self._resolve_window_manager() or self._ensure_focus_func is None:
                debug_log(LogCategory.MOUSE, "⚠️ Window Manager not available - skipping focus")
                return
            focus_success = self._ensure_focus_func()
            
            if focus_success:
                debug_log(LogCategory.MOUSE, "✅ [AHK-STYLE] Window focus confirmed before click")
                # Small delay to let focus settle (critical for automation detection)
                time.sleep(0.05)
            else:
                debug_log(LogCategory.MOUSE, "⚠️ [AHK-STYLE] Window focus may have failed - proceeding anyway")
                
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Window focus error: {e}")
            # Continue with click even if focus fails


# Global instance for easy access
virtual_mouse = VirtualMouse()
