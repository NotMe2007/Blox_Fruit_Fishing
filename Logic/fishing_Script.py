import time
import sys
import cv2
import numpy as np
import pyautogui
import random
import math
import win32gui
import win32con
from pathlib import Path
import importlib.util

# Import virtual mouse driver
virtual_mouse = None
VIRTUAL_MOUSE_AVAILABLE = False

try:
    from VirtualMouse import virtual_mouse
    VIRTUAL_MOUSE_AVAILABLE = True
    print("✓ Virtual mouse driver loaded for fishing script!")
except ImportError as e:
    print(f"Warning: Virtual mouse not available in fishing script: {e}")
    virtual_mouse = None
    VIRTUAL_MOUSE_AVAILABLE = False

# Import window manager for proper Roblox window handling
try:
    from Logic.BackGroud_Logic.WindowManager import roblox_window_manager, get_roblox_coordinates, get_roblox_window_region, ensure_roblox_focused # type: ignore
    WINDOW_MANAGER_AVAILABLE = True
    print("✓ Window manager loaded for proper Roblox window detection!")
except ImportError as e:
    print(f"Warning: Window manager not available: {e}")
    WINDOW_MANAGER_AVAILABLE = False
    # Define dummy functions for fallback
    def get_roblox_coordinates():
        return None, None
    def get_roblox_window_region():
        return None
    def ensure_roblox_focused():
        return False

pyautogui.FAILSAFE = True


def smooth_move_to(target_x, target_y, duration=None):
    """
    Smoothly move mouse to target position with human-like curves and acceleration.
    """
    start_x, start_y = pyautogui.position()
    
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
        
        pyautogui.moveTo(final_x, final_y)
        
        # Much faster step timing
        step_delay = duration / steps
        # Less variation for smoother, faster movement
        step_delay *= random.uniform(0.8, 1.2)
        time.sleep(step_delay)


def find_roblox_window():
    """Find the Roblox window handle and title."""
    roblox_windows = []
    
    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            window_title = win32gui.GetWindowText(hwnd).lower()
            if 'roblox' in window_title:
                results.append((hwnd, win32gui.GetWindowText(hwnd)))
        return True
    
    win32gui.EnumWindows(enum_callback, roblox_windows)
    return roblox_windows


def bring_roblox_to_front():
    """Find and bring Roblox window to the foreground using multiple methods."""
    # Use window manager if available
    if WINDOW_MANAGER_AVAILABLE:
        return ensure_roblox_focused()
    
    # Fallback to original method
    roblox_windows = find_roblox_window()
    
    if not roblox_windows:
        print("ERROR: No Roblox window found!")
        return False
    
    # Use the first Roblox window found
    hwnd, title = roblox_windows[0]
    
    try:
        # Method 1: Try standard Windows API
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.2)
        
        # Try multiple methods to bring window to front
        success = False
        
        try:
            win32gui.SetForegroundWindow(hwnd)
            success = True
        except Exception as e:
            print(f"SetForegroundWindow failed: {e}")
        
        if not success:
            try:
                # Alternative method: Use ShowWindow
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.BringWindowToTop(hwnd)
                success = True
            except Exception as e:
                print(f"Alternative window method failed: {e}")
        
        if not success and VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
            try:
                # Method 3: Click on the window to bring it to front
                print("Using virtual mouse to click Roblox window...")
                rect = win32gui.GetWindowRect(hwnd)
                center_x = (rect[0] + rect[2]) // 2
                center_y = (rect[1] + rect[3]) // 2
                
                # Click on window center to focus it
                virtual_mouse.human_click(center_x, center_y)
                time.sleep(0.5)
                success = True
                print("Virtual mouse window focus completed")
            except Exception as e:
                print(f"Virtual mouse window focus failed: {e}")
        
        if success:
            print(f"Successfully focused Roblox window: {title}")
            time.sleep(0.5)  # Give window time to come to front
            return True
        else:
            print("All window focus methods failed")
            return False
    
    except Exception as e:
        print(f"Error in bring_roblox_to_front: {e}")
        return False


def validate_roblox_and_game():
    """Check if Roblox is running, in foreground, and playing Blox Fruits."""
    try:
        # Import the Roblox checker
        sys.path.insert(0, str(Path(__file__).parent))
        from Logic.BackGroud_Logic.IsRoblox_Open import RobloxChecker
        
        checker = RobloxChecker()
        
        # Check if Roblox is running and in Blox Fruits
        if not checker.is_roblox_running():
            print("ERROR: Roblox is not running!")
            return False
        
        game_result = checker.detect_game_via_api()
        if isinstance(game_result, tuple):
            is_blox, game_name, _ = game_result
            if not is_blox:
                print("ERROR: Not playing Blox Fruits!")
                print(f"Current game: {game_name if game_name else 'Unknown'}")
                return False
        else:
            print("ERROR: Could not detect current game!")
            return False
        
        # Check if Roblox window is in foreground
        foreground_hwnd = win32gui.GetForegroundWindow()
        foreground_title = win32gui.GetWindowText(foreground_hwnd).lower()
        
        if 'roblox' not in foreground_title:
            print("ERROR: Roblox window is not in foreground!")
            print(f"Current foreground: {win32gui.GetWindowText(foreground_hwnd)}")
            return False
        
        print("✓ Roblox is running Blox Fruits and in foreground")
        return True
        
    except Exception as e:
        print(f"Error validating Roblox: {e}")
        return False


def get_detector_module():
    """Lazily load the FishingRodDetector module.

    Returns the loaded module. Raises RuntimeError if the detector cannot be found
    or loaded. This avoids printing or exiting during import-time of this module.
    """
    detector_path = Path(__file__).resolve().parent / 'BackGroud_Logic' / 'FishingRodDetector.py'
    if not detector_path.exists():
        # Try alternative locations
        alt = Path(__file__).resolve().parents[1] / 'Images' / 'FishingRodDetector.py'
        if alt.exists():
            detector_path = alt
        else:
            alt2 = Path(__file__).resolve().parents[1] / 'FishingRodDetector.py'
            if alt2.exists():
                detector_path = alt2
            else:
                raise RuntimeError(f"detector file not found. Tried: {detector_path}, {alt}, and {alt2}")

    spec = importlib.util.spec_from_file_location('frod', str(detector_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to create import spec for: {detector_path}")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise RuntimeError(f"failed to load detector module: {e}")

    return module


def screen_region_image():
    frod = get_detector_module()
    left = max(0, frod.TOP_LEFT[0])
    top = max(0, frod.TOP_LEFT[1])
    right = max(left + 1, frod.BOTTOM_RIGHT[0])
    bottom = max(top + 1, frod.BOTTOM_RIGHT[1])
    w = right - left
    h = bottom - top
    pil = pyautogui.screenshot(region=(left, top, w, h))
    img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img, gray, left, top


def CastFishingRod(x, y, hold_seconds=1.5):
    # Validate Roblox before casting
    if not validate_roblox_and_game():
        print("Cannot cast - Roblox validation failed!")
        return False
    
    # Ensure Roblox window is focused and get proper coordinates
    if WINDOW_MANAGER_AVAILABLE:
        if not ensure_roblox_focused():
            print("Failed to focus Roblox window!")
            return False
        
        # Get proper Roblox window coordinates
        target_x, target_y = get_roblox_coordinates()
        if target_x is None or target_y is None:
            print("Failed to get Roblox window coordinates!")
            return False
        
        print(f"Casting in Roblox window at ({target_x}, {target_y}) holding for {hold_seconds} seconds...")
    else:
        # Fallback to screen center if window manager not available
        screen_w, screen_h = pyautogui.size()
        center_x = screen_w // 2
        center_y = screen_h // 2
        target_x = center_x
        target_y = center_y - 20
        print(f"Casting at screen center ({target_x}, {target_y}) holding for {hold_seconds} seconds...")
    
    # Human-like hold duration with slight variation
    actual_hold = hold_seconds + random.uniform(-0.1, 0.1)
    
    # Use virtual mouse for casting if available
    if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
        print(f"Virtual mouse casting at ({target_x}, {target_y}) for {actual_hold:.2f}s")
        
        # Move to casting position with virtual mouse
        virtual_mouse.smooth_move_to(target_x, target_y)
        time.sleep(random.uniform(0.08, 0.15))
        
        # Perform virtual drag for casting (more realistic than click-hold)
        end_x = target_x + random.randint(-5, 5)  # Slight cast variation
        end_y = target_y + random.randint(-5, 5)
        virtual_mouse.drag(target_x, target_y, end_x, end_y, actual_hold)
        
        print("Virtual mouse casting completed!")
        
    else:
        # Fallback to pyautogui
        print("Using fallback pyautogui for casting")
        offset_x = random.randint(-3, 3)
        offset_y = random.randint(-3, 3)
        final_x = target_x + offset_x
        final_y = target_y + offset_y
        
        smooth_move_to(final_x, final_y)
        time.sleep(random.uniform(0.08, 0.15))
        
        print(f"Fallback casting at ({final_x}, {final_y}) for {actual_hold:.2f}s")
        
        pyautogui.mouseDown(final_x, final_y, button='left')
        time.sleep(actual_hold)
        pyautogui.mouseUp(final_x, final_y, button='left')
        
        print("Fallback casting completed!")
    
    # Random delay after cast
    time.sleep(random.uniform(0.1, 0.2))
    return True

def Zoom_In(x, y, duration=0.011):
    # Simulate pressing 'i' 45 times to zoom in. Presses occur every `duration` seconds.
    # x,y are kept for API compatibility but aren't used for key presses.
    for _ in range(45):
        pyautogui.press('i')
        time.sleep(duration)

def Zoom_Out(x, y, duration=0.011):
    # Simulate pressing '0' four times to zoom out. Presses occur every `duration` seconds.
    # x,y are kept for API compatibility but aren't used for key presses.
    for _ in range(4):
        pyautogui.press('0')
        time.sleep(duration)

def Fish_On_Hook(x, y, duration=0.011):
    """Detect the fish-on-hook indicator and click the current mouse position.

    Detects whether the fish indicator corresponds to a left- or right-moving
    fish by matching against `Fish_Left.png` and `Fish_Right.png`.

    Returns the direction string 'left' or 'right' when a click was performed,
    or None when nothing was detected. (Previous callers expecting a boolean
    should treat non-None as True.)
    """
    # Validate Roblox before checking for fish
    if not validate_roblox_and_game():
        print("Cannot check for fish - Roblox validation failed!")
        return False
    
    # load detector templates lazily
    try:
        frod = get_detector_module()
    except RuntimeError:
        return False
    # prefer detector-provided generic template, fall back to module-level one
    generic_tpl = getattr(frod, 'FISH_ON_HOOK_TPL', None)
    if generic_tpl is None or (hasattr(generic_tpl, 'size') and generic_tpl.size == 0):
        generic_tpl = globals().get('FISH_ON_HOOK_TPL')
    
    if generic_tpl is None or (hasattr(generic_tpl, 'size') and generic_tpl.size == 0):
        return False

    # Get screen dimensions for fallback clicking
    screen_w, screen_h = pyautogui.size()
    
    # Use specific fish on hook detection region: (873, 351) to (1037, 470)
    fish_region_left = 873
    fish_region_top = 351  
    fish_region_right = 1037
    fish_region_bottom = 470
    fish_region_width = fish_region_right - fish_region_left
    fish_region_height = fish_region_bottom - fish_region_top
    
    # Create region tuple (left, top, width, height) for screenshot
    region = (fish_region_left, fish_region_top, fish_region_width, fish_region_height)
    print(f"Searching for fish in specific region: {region} (coordinates: {fish_region_left}, {fish_region_top} to {fish_region_right}, {fish_region_bottom})")
    
    found, score = _match_template_in_region(generic_tpl, region, threshold=0.84)
    if found:
        print(f"Fish on hook detected! Score: {score}")
        
        # Get click position - prefer Roblox window center, fallback to screen center
        if WINDOW_MANAGER_AVAILABLE:
            click_x, click_y = get_roblox_coordinates()
            if click_x is None or click_y is None:
                # Fallback to screen center
                click_x = screen_w // 2
                click_y = screen_h // 2
                print("Using screen center for minigame click")
            else:
                print(f"Using Roblox window center for minigame click: ({click_x}, {click_y})")
        else:
            # Use screen center as fallback
            click_x = screen_w // 2
            click_y = screen_h // 2
        
        # Use virtual mouse for minigame start if available
        if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
            print(f"Virtual mouse starting minigame at ({click_x}, {click_y})")
            
            # First click
            success1 = virtual_mouse.human_click(click_x, click_y)
            
            # Short delay between clicks
            time.sleep(random.uniform(0.05, 0.15))
            
            # Second click to ensure minigame starts
            success2 = virtual_mouse.human_click(click_x, click_y)
            
            if success1 and success2:
                print("Virtual mouse minigame clicks completed!")
            else:
                print("Some virtual mouse clicks failed, but continuing...")
                
        else:
            # Fallback to pyautogui
            print("Using fallback pyautogui for minigame clicks")
            offset_x = random.randint(-5, 5)
            offset_y = random.randint(-5, 5)
            final_x = click_x + offset_x
            final_y = click_y + offset_y
            
            smooth_move_to(final_x, final_y)
            
            # First click with human timing
            time.sleep(random.uniform(0.05, 0.12))
            click_duration1 = random.uniform(0.08, 0.15)
            
            pyautogui.mouseDown(final_x, final_y, button='left')
            time.sleep(click_duration1)
            pyautogui.mouseUp(final_x, final_y, button='left')
            
            # Short delay between clicks
            time.sleep(random.uniform(0.05, 0.15))
            
            # Second click to ensure minigame starts
            click_duration2 = random.uniform(0.08, 0.15)
            pyautogui.mouseDown(final_x, final_y, button='left')
            time.sleep(click_duration2)
            pyautogui.mouseUp(final_x, final_y, button='left')
            
            print(f"Fallback minigame clicks completed! Durations: {click_duration1:.3f}s, {click_duration2:.3f}s")
        
        # Random pause to avoid double-detecting
        time.sleep(random.uniform(0.2, 0.4))
        return True
    return False


def Shift_State(x, y, duration=0.011):
    """Simulate pressing 'shift' to change the fishing state. Presses occur every `duration` seconds.
    x,y are kept for API compatibility but aren't used for key presses.
    """
    # check a 200x200 region centered on screen (100px around center)
    screen_w, screen_h = pyautogui.size()
    cx = screen_w // 2
    cy = screen_h // 2
    region = (max(0, cx - 100), max(0, cy - 100), min(200, screen_w), min(200, screen_h))

    try:
        frod = get_detector_module()
    except RuntimeError:
        return False

    # require the Shift_Lock template to be present in Images/
    if not hasattr(frod, 'SHIFT_LOCK_TPL') or frod.SHIFT_LOCK_TPL is None:
        return False

    found, score = _match_template_in_region(frod.SHIFT_LOCK_TPL, region, threshold=0.82)
    if found:
        pyautogui.keyDown('shift')
        time.sleep(duration)
        pyautogui.keyUp('shift')
        return True
    return False




# --- power detection helpers -------------------------------------------------

IMAGES_DIR = Path(__file__).resolve().parents[1] / 'Images'
POWER_MAX_TPL = None
POWER_ACTIVE_TPL = None
def safe_load_template(path):
    """Safely load a template image, handling both None and empty array cases."""
    try:
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is not None and img.size > 0:
            return img
    except Exception:
        pass
    return None

try:
    POWER_MAX_TPL = safe_load_template(IMAGES_DIR / 'Power_Max.png')
    POWER_ACTIVE_TPL = safe_load_template(IMAGES_DIR / 'Power_Active.png')
    FISH_ON_HOOK_TPL = safe_load_template(IMAGES_DIR / 'Fish_On_Hook.png')
    FISH_LEFT_TPL = safe_load_template(IMAGES_DIR / 'Fish_Left.png')
    FISH_RIGHT_TPL = safe_load_template(IMAGES_DIR / 'Fish_Right.png')
    SHIFT_LOCK_TPL = safe_load_template(IMAGES_DIR / 'Shift_Lock.png')
except Exception:
    # set templates to None if loading fails
    POWER_MAX_TPL = None
    POWER_ACTIVE_TPL = None
    FISH_ON_HOOK_TPL = None
    FISH_LEFT_TPL = None
    FISH_RIGHT_TPL = None
    SHIFT_LOCK_TPL = None


def _match_template_in_region(template, region, threshold=0.80):
    """Take a screenshot of region (x,y,w,h), run grayscale template match and
    return (matched: bool, score: float).
    """
    # Enhanced template validation
    if template is None or (hasattr(template, 'size') and template.size == 0):
        return False, 0.0
    
    try:
        x, y, w, h = region
        pil = pyautogui.screenshot(region=(x, y, w, h))
        hay = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
        hay_gray = cv2.cvtColor(hay, cv2.COLOR_BGR2GRAY)
        
        # Ensure we have valid images for template matching
        if hay_gray.size == 0 or template.size == 0:
            return False, 0.0
        
        res = cv2.matchTemplate(hay_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        
        # Ensure max_val is a scalar value
        max_val = float(max_val)
        return (max_val >= threshold), max_val
        
    except Exception as e:
        print(f"Error in template matching: {e}")
        return False, 0.0


def _estimate_bar_fill(region, brightness_thresh=110):
    """Estimate fill fraction (0.0-1.0) of the bar under the icon inside region.
    Uses a heuristic: sample the lower 30% of the region and compute the fraction
    of bright pixels across a central horizontal slice.
    """
    try:
        x, y, w, h = region
        # sample the lower part of the region where the bar usually appears
        sample_y = y + int(h * 0.6)
        sample_h = max(3, int(h * 0.3))
        sample_x = x + int(w * 0.05)
        sample_w = max(10, int(w * 0.9))
        
        pil = pyautogui.screenshot(region=(sample_x, sample_y, sample_w, sample_h))
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Ensure we have a valid image
        if gray.size == 0 or sample_h < 3:
            return 0.0
        
        # take the central row (or average a few rows) to be robust
        row = gray[sample_h // 2 - 1: sample_h // 2 + 2, :]
        
        # Check if row has valid data
        if row.size == 0:
            return 0.0
        
        # use ndarray.mean to keep typing happy
        row_mean = row.mean(axis=0)
        
        # Ensure row_mean is not empty
        if row_mean.size == 0:
            return 0.0
        
        # Create boolean array and count True values (safer than direct comparison)
        brightness_mask = row_mean > brightness_thresh
        filled = int(np.count_nonzero(brightness_mask))
        total = int(row_mean.shape[0])
        
        return float(filled) / float(total) if total > 0 else 0.0
        
    except Exception as e:
        print(f"Error in _estimate_bar_fill: {e}")
        return 0.0


def _detect_fish_direction(region=None, threshold=0.84):
    """Return 'left' or 'right' if matching Fish_Left or Fish_Right templates in region.
    If region is None, search the full screen. Returns None when no match.
    """
    if region is None:
        screen_w, screen_h = pyautogui.size()
        region = (0, 0, screen_w, screen_h)

    # prefer detector-provided templates if available
    try:
        frod = get_detector_module()
        left_tpl = getattr(frod, 'FISH_LEFT_TPL', None)
        right_tpl = getattr(frod, 'FISH_RIGHT_TPL', None)
    except RuntimeError:
        left_tpl = None
        right_tpl = None

    # Safe template fallback for arrays
    if left_tpl is None or (hasattr(left_tpl, 'size') and left_tpl.size == 0):
        left_tpl = globals().get('FISH_LEFT_TPL')
    if right_tpl is None or (hasattr(right_tpl, 'size') and right_tpl.size == 0):
        right_tpl = globals().get('FISH_RIGHT_TPL')

    if left_tpl is None and right_tpl is None:
        return None

    left_found, left_score = _match_template_in_region(left_tpl, region, threshold=threshold) if left_tpl is not None else (False, 0.0)
    right_found, right_score = _match_template_in_region(right_tpl, region, threshold=threshold) if right_tpl is not None else (False, 0.0)

    # pick the higher score if both matched
    if left_found and right_found:
        return 'left' if left_score >= right_score else 'right'
    if left_found:
        return 'left'
    if right_found:
        return 'right'
    return None


def Fish_Left(x, y, duration=0.011):
    """Detect left-moving fish using Fish_Left template. Returns True when detected and clicks."""
    # search a reasonable region (full screen for now)
    direction = _detect_fish_direction(region=None, threshold=0.84)
    if direction == 'left':
        pyautogui.click()
        time.sleep(duration)
        return True
    return False


def Fish_Right(x, y, duration=0.011):
    """Detect right-moving fish using Fish_Right template. Returns True when detected and clicks."""
    direction = _detect_fish_direction(region=None, threshold=0.84)
    if direction == 'right':
        pyautogui.click()
        time.sleep(duration)
        return True
    return False


def Use_Ability_Fishing(x, y, duration=0.011):
    """Try to use the fishing ability only when the power is full.

    Detection logic:
    - Prefer template match against `Power_Max.png` (high threshold).
    - If template not detected, estimate the bar fill under the icon and
      consider full when fill >= 0.95.
    - If `Power_Active.png` (particles) is present, treat as active and avoid
      clicking until particles disappear.
    """
    region = (1564, 769, 348, 76)

    # check if an active particle state is present (use lower threshold)
    # load templates from Images/ lazily
    try:
        frod = get_detector_module()
    except RuntimeError:
        # cannot find templates; nothing to do
        return

    # Safe template fallback for arrays
    active_tpl = getattr(frod, 'POWER_ACTIVE_TPL', None)
    if active_tpl is None or (hasattr(active_tpl, 'size') and active_tpl.size == 0):
        active_tpl = POWER_ACTIVE_TPL
    
    power_max_tpl = getattr(frod, 'POWER_MAX_TPL', None)
    if power_max_tpl is None or (hasattr(power_max_tpl, 'size') and power_max_tpl.size == 0):
        power_max_tpl = POWER_MAX_TPL
    active_found, active_score = _match_template_in_region(active_tpl, region, threshold=0.6)
    if active_found:
        # power is currently being used; skip clicking
        return

    # check for exact full template
    full_found, full_score = _match_template_in_region(power_max_tpl, region, threshold=0.84)
    if full_found:
        # power is full: press the activation key (Z)
        pyautogui.press('z')
        time.sleep(0.05)
        return

    # fallback: sample the bar fill and click if essentially full
    fill = _estimate_bar_fill(region)
    if fill >= 0.95:
        # fallback: treat as full and press activation key
        pyautogui.press('z')
        time.sleep(0.05)

# --- power detection helpers and defined fishing ------------------------------------^^^^


def handle_fishing_minigame(minigame_controller):
    """
    Handle the fishing minigame by detecting the UI and making decisions.
    
    Returns True when minigame is complete, False to continue.
    """
    # This is a simplified minigame handler
    # In a full implementation, you would:
    # 1. Detect the minigame UI elements
    # 2. Read the indicator position and arrow direction
    # 3. Use the minigame_controller to decide actions
    # 4. Execute the recommended actions (key presses)
    
    # For now, simulate basic minigame interaction
    # This should be replaced with actual UI detection and control
    time.sleep(0.1)  # Brief pause for minigame processing
    return False  # Continue minigame (return True when complete)


def main_fishing_loop():
    """Main fishing automation loop."""
    print("Starting Blox Fruits Auto Fishing...")
    print("Press Ctrl+C to stop the script.")
    
    # Import the rod detector and minigame logic
    try:
        from BackGroud_Logic.FishingRodDetector import check_region_and_act
        from BackGroud_Logic.Fishing_MiniGame import MinigameController, MinigameConfig
    except ImportError as e:
        print(f"Failed to import required modules: {e}")
        return
    
    # Initialize minigame controller
    minigame_config = MinigameConfig()
    minigame_controller = MinigameController(minigame_config)
    
    # Fishing state variables
    fishing_state = "waiting"  # "waiting", "casting", "hooking", "minigame", "reeling"
    cast_attempts = 0
    max_cast_attempts = 3
    minigame_start_time = 0
    last_rod_click_time = 0  # Track when we last clicked the rod
    rod_click_cooldown = 3.0  # Wait 3 seconds before clicking rod again
    last_validation_time = 0  # Track when we last validated Roblox
    validation_interval = 5.0  # Only validate every 5 seconds to reduce spam
    
    try:
        while True:
            # Validate Roblox periodically (not every loop to reduce debug spam)
            current_time = time.time()
            if current_time - last_validation_time > validation_interval:
                if not validate_roblox_and_game():
                    print("Roblox validation failed. Bringing to front and retrying...")
                    if not bring_roblox_to_front():
                        print("Failed to bring Roblox to front. Waiting 5 seconds...")
                        time.sleep(5)
                        continue
                    # Wait a moment after bringing to front
                    time.sleep(1)
                    # Revalidate after bringing to front
                    if not validate_roblox_and_game():
                        print("Still unable to validate Roblox. Waiting 5 seconds...")
                        time.sleep(5)
                        continue
                last_validation_time = current_time
            
            # Check for fishing rod state (with cooldown to prevent spam clicking)
            current_time = time.time()
            if current_time - last_rod_click_time < rod_click_cooldown:
                # Still in cooldown period, skip rod detection
                time.sleep(0.1)
                rod_result = None
            else:
                rod_result = check_region_and_act()
            
            if rod_result is True:  # UN (unequipped) detected and clicked
                print("Fishing rod clicked to equip, waiting for it to equip...")
                fishing_state = "equipping"
                cast_attempts = 0
                last_rod_click_time = current_time  # Record click time
                time.sleep(2.0)  # Wait longer for rod to equip
                
                # After rod is equipped, perform zoom sequence and center mouse
                print("Performing post-equip setup: zoom in -> zoom out -> center mouse...")
                
                # Get screen/window center for zoom operations
                if WINDOW_MANAGER_AVAILABLE:
                    center_x, center_y = get_roblox_coordinates()
                    if center_x is None or center_y is None:
                        # Fallback to screen center
                        screen_w, screen_h = pyautogui.size()
                        center_x = screen_w // 2
                        center_y = screen_h // 2
                else:
                    screen_w, screen_h = pyautogui.size()
                    center_x = screen_w // 2
                    center_y = screen_h // 2
                
                # Zoom in sequence
                print("Zooming in...")
                Zoom_In(center_x, center_y)
                time.sleep(0.5)  # Brief pause between zoom operations
                
                # Zoom out sequence  
                print("Zooming out...")
                Zoom_Out(center_x, center_y)
                time.sleep(0.5)  # Brief pause after zoom out
                
                # Move mouse to center of Roblox window/screen
                print(f"Centering mouse at ({center_x}, {center_y})...")
                if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
                    virtual_mouse.smooth_move_to(center_x, center_y)
                else:
                    smooth_move_to(center_x, center_y)
                
                print("Post-equip setup completed! Ready to fish.")
                time.sleep(0.5)  # Brief pause before continuing
                
            elif rod_result is False:  # EQ (equipped) detected - rod is ready
                if fishing_state == "waiting" or fishing_state == "equipping":
                    fishing_state = "casting"
                    cast_attempts = 0
                    
            elif rod_result is None:  # No clear detection or error
                # Continue with current state but add small delay
                time.sleep(0.2)
                
            if fishing_state == "casting":
                print(f"Casting fishing rod (attempt {cast_attempts + 1}/{max_cast_attempts})...")
                
                # Zoom in for better accuracy
                screen_w, screen_h = pyautogui.size()
                Zoom_In(screen_w // 2, screen_h // 2)
                time.sleep(0.5)
                
                # Cast the rod
                CastFishingRod(screen_w // 2, screen_h // 2 - 20)
                time.sleep(2)  # Wait for cast to complete
                
                fishing_state = "hooking"
                cast_attempts += 1
                
            elif fishing_state == "hooking":
                print("Waiting for fish to bite...")
                
                # Check for fish on hook
                hook_result = Fish_On_Hook(0, 0)  # Coordinates not used in current implementation
                
                if hook_result:
                    print("Fish detected! Starting minigame...")
                    fishing_state = "minigame"
                    minigame_start_time = time.time()
                
                # Use fishing ability if available
                Use_Ability_Fishing(0, 0)
                
                # Check shift state
                Shift_State(0, 0)
                
                # Timeout after 30 seconds of waiting
                if cast_attempts >= max_cast_attempts:
                    print("Max cast attempts reached, resetting...")
                    fishing_state = "waiting"
                    cast_attempts = 0
                    # Zoom out
                    screen_w, screen_h = pyautogui.size()
                    Zoom_Out(screen_w // 2, screen_h // 2)
                
            elif fishing_state == "minigame":
                # Handle the fishing minigame
                minigame_result = handle_fishing_minigame(minigame_controller)
                
                if minigame_result or (time.time() - minigame_start_time) > 15:  # 15 second timeout
                    print("Fishing cycle complete, resetting...")
                    fishing_state = "waiting"
                    cast_attempts = 0
                    
                    # Zoom out after fishing
                    screen_w, screen_h = pyautogui.size()
                    Zoom_Out(screen_w // 2, screen_h // 2)
                    time.sleep(1)  # Brief pause before next cycle
                
            # Small delay between iterations
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopping auto fishing...")
    except Exception as e:
        import traceback
        print(f"Error in fishing loop: {e}")
        print("Full traceback:")
        traceback.print_exc()
    finally:
        # Zoom out when exiting
        try:
            screen_w, screen_h = pyautogui.size()
            Zoom_Out(screen_w // 2, screen_h // 2)
        except:
            pass
        print("Auto fishing stopped.")


if __name__ == "__main__":
    main_fishing_loop()
