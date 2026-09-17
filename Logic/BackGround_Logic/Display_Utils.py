"""Physical desktop coordinates shared by capture and window detection."""
import ctypes


def enable_dpi_awareness():
    """Set DPI awareness before GUI/capture imports; tolerate an existing setting."""
    try:
        user32 = ctypes.windll.user32
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = ctypes.c_bool
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def hotbar_region(client_region):
    """Bottom-center hotbar search, relative to the current client area.

    Search the central 60% and bottom 15%, allowing fixed-size and scaled HUDs.
    Coordinates are physical screen pixels and may be negative on other monitors.
    """
    left, top, width, height = client_region
    if width <= 0 or height <= 0:
        raise ValueError("Roblox client area is empty")
    x1, x2 = int(width * 0.2), max(1, int(width * 0.8))
    y1 = int(height * 0.85)
    return left + x1, top + y1, x2 - x1, height - y1
