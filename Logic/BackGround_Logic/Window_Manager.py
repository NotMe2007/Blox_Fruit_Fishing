"""
Window Manager for Roblox Focus and Screen Detection
Handles finding Roblox window and getting its proper coordinates
Uses VirtualMouse for undetectable input simulation
"""

import win32gui
import win32con
import win32process
import time

# Virtual Mouse for undetectable input
try:
    from .Virtual_Mouse import VirtualMouse
    VIRTUAL_MOUSE_AVAILABLE = True
except ImportError:
    try:
        from Virtual_Mouse import VirtualMouse
        VIRTUAL_MOUSE_AVAILABLE = True
    except ImportError:
        VIRTUAL_MOUSE_AVAILABLE = False

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
            WINDOW_MANAGEMENT = "WINDOW_MANAGEMENT"
            SYSTEM = "SYSTEM"
            ERROR = "ERROR"
        def debug_log(category, message):
            print(f"[{category.value}] {message}")


class RobloxWindowManager:
    def __init__(self):
        self.roblox_hwnd = None
        self.window_rect = None
        self.last_validation = 0
        self.validation_interval = 2.0  # Check window every 2 seconds
        
        # Initialize virtual mouse for undetectable input
        if VIRTUAL_MOUSE_AVAILABLE:
            try:
                self.virtual_mouse = VirtualMouse()
                debug_log(LogCategory.WINDOW_MANAGEMENT, "VirtualMouse initialized successfully")
            except Exception as e:
                debug_log(LogCategory.ERROR, f"Failed to initialize VirtualMouse: {e}")
                self.virtual_mouse = None
        else:
            self.virtual_mouse = None
            debug_log(LogCategory.WINDOW_MANAGEMENT, "VirtualMouse not available - using fallback methods")
    
    def find_roblox_window(self):
        """Find the active Roblox window and get its properties."""
        roblox_windows = []
        
        def enum_callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd).lower()
                
                # Get the process name to distinguish Roblox app from browsers
                try:
                    import psutil
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    process = psutil.Process(pid)
                    process_name = process.name().lower()
                    
                    # Only accept windows from actual Roblox processes, not browsers
                    if ('roblox' in window_title and 
                        ('roblox' in process_name or 'robloxplayerbeta' in process_name) and
                        not any(browser in process_name for browser in ['opera', 'chrome', 'firefox', 'edge', 'safari', 'brave'])):
                        
                        # Prefer Blox Fruits specifically, but accept any Roblox game
                        if 'blox fruits' in window_title:
                            results.insert(0, (hwnd, win32gui.GetWindowText(hwnd)))  # Priority insert
                        else:
                            results.append((hwnd, win32gui.GetWindowText(hwnd)))
                            
                except (ImportError, Exception):
                    # Fallback: Use stricter window title matching if psutil not available
                    if ('roblox' in window_title and 
                        not any(browser in window_title for browser in ['opera', 'chrome', 'firefox', 'edge', 'safari', 'brave']) and
                        'browser' not in window_title):
                        
                        if 'blox fruits' in window_title:
                            results.insert(0, (hwnd, win32gui.GetWindowText(hwnd)))  # Priority insert
                        else:
                            results.append((hwnd, win32gui.GetWindowText(hwnd)))
            return True
        
        try:
            win32gui.EnumWindows(enum_callback, roblox_windows)
            
            if roblox_windows:
                # Windows are already prioritized (Blox Fruits first, then other Roblox games)
                self.roblox_hwnd, title = roblox_windows[0]
                
                # Get window rectangle
                self.window_rect = win32gui.GetWindowRect(self.roblox_hwnd)
                debug_log(LogCategory.WINDOW_MANAGEMENT, f"Found Roblox window: {title}")
                debug_log(LogCategory.WINDOW_MANAGEMENT, f"Window coordinates: {self.window_rect}")
                return True
            else:
                debug_log(LogCategory.WINDOW_MANAGEMENT, "No Roblox window found!")
                return False
                
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Error finding Roblox window: {e}")
            return False
    
    def get_window_center(self):
        """Get the center coordinates of the Roblox window."""
        if not self.is_window_valid():
            if not self.find_roblox_window():
                return None, None
        
        left, top, right, bottom = self.window_rect # type: ignore
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        return center_x, center_y
    
    def get_fishing_cast_position(self):
        """Get the position where we should cast the fishing line (center of Roblox window)."""
        center_x, center_y = self.get_window_center()
        if center_x is None:
            return None, None
        
        # Cast slightly above center for better fishing
        fishing_x = center_x
        fishing_y = center_y - 20 # type: ignore
        return fishing_x, fishing_y
    
    def get_window_region(self):
        """Get the region (left, top, width, height) of the Roblox window for screenshots."""
        if not self.is_window_valid():
            if not self.find_roblox_window():
                return None
        
        left, top, right, bottom = self.window_rect # type: ignore
        width = right - left
        height = bottom - top
        return (left, top, width, height)
    
    def is_window_valid(self):
        """Check if the current window handle is still valid."""
        current_time = time.time()
        
        # Only validate periodically to avoid performance issues
        if current_time - self.last_validation < self.validation_interval:
            return self.roblox_hwnd is not None
        
        self.last_validation = current_time
        
        if self.roblox_hwnd is None:
            return False
        
        try:
            # Check if window still exists and is visible
            if not win32gui.IsWindow(self.roblox_hwnd):
                self.roblox_hwnd = None
                return False
            
            if not win32gui.IsWindowVisible(self.roblox_hwnd):
                self.roblox_hwnd = None
                return False
            
            # Update window rectangle in case it moved
            self.window_rect = win32gui.GetWindowRect(self.roblox_hwnd)
            return True
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Window validation error: {e}")
            self.roblox_hwnd = None
            return False
    
    def bring_to_front(self):
        """
        Enhanced window focus method using multiple techniques including AHK-style focus.
        Based on Reddit post: AHK window.focus() solved Roblox automation detection.
        """
        if not self.is_window_valid():
            if not self.find_roblox_window():
                return False
        
        try:
            # Method 1: AHK-style aggressive window focus (CRITICAL for Roblox automation)
            debug_log(LogCategory.WINDOW_MANAGEMENT, "🎯 Attempting AHK-style aggressive window focus...")
            if self._ahk_style_focus():
                debug_log(LogCategory.WINDOW_MANAGEMENT, "✅ AHK-style focus successful!")
                return True
            
            # Method 2: VirtualMouse gentle click (most undetectable)
            if self.virtual_mouse:
                debug_log(LogCategory.WINDOW_MANAGEMENT, "Attempting gentle focus via VirtualMouse...")
                center_x, center_y = self.get_window_center()
                if center_x and center_y:
                    # Small random offset to appear more human
                    import random
                    offset_x = random.randint(-50, 50)
                    offset_y = random.randint(-50, 50)
                    
                    # Get screen dimensions from VirtualMouse
                    screen_width = self.virtual_mouse.primary_width
                    screen_height = self.virtual_mouse.primary_height
                    
                    click_x = max(0, min(center_x + offset_x, screen_width - 1))
                    click_y = max(0, min(center_y + offset_y, screen_height - 1))
                    
                    # Ultra-stealth PostMessage click with human-like timing
                    success = self.virtual_mouse.ultimate_stealth_click(click_x, click_y)
                    if success:
                        debug_log(LogCategory.WINDOW_MANAGEMENT, f"🛡️ [ULTRA-STEALTH] PostMessage focus click at ({click_x}, {click_y})")
                    else:
                        debug_log(LogCategory.WINDOW_MANAGEMENT, f"🛡️ [ULTRA-STEALTH] Enhanced focus click at ({click_x}, {click_y})")
                    time.sleep(random.uniform(0.2, 0.4))
                    
                    # Check if successful
                    if self.is_roblox_focused():
                        debug_log(LogCategory.WINDOW_MANAGEMENT, "✅ Roblox focused via ultra-stealth click")
                        return True
            
            # Method 3: Alt-Tab simulation (keyboard-based, less detectable)
            debug_log(LogCategory.WINDOW_MANAGEMENT, "Attempting focus via Alt-Tab simulation...")
            return self._alt_tab_to_roblox()
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Failed to bring Roblox to front: {e}")
            return False

    def _ahk_style_focus(self):
        """
        AHK-style window focus that bypasses Roblox automation detection.
        
        This implements the same window focus method that AHK uses which the Reddit user
        found was critical for making automation work in Roblox.
        """
        try:
            import ctypes
            from ctypes import wintypes
            
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            # Get current thread and target window thread
            current_thread = kernel32.GetCurrentThreadId()
            target_thread = user32.GetWindowThreadProcessId(self.roblox_hwnd, None)
            
            debug_log(LogCategory.WINDOW_MANAGEMENT, f"🔧 Current thread: {current_thread}, Target thread: {target_thread}")
            
            # Step 1: Attach to target thread input (critical for Roblox)
            if target_thread != current_thread:
                attach_result = user32.AttachThreadInput(current_thread, target_thread, True)
                debug_log(LogCategory.WINDOW_MANAGEMENT, f"🔗 Thread attach result: {attach_result}")
            
            # Step 2: Multiple focus attempts with different methods
            focus_success = False
            
            # Method A: Smart ShowWindow + SetForegroundWindow (AHK standard but improved)
            # Check if window is minimized before restoring to avoid unwanted resizing
            placement = win32gui.GetWindowPlacement(self.roblox_hwnd)
            window_state = placement[1]  # SW_HIDE=0, SW_NORMAL=1, SW_MINIMIZED=2, SW_MAXIMIZED=3
            
            debug_log(LogCategory.WINDOW_MANAGEMENT, f"🔍 Current window state: {window_state}")
            
            # Only restore if window is actually minimized (state 2)
            if window_state == 2:  # SW_MINIMIZED
                debug_log(LogCategory.WINDOW_MANAGEMENT, "📏 Window is minimized - restoring...")
                user32.ShowWindow(self.roblox_hwnd, win32con.SW_RESTORE)
                time.sleep(0.1)  # Give time for restore animation
            else:
                debug_log(LogCategory.WINDOW_MANAGEMENT, "✅ Window already visible - skipping restore")
            
            foreground_result = user32.SetForegroundWindow(self.roblox_hwnd)
            debug_log(LogCategory.WINDOW_MANAGEMENT, f"🎯 SetForegroundWindow result: {foreground_result}")
            
            if foreground_result:
                focus_success = True
            
            # Method B: BringWindowToTop (gentle - no size changes)
            user32.BringWindowToTop(self.roblox_hwnd)
            time.sleep(0.05)
            
            # Method C: SetActiveWindow (for input focus)
            user32.SetActiveWindow(self.roblox_hwnd)
            time.sleep(0.05)
            
            # Method D: SetFocus (final input ensure)
            user32.SetFocus(self.roblox_hwnd)
            time.sleep(0.1)
            
            # Step 3: Detach thread input
            if target_thread != current_thread:
                user32.AttachThreadInput(current_thread, target_thread, False)
                debug_log(LogCategory.WINDOW_MANAGEMENT, "🔓 Thread detached")
            
            # Step 4: Verify focus success
            verification_success = self.is_roblox_focused()
            debug_log(LogCategory.WINDOW_MANAGEMENT, f"🔍 Focus verification: {verification_success}")
            
            # Step 5: Additional input state reset (critical for automation)
            if verification_success:
                self._reset_input_state()
            
            return verification_success
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"❌ AHK-style focus failed: {e}")
            return False
    
    def _reset_input_state(self):
        """
        Reset input state after focus - critical for Roblox automation.
        This ensures that subsequent mouse/keyboard input is properly recognized.
        """
        try:
            import ctypes
            user32 = ctypes.windll.user32
            
            # Reset key states (prevent stuck keys)
            for vk_code in [0x01, 0x02, 0x04]:  # Left, Right, Middle mouse buttons
                user32.keybd_event(vk_code, 0, 0x0002, 0)  # Key up event
            
            # Short delay for state reset
            time.sleep(0.1)
            
            # Reset cursor position slightly to "wake up" input system
            current_pos = win32gui.GetCursorPos()
            user32.SetCursorPos(current_pos[0], current_pos[1])
            
            debug_log(LogCategory.WINDOW_MANAGEMENT, "🔄 Input state reset completed")
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Input state reset failed: {e}")
    
    def _alt_tab_to_roblox(self):
        """Use Alt-Tab behavior to find and focus Roblox window."""
        try:
            # Import keyboard for key simulation
            import keyboard
            
            # Get list of visible windows
            visible_windows = []
            def enum_callback(hwnd, results):
                if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                    results.append((hwnd, win32gui.GetWindowText(hwnd)))
                return True
            
            win32gui.EnumWindows(enum_callback, visible_windows)
            
            # Find Roblox window position in the list
            roblox_index = -1
            for i, (hwnd, title) in enumerate(visible_windows):
                if hwnd == self.roblox_hwnd:
                    roblox_index = i
                    break
            
            if roblox_index == -1:
                return False
            
            # Simulate Alt-Tab with precise timing
            keyboard.press('alt')
            time.sleep(0.05)
            
            # Tab the right number of times (with human-like pauses)
            for _ in range(roblox_index + 1):
                keyboard.press_and_release('tab')
                time.sleep(0.08)  # Human-like tab timing
            
            time.sleep(0.1)
            keyboard.release('alt')
            time.sleep(0.2)
            
            # Verify success
            if self.is_roblox_focused():
                debug_log(LogCategory.WINDOW_MANAGEMENT, "Roblox focused via Alt-Tab simulation")
                return True
                
        except ImportError:
            debug_log(LogCategory.WINDOW_MANAGEMENT, "Keyboard library not available for Alt-Tab simulation")
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Alt-Tab simulation failed: {e}")
        
        return False
    
    def is_roblox_focused(self):
        """Check if Roblox is currently the focused window."""
        try:
            foreground_hwnd = win32gui.GetForegroundWindow()
            return foreground_hwnd == self.roblox_hwnd
        except Exception:
            return False
    
    def get_roblox_hwnd(self):
        """Get the Roblox window handle for stealth clicking operations."""
        if self.roblox_hwnd and self.is_window_valid():
            return self.roblox_hwnd
        return None


# Global instance
roblox_window_manager = RobloxWindowManager()


def get_roblox_coordinates():
    """Get proper Roblox window coordinates for fishing operations."""
    return roblox_window_manager.get_fishing_cast_position()


def get_roblox_window_region():
    """Get Roblox window region for screenshot operations."""
    return roblox_window_manager.get_window_region()


def ensure_roblox_focused():
    """Ensure Roblox window is found and focused."""
    if not roblox_window_manager.is_roblox_focused():
        return roblox_window_manager.bring_to_front()
    return True


def get_roblox_hwnd():
    """Get Roblox window handle for stealth clicking."""
    return roblox_window_manager.get_roblox_hwnd()