"""
Screen Capture Utility using Windows API for undetectable screen capture.
Uses GDI and Win32 API calls to capture screen regions without detection.
Replaces pyautogui.screenshot() functionality.
"""
import ctypes
import ctypes.wintypes
import numpy as np
from PIL import Image
from typing import Tuple, Optional

# Debug Logger - Import from centralized Import_Utils
try:
    from .Import_Utils import debug_log, LogCategory, DEBUG_LOGGER_AVAILABLE
except ImportError:
    try:
        from Import_Utils import debug_log, LogCategory, DEBUG_LOGGER_AVAILABLE
    except ImportError:
        # Final fallback if Import_Utils not available
        from enum import Enum
        class LogCategory(Enum):
            SYSTEM = "SYSTEM"
            ERROR = "ERROR"
            SCREEN_CAPTURE = "SCREEN_CAPTURE"
        def debug_log(category, message):
            print(f"[{category.value}] {message}")
        DEBUG_LOGGER_AVAILABLE = False


# Windows API constants
DIB_RGB_COLORS = 0
SRCCOPY = 0x00CC0020


class ScreenCapture:
    """
    Windows API-based screen capture that bypasses anti-cheat detection.
    Uses GDI functions to capture screen regions directly from graphics memory.
    """
    
    def __init__(self):
        # Get Windows API handles
        self.user32 = ctypes.windll.user32
        self.gdi32 = ctypes.windll.gdi32
        self.kernel32 = ctypes.windll.kernel32
        
        # Get screen dimensions
        self.screen_width = self.user32.GetSystemMetrics(0)  # SM_CXSCREEN
        self.screen_height = self.user32.GetSystemMetrics(1)  # SM_CYSCREEN
        
        debug_log(LogCategory.SYSTEM, f"Screen capture initialized: {self.screen_width}x{self.screen_height}")
    
    def capture_region(self, region: Tuple[int, int, int, int]) -> Optional[Image.Image]:
        """
        Capture a specific region of the screen using Windows GDI.
        
        Args:
            region: (left, top, width, height) tuple
            
        Returns:
            PIL Image object or None if capture fails
        """
        try:
            left, top, width, height = region
            
            # Validate region bounds
            if left < 0 or top < 0 or width <= 0 or height <= 0:
                debug_log(LogCategory.ERROR, f"Invalid region: {region}")
                return None
            
            if left + width > self.screen_width or top + height > self.screen_height:
                debug_log(LogCategory.ERROR, f"Region exceeds screen bounds: {region}")
                return None
            
            debug_log(LogCategory.SCREEN_CAPTURE, f"Capturing region: {region}")
            
            # Get desktop device context
            desktop_dc = self.user32.GetDC(0)
            if not desktop_dc:
                debug_log(LogCategory.ERROR, "Failed to get desktop DC")
                return None
            
            try:
                # Create compatible device context
                mem_dc = self.gdi32.CreateCompatibleDC(desktop_dc)
                if not mem_dc:
                    debug_log(LogCategory.ERROR, "Failed to create compatible DC")
                    return None
                
                try:
                    # Create compatible bitmap
                    bitmap = self.gdi32.CreateCompatibleBitmap(desktop_dc, width, height)
                    if not bitmap:
                        debug_log(LogCategory.ERROR, "Failed to create compatible bitmap")
                        return None
                    
                    try:
                        # Select bitmap into memory DC
                        old_bitmap = self.gdi32.SelectObject(mem_dc, bitmap)
                        if not old_bitmap:
                            debug_log(LogCategory.ERROR, "Failed to select bitmap into DC")
                            return None
                        
                        # Copy screen region to memory bitmap
                        result = self.gdi32.BitBlt(
                            mem_dc, 0, 0, width, height,
                            desktop_dc, left, top, SRCCOPY
                        )
                        
                        if not result:
                            debug_log(LogCategory.ERROR, "BitBlt operation failed")
                            return None
                        
                        # Get bitmap info
                        bmp_info = self._create_bitmap_info(width, height)
                        
                        # Calculate image size
                        image_size = width * height * 4  # 32-bit RGBA
                        
                        # Create buffer for image data
                        buffer = ctypes.create_string_buffer(image_size)
                        
                        # Get bitmap bits
                        lines_copied = self.gdi32.GetDIBits(
                            mem_dc, bitmap, 0, height, buffer, 
                            ctypes.byref(bmp_info), DIB_RGB_COLORS
                        )
                        
                        if lines_copied != height:
                            debug_log(LogCategory.ERROR, f"GetDIBits failed: copied {lines_copied}/{height} lines")
                            return None
                        
                        # Convert to numpy array
                        image_array = np.frombuffer(buffer.raw, dtype=np.uint8)
                        image_array = image_array.reshape((height, width, 4))
                        
                        # Convert BGRA to RGB (Windows bitmap format is BGRA)
                        image_array = image_array[:, :, [2, 1, 0]]  # BGR to RGB
                        
                        # Create PIL Image
                        pil_image = Image.fromarray(image_array, 'RGB')
                        
                        debug_log(LogCategory.SCREEN_CAPTURE, f"✅ Successfully captured {width}x{height} region")
                        return pil_image
                        
                    finally:
                        # Cleanup bitmap - restore original bitmap to DC
                        try:
                            self.gdi32.SelectObject(mem_dc, old_bitmap)
                        except:
                            pass  # Ignore cleanup errors
                        self.gdi32.DeleteObject(bitmap)
                        
                finally:
                    # Cleanup memory DC
                    self.gdi32.DeleteDC(mem_dc)
                    
            finally:
                # Release desktop DC
                self.user32.ReleaseDC(0, desktop_dc)
                
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Screen capture failed: {e}")
            return None
    
    def _create_bitmap_info(self, width: int, height: int):
        """Create BITMAPINFO structure for GetDIBits."""
        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ('biSize', ctypes.wintypes.DWORD),
                ('biWidth', ctypes.wintypes.LONG),
                ('biHeight', ctypes.wintypes.LONG),
                ('biPlanes', ctypes.wintypes.WORD),
                ('biBitCount', ctypes.wintypes.WORD),
                ('biCompression', ctypes.wintypes.DWORD),
                ('biSizeImage', ctypes.wintypes.DWORD),
                ('biXPelsPerMeter', ctypes.wintypes.LONG),
                ('biYPelsPerMeter', ctypes.wintypes.LONG),
                ('biClrUsed', ctypes.wintypes.DWORD),
                ('biClrImportant', ctypes.wintypes.DWORD)
            ]
        
        class BITMAPINFO(ctypes.Structure):
            _fields_ = [
                ('bmiHeader', BITMAPINFOHEADER),
                ('bmiColors', ctypes.wintypes.DWORD * 3)
            ]
        
        bmp_info = BITMAPINFO()
        bmp_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmp_info.bmiHeader.biWidth = width
        bmp_info.bmiHeader.biHeight = -height  # Negative for top-down bitmap
        bmp_info.bmiHeader.biPlanes = 1
        bmp_info.bmiHeader.biBitCount = 32  # 32-bit color
        bmp_info.bmiHeader.biCompression = 0  # BI_RGB
        bmp_info.bmiHeader.biSizeImage = 0
        bmp_info.bmiHeader.biXPelsPerMeter = 0
        bmp_info.bmiHeader.biYPelsPerMeter = 0
        bmp_info.bmiHeader.biClrUsed = 0
        bmp_info.bmiHeader.biClrImportant = 0
        
        return bmp_info
    
    def capture_fullscreen(self) -> Optional[Image.Image]:
        """Capture the entire screen."""
        return self.capture_region((0, 0, self.screen_width, self.screen_height))


# Global instance for easy access
screen_capture = ScreenCapture()


def screenshot(region=None):
    """
    Drop-in replacement for pyautogui.screenshot().
    
    Args:
        region: Optional (left, top, width, height) tuple for region capture
        
    Returns:
        PIL Image object
    """
    try:
        if region is None:
            return screen_capture.capture_fullscreen()
        else:
            return screen_capture.capture_region(region)
    except Exception as e:
        debug_log(LogCategory.ERROR, f"Screenshot function failed: {e}")
        # Fallback to PyAutoGUI if available (for compatibility)
        try:
            import pyautogui
            debug_log(LogCategory.SYSTEM, "Falling back to PyAutoGUI screenshot")
            return pyautogui.screenshot(region=region)
        except ImportError:
            debug_log(LogCategory.ERROR, "No fallback screenshot method available")
            return None