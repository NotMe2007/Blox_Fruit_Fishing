"""Screen capture in physical pixels, including secondary monitors.

Pillow owns native bitmap handles and their cleanup, avoiding ctypes handle
truncation on 64-bit Python. Public regions use (left, top, width, height).
"""
import ctypes
from typing import Optional, Tuple
from PIL import Image, ImageGrab

try:
    from .Display_Utils import enable_dpi_awareness
except ImportError:
    from Display_Utils import enable_dpi_awareness

enable_dpi_awareness()


class ScreenCapture:
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.screen_width = self.user32.GetSystemMetrics(0)
        self.screen_height = self.user32.GetSystemMetrics(1)

    def capture_region(self, region: Tuple[int, int, int, int]) -> Optional[Image.Image]:
        left, top, width, height = region
        if width <= 0 or height <= 0:
            return None
        # Read current virtual desktop bounds; monitor layouts can change.
        x, y, w, h = (self.user32.GetSystemMetrics(i) for i in (76, 77, 78, 79))
        if left < x or top < y or left + width > x + w or top + height > y + h:
            return None
        try:
            return ImageGrab.grab(
                bbox=(left, top, left + width, top + height), all_screens=True
            ).convert("RGB")
        except (OSError, ValueError):
            return None

    def capture_fullscreen(self) -> Optional[Image.Image]:
        try:
            return ImageGrab.grab(all_screens=True).convert("RGB")
        except (OSError, ValueError):
            return None


screen_capture = ScreenCapture()


def screenshot(region=None):
    return (screen_capture.capture_fullscreen() if region is None
            else screen_capture.capture_region(region))
