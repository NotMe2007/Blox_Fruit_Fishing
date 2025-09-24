"""
Window Manager for Roblox Focus and Screen Detection
Handles finding Roblox window and getting its proper coordinates
"""

import win32gui
import win32con
import win32process
import pyautogui
import time

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
        """Bring the Roblox window to front and focus it."""
        if not self.is_window_valid():
            if not self.find_roblox_window():
                return False
        
        try:
            # Restore if minimized
            if win32gui.IsIconic(self.roblox_hwnd): # type: ignore
                win32gui.ShowWindow(self.roblox_hwnd, win32con.SW_RESTORE)
                time.sleep(0.5)
            
            # Try to bring to front
            win32gui.SetForegroundWindow(self.roblox_hwnd) # pyright: ignore[reportArgumentType]
            win32gui.BringWindowToTop(self.roblox_hwnd) # type: ignore
            
            debug_log(LogCategory.WINDOW_MANAGEMENT, "Roblox window brought to front")
            return True
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Failed to bring Roblox to front: {e}")
            # If API calls fail, try clicking on the window
            try:
                center_x, center_y = self.get_window_center()
                if center_x and center_y:
                    pyautogui.click(center_x, center_y)
                    time.sleep(0.5)
                    debug_log(LogCategory.WINDOW_MANAGEMENT, "Clicked Roblox window to focus it")
                    return True
            except Exception as e2:
                debug_log(LogCategory.ERROR, f"Click focus also failed: {e2}")
            
            return False
    
    def is_roblox_focused(self):
        """Check if Roblox is currently the focused window."""
        try:
            foreground_hwnd = win32gui.GetForegroundWindow()
            return foreground_hwnd == self.roblox_hwnd
        except Exception:
            return False


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