import cv2
import numpy as np
import sys
import time
import random
import math
import win32gui
from pathlib import Path
import importlib.util

# Import from centralized Import_Utils
try:
    from .Import_Utils import (  # type: ignore
        virtual_mouse, VIRTUAL_MOUSE_AVAILABLE, is_virtual_mouse_available,
        screenshot, SCREEN_CAPTURE_AVAILABLE
    )
except ImportError:
    try:
        from Import_Utils import (  # type: ignore
            virtual_mouse, VIRTUAL_MOUSE_AVAILABLE, is_virtual_mouse_available,
            screenshot, SCREEN_CAPTURE_AVAILABLE
        )
    except ImportError:
        # Final fallback if Import_Utils not available
        virtual_mouse = None  # type: ignore
        VIRTUAL_MOUSE_AVAILABLE = False
        def is_virtual_mouse_available():  # type: ignore
            return False
        screenshot = None  # type: ignore
        SCREEN_CAPTURE_AVAILABLE = False


# Cache for detector module to prevent reloading
_detector_module_cache = None

def get_detector_module():
    """Lazily load the FishingRodDetector module.

    Returns the loaded module. Raises RuntimeError if the detector cannot be found
    or loaded. This avoids printing or exiting during import-time of this module.
    """
    global _detector_module_cache
    if _detector_module_cache is not None:
        return _detector_module_cache
        
    detector_path = Path(__file__).resolve()  # This module itself
    
    spec = importlib.util.spec_from_file_location('frod', str(detector_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to create import spec for: {detector_path}")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise RuntimeError(f"failed to load detector module: {e}")

    _detector_module_cache = module
    return module


def screen_region_image():
    """Capture a screenshot of the fishing rod detection region."""
    left = max(0, TOP_LEFT[0])
    top = max(0, TOP_LEFT[1])
    right = max(left + 1, BOTTOM_RIGHT[0])
    bottom = max(top + 1, BOTTOM_RIGHT[1])
    w = right - left
    h = bottom - top
    # Use Windows API screen capture instead of PyAutoGUI
    try:
        from .Screen_Capture import screenshot
        pil_img = screenshot(region=(left, top, w, h))
        if pil_img is None:
            raise Exception("Screen capture failed")
    except:
        # Final fallback - try to use PIL directly
        try:
            from PIL import ImageGrab
            pil_img = ImageGrab.grab(bbox=(left, top, left + w, top + h))
        except Exception as e:
            print(f"Screenshot capture failed: {e}")
            # Return dummy image to prevent crashes
            img = np.zeros((h, w, 3), dtype=np.uint8)
            gray = np.zeros((h, w), dtype=np.uint8)
            return img, gray, left, top
    
    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img, gray, left, top


def smooth_move_to(target_x, target_y, duration=None):
    """
    Smoothly move mouse to target position with human-like curves and acceleration.
    """
    # Get current mouse position using Windows API
    try:
        import ctypes
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        point = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
        start_x, start_y = point.x, point.y
    except Exception:
        start_x, start_y = 0, 0  # fallback
    
    # Calculate distance and auto-adjust duration if not specified
    distance = math.sqrt((target_x - start_x) ** 2 + (target_y - start_y) ** 2)
    if duration is None:
        # Much faster movement - humans are quick with mouse
        duration = min(0.05 + distance * 0.0005, 0.3)  # 0.05s to 0.3s max (much faster!)
    
    # Less variation to keep it snappy
    duration = duration * random.uniform(0.9, 1.1)
    
    # Fewer steps for faster movement
    steps = max(5, int(duration * 60))  # Fewer steps, faster movement
    
    # Smaller curves for more direct movement
    control_factor = random.uniform(0.05, 0.15)  # Less curve
    mid_x = (start_x + target_x) / 2 + random.randint(-10, 10) * control_factor
    mid_y = (start_y + target_y) / 2 + random.randint(-10, 10) * control_factor
    
    for i in range(steps + 1):
        progress = i / steps
        
        # Smooth acceleration/deceleration curve (ease-in-out)
        smooth_progress = 0.5 - 0.5 * math.cos(progress * math.pi)
        
        # Quadratic bezier curve for natural movement
        t = smooth_progress
        x = (1-t)**2 * start_x + 2*(1-t)*t * mid_x + t**2 * target_x
        y = (1-t)**2 * start_y + 2*(1-t)*t * mid_y + t**2 * target_y
        
        # Much smaller jitter for faster, more precise movement
        jitter_x = random.uniform(-0.2, 0.2)
        jitter_y = random.uniform(-0.2, 0.2)
        
        final_x = int(x + jitter_x)
        final_y = int(y + jitter_y)
        
        # Use Windows API for mouse movement
        try:
            import ctypes
            ctypes.windll.user32.SetCursorPos(final_x, final_y)
        except Exception:
            pass  # Ignore movement errors
        
        # Much faster step timing
        step_delay = duration / steps
        # Less variation for smoother, faster movement
        step_delay *= random.uniform(0.8, 1.2)
        time.sleep(step_delay)

# Config
# Templates live in the Images/ folder relative to the project root
IMAGES_DIR = Path(__file__).parent.parent.parent / 'Images'
UN_PATH = IMAGES_DIR / 'Basic_Fishing_UN.png'
EQ_PATH = IMAGES_DIR / 'Basic_Fishing_EQ.png'
# Region to check: top-left and bottom-right (inclusive)
TOP_LEFT = (725, 1004)
BOTTOM_RIGHT = (1189, 1072)
threshold = 0.50   # matching threshold (0-1). Increased from 35% to 50% for better accuracy
debug = True       # set True to print info and save debug image


def load_templates():
    # Use absolute paths so imports from other folders find them reliably
    un_color = cv2.imread(str(UN_PATH))
    eq_color = cv2.imread(str(EQ_PATH))
    
    # Check if images loaded successfully (handle both None and empty arrays)
    un_valid = un_color is not None and un_color.size > 0
    eq_valid = eq_color is not None and eq_color.size > 0
    
    if not un_valid or not eq_valid:
        print(f"Error: Could not load template images. Looking for:\n  {UN_PATH}\n  {EQ_PATH}")
        sys.exit(1)
    return cv2.cvtColor(un_color, cv2.COLOR_BGR2GRAY), cv2.cvtColor(eq_color, cv2.COLOR_BGR2GRAY) # type: ignore


def multi_scale_match(screenshot_gray, template_gray, scales=None):
    if scales is None:
        scales = np.linspace(0.8, 1.2, 21)

    best_val = -1.0
    best_loc = None
    best_scale = None
    best_size = None

    sh, sw = screenshot_gray.shape[:2]
    th, tw = template_gray.shape[:2]

    # Precompute edges for screenshot
    try:
        screenshot_edges = cv2.Canny(screenshot_gray, 50, 150)
    except Exception:
        screenshot_edges = None

    template_edges_base = None
    try:
        template_edges_base = cv2.Canny(template_gray, 50, 150)
    except Exception:
        template_edges_base = None

    for scale in scales:
        new_w = max(1, int(tw * scale))
        new_h = max(1, int(th * scale))
        if new_h >= sh or new_w >= sw:
            continue

        templ_resized = cv2.resize(template_gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
        templ_edges = None
        if template_edges_base is not None:
            templ_edges = cv2.resize(template_edges_base, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Intensity match
        try:
            res = cv2.matchTemplate(screenshot_gray, templ_resized, cv2.TM_CCOEFF_NORMED)
            _, max_val_i, _, max_loc_i = cv2.minMaxLoc(res)
        except Exception:
            max_val_i = -1.0
            max_loc_i = None

        # Edge match
        if screenshot_edges is not None and templ_edges is not None:
            try:
                res_e = cv2.matchTemplate(screenshot_edges, templ_edges, cv2.TM_CCOEFF_NORMED)
                _, max_val_e, _, max_loc_e = cv2.minMaxLoc(res_e)
            except Exception:
                max_val_e = -1.0
                max_loc_e = None
        else:
            max_val_e = -1.0
            max_loc_e = None

        combined = 0.75 * float(max_val_i) + 0.25 * float(max_val_e)

        if combined > best_val:
            best_val = float(combined)  # Ensure it's a scalar
            best_loc = max_loc_i if max_loc_i is not None else max_loc_e
            best_scale = scale
            best_size = (new_w, new_h)

    # Return scalar values
    return float(best_val), best_loc, best_scale, best_size


def check_region_and_act():
    """
    Check the fishing rod region and take appropriate action.
    
    Returns:
        True: UN (unequipped) rod detected and clicked
        False: EQ (equipped) rod detected - ready to fish
        None: No clear detection
    """
    # Quick validation - check if Roblox window is available (but don't require foreground)
    try:
        foreground_hwnd = win32gui.GetForegroundWindow()
        foreground_title = win32gui.GetWindowText(foreground_hwnd).lower()
        
        # Only warn if Roblox not in foreground, but don't skip detection
        if 'roblox' not in foreground_title:
            # Check if Roblox window exists at all
            roblox_found = False
            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).lower()
                    
                    # Only accept actual Roblox application windows, not browser tabs
                    if 'roblox' in title and not any(browser in title for browser in ['opera', 'chrome', 'firefox', 'edge', 'safari', 'brave']):
                        # Additional check: try to verify it's the actual Roblox process
                        try:
                            import win32process
                            import psutil
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            process = psutil.Process(pid)
                            process_name = process.name().lower()
                            
                            if 'roblox' in process_name or 'robloxplayerbeta' in process_name:
                                windows.append((hwnd, title))
                        except (ImportError, Exception):
                            # Fallback: accept if title looks like Roblox app (not browser)
                            if 'browser' not in title:
                                windows.append((hwnd, title))
                return True
            
            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            
            if not windows:
                print("WARNING: No Roblox window found. Skipping rod detection.")
                return None
            # Continue with detection even if not in foreground
    except Exception as e:
        print(f"Error checking window state: {e}")
        # Continue anyway - don't let window check failure stop detection
    
    try:
        un_gray, eq_gray = load_templates()
    except Exception as e:
        print(f"Error loading templates: {e}")
        return None

    try:
        left = max(0, TOP_LEFT[0])
        top = max(0, TOP_LEFT[1])
        # Get screen dimensions using Windows API
        try:
            import ctypes
            user32 = ctypes.windll.user32
            screen_w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
            screen_h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
        except Exception:
            screen_w, screen_h = 1920, 1080  # Fallback
        right = min(screen_w, BOTTOM_RIGHT[0])
        bottom = min(screen_h, BOTTOM_RIGHT[1])
        w = max(1, right - left)
        h = max(1, bottom - top)
        region = (left, top, w, h)

        time.sleep(0.05)
        # Use Windows API screen capture
        try:
            from .Screen_Capture import screenshot
            pil_img = screenshot(region=region)
            if pil_img is None:
                raise Exception("Screen capture failed")
        except:
            # Final fallback - try to use PIL directly
            try:
                from PIL import ImageGrab
                pil_img = ImageGrab.grab(bbox=region)
            except Exception as e:
                print(f"Screenshot capture failed: {e}")
                return False, 0.0
        screenshot = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    except Exception as e:
        print(f"Error capturing screenshot: {e}")
        return None

    try:
        best_un_val, best_un_loc, best_un_scale, best_un_size = multi_scale_match(screenshot_gray, un_gray)
        best_eq_val, best_eq_loc, best_eq_scale, best_eq_size = multi_scale_match(screenshot_gray, eq_gray)
    except Exception as e:
        print(f"Error in template matching: {e}")
        return None

    if debug:
        print(f"Region ({left},{top})-({right},{bottom}) -> UN:{best_un_val:.3f} (scale={best_un_scale}) EQ:{best_eq_val:.3f} (scale={best_eq_scale})")
        dbg = screenshot.copy()
        if best_un_loc is not None and best_un_size is not None:
            bx, by = int(best_un_loc[0]), int(best_un_loc[1])
            bw, bh = int(best_un_size[0]), int(best_un_size[1])
            cv2.rectangle(dbg, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
            cv2.putText(dbg, f"UN {best_un_val:.2f}", (bx, max(5, by - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
        if best_eq_loc is not None and best_eq_size is not None:
            ex, ey = int(best_eq_loc[0]), int(best_eq_loc[1])
            ew, eh = int(best_eq_size[0]), int(best_eq_size[1])
            cv2.rectangle(dbg, (ex, ey), (ex + ew, ey + eh), (0, 0, 255), 2)
            cv2.putText(dbg, f"EQ {best_eq_val:.2f}", (ex, max(5, ey - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)
        
        # Save to debug directory
        debug_dir = Path(__file__).parent.parent.parent / 'debug'
        debug_dir.mkdir(exist_ok=True)
        dbg_path = debug_dir / 'rod_detection_region.png'
        cv2.imwrite(str(dbg_path), dbg)
        print(f'Saved debug image: {dbg_path}')

    # Decide - ensure all values are scalar
    best_un_val_scalar = float(best_un_val) if best_un_val is not None else -1.0
    best_eq_val_scalar = float(best_eq_val) if best_eq_val is not None else -1.0
    
    # Prioritize UN detection - if UN is above threshold, click it (even if EQ score is higher)
    # This is more aggressive but necessary for reliable rod equipping
    if (best_un_loc is not None and best_un_size is not None and 
        best_un_val_scalar >= threshold):
        tw, th = best_un_size
        click_x = left + int(best_un_loc[0]) + tw // 2
        click_y = top + int(best_un_loc[1]) + th // 2
        
        print(f'UN rod detected at ({click_x}, {click_y}) - score={best_un_val_scalar:.3f} (EQ score: {best_eq_val_scalar:.3f})')
        print(f'🎯 Prioritizing UN click to equip rod')
        
        # Use virtual mouse driver for undetectable input
        if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
            print("🛡️ Using STEALTH hardware-level mouse driver")
            
            # Human-like behavior with anti-detection patterns
            import random
            
            # Add larger random offset for more natural clicking (avoid patterns)
            offset_x = random.randint(-7, 7)
            offset_y = random.randint(-7, 7)
            final_click_x = click_x + offset_x
            final_click_y = click_y + offset_y
            
            print(f'🎯 [STEALTH] Target position ({final_click_x}, {final_click_y})')
            
            # Anti-detection: Randomized approach pattern
            approach_pattern = random.choice(['direct', 'curved', 'double_move'])
            
            if approach_pattern == 'direct':
                # Simple direct movement
                virtual_mouse.move_to(final_click_x, final_click_y)
                time.sleep(random.uniform(0.08, 0.15))
                
            elif approach_pattern == 'curved':
                # Curved approach to target (more human-like)
                mid_x = final_click_x + random.randint(-20, 20)
                mid_y = final_click_y + random.randint(-20, 20)
                virtual_mouse.move_to(mid_x, mid_y)
                time.sleep(random.uniform(0.05, 0.1))
                virtual_mouse.move_to(final_click_x, final_click_y)
                time.sleep(random.uniform(0.08, 0.15))
                
            elif approach_pattern == 'double_move':
                # Double movement with pause (avoids detection algorithms)
                pre_x = final_click_x + random.randint(-15, 15)
                pre_y = final_click_y + random.randint(-15, 15)
                virtual_mouse.move_to(pre_x, pre_y)
                time.sleep(random.uniform(0.1, 0.2))
                virtual_mouse.move_to(final_click_x, final_click_y)
                time.sleep(random.uniform(0.08, 0.15))
            
            # Variable click duration to avoid timing patterns
            click_duration = random.uniform(0.12, 0.22)
            
            # Perform ultra-stealth PostMessage click
            success = virtual_mouse.ultimate_stealth_click(final_click_x, final_click_y)
            if success:
                print(f'🛡️ [ULTRA-STEALTH] PostMessage rod click completed at ({final_click_x}, {final_click_y})')
            else:
                print(f'🛡️ [ULTRA-STEALTH] Fallback rod click completed at ({final_click_x}, {final_click_y})')
            
            # Randomized post-click delay (critical for avoiding detection)
            post_delay = random.uniform(0.4, 0.8)
            time.sleep(post_delay)
            
            return True
        
        # Fallback to ultra-stealth if virtual mouse initialization fails
        print("�️ [ULTRA-STEALTH] Using ultimate stealth click for rod clicking")
        import random
        offset_x = random.randint(-2, 2)
        offset_y = random.randint(-2, 2)
        final_x = click_x + offset_x
        final_y = click_y + offset_y
        
        print(f'🛡️ [ULTRA-STEALTH] Moving to rod at ({final_x}, {final_y}) with PostMessage')
        
        # Import Virtual_Mouse for fallback
        try:
            from . import Virtual_Mouse
            fallback_mouse = Virtual_Mouse.VirtualMouse()
            success = fallback_mouse.ultimate_stealth_click(final_x, final_y)
            if success:
                print(f'�️ [ULTRA-STEALTH] PostMessage fallback rod click completed at ({final_x}, {final_y})')
            else:
                print(f'🛡️ [ULTRA-STEALTH] Enhanced fallback rod click completed at ({final_x}, {final_y})')
            
            # Wait longer for game to register the click and update UI
            time.sleep(random.uniform(0.4, 0.6))
            return True
        except Exception as e:
            print(f'❌ Ultimate stealth fallback failed: {e}')
            return False

    # Only check for EQ if UN was not detected above threshold
    if (best_eq_loc is not None and best_eq_size is not None and 
        best_eq_val_scalar >= threshold and best_un_val_scalar < threshold):
        print(f'EQ detected in region - rod is equipped (score={best_eq_val_scalar:.3f})')
        return False

    # Enhanced debug information for failed detections
    print(f'No UN or EQ detected in the region')
    print(f'UN score: {best_un_val_scalar:.3f} (threshold: {threshold})')
    print(f'EQ score: {best_eq_val_scalar:.3f} (threshold: {threshold})')
    if best_un_val_scalar >= 0.25 or best_eq_val_scalar >= 0.25:
        print(f'⚠️  Close matches found but below threshold - consider lowering threshold')
        if best_un_val_scalar >= 0.30:
            print(f'⚠️  UN score {best_un_val_scalar:.3f} is close to threshold - rod might be unequipped')
    if max(best_un_val_scalar, best_eq_val_scalar) < 0.2:
        print(f'⚠️  Very low scores - check if detection region is correct')
    return None


# Load templates that are expected by Fishing_Script.py
def safe_load_template(path):
    """Safely load a template image, handling both None and empty array cases."""
    try:
        # Load as color image to match screenshot format
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is not None and img.size > 0:
            # Only print on first load - this should only happen once
            return img
        else:
            print(f"❌ Template failed to load: {path.name}")
    except Exception as e:
        print(f"❌ Template loading error: {path.name} - {e}")
    return None

try:
    FISH_LEFT_TPL = safe_load_template(IMAGES_DIR / 'Fish_Left.png')
    FISH_RIGHT_TPL = safe_load_template(IMAGES_DIR / 'Fish_Right.png')
    SHIFT_LOCK_TPL = safe_load_template(IMAGES_DIR / 'Shift_Lock.png')
    POWER_MAX_TPL = safe_load_template(IMAGES_DIR / 'Power_Max.png')
    POWER_ACTIVE_TPL = safe_load_template(IMAGES_DIR / 'Power_Active.png')
except Exception as e:
    print(f"Warning: Could not load some template images: {e}")
    FISH_LEFT_TPL = None
    FISH_RIGHT_TPL = None
    SHIFT_LOCK_TPL = None
    POWER_MAX_TPL = None
    POWER_ACTIVE_TPL = None


if __name__ == '__main__':
    res = check_region_and_act()
    if res is False:
        sys.exit(0)
