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

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import virtual mouse driver
virtual_mouse = None
VIRTUAL_MOUSE_AVAILABLE = False

try:
    from BackGroud_Logic.VirtualMouse import VirtualMouse
    virtual_mouse = VirtualMouse()
    VIRTUAL_MOUSE_AVAILABLE = True
    print("✓ Virtual mouse driver loaded for fishing script!")
except ImportError as e:
    print(f"Warning: Virtual mouse not available in fishing script: {e}")
    virtual_mouse = None
    VIRTUAL_MOUSE_AVAILABLE = False

# Import window manager for proper Roblox window handling
try:
    from BackGroud_Logic.WindowManager import roblox_window_manager, get_roblox_coordinates, get_roblox_window_region, ensure_roblox_focused # type: ignore
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
    Move mouse to target position. Uses instant movement with virtual mouse (undetected),
    fallback to smooth movement with PyAutoGUI when virtual mouse unavailable.
    """
    # If virtual mouse is available, use instant movement (no delays needed - undetected)
    if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
        try:
            virtual_mouse.move_to(target_x, target_y)
            return
        except Exception as e:
            print(f"Virtual mouse move failed, falling back to PyAutoGUI: {e}")
    
    # Fallback: PyAutoGUI with minimal smooth movement for compatibility
    start_x, start_y = pyautogui.position()
    
    # Calculate distance and minimal duration for system responsiveness
    distance = math.sqrt((target_x - start_x) ** 2 + (target_y - start_y) ** 2)
    if duration is None:
        # Minimal duration for system to register movement
        duration = min(0.01 + distance * 0.0001, 0.05)  # 0.01s to 0.05s max (very fast!)
    
    # Minimal steps for fastest movement
    steps = max(2, int(duration * 30))  # Fewer steps, much faster
    
    for i in range(steps + 1):
        progress = i / steps
        
        # Linear interpolation (no curves needed)
        x = start_x + (target_x - start_x) * progress
        y = start_y + (target_y - start_y) * progress
        
        pyautogui.moveTo(int(x), int(y))
        
        # Minimal step timing for system responsiveness only
        step_delay = duration / steps
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
        from BackGroud_Logic.IsRoblox_Open import RobloxChecker
        
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


def CastFishingRod(x, y, hold_seconds=0.9):
    # Validate Roblox before casting
    if not validate_roblox_and_game():
        print("Cannot cast - Roblox validation failed!")
        return False
    
    # ALWAYS use Roblox window coordinates - no fallbacks to screen center
    if not WINDOW_MANAGER_AVAILABLE:
        print("ERROR: Window manager not available - cannot cast without Roblox window detection!")
        return False
        
    if not ensure_roblox_focused():
        print("Failed to focus Roblox window!")
        return False
    
    # Get proper Roblox window coordinates
    target_x, target_y = get_roblox_coordinates()
    if target_x is None or target_y is None:
        print("Failed to get Roblox window coordinates!")
        return False
    
    print(f"Casting in Roblox window at ({target_x}, {target_y}) holding for {hold_seconds} seconds...")
    
    # Human-like hold duration with slight variation
    actual_hold = hold_seconds + random.uniform(-0.1, 0.1)
    
    # Use virtual mouse for casting if available
    if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
        print(f"Virtual mouse casting at ({target_x}, {target_y}) for {actual_hold:.2f}s")
        
        # DEBUG: Check mouse position BEFORE moving
        current_x, current_y = virtual_mouse.get_cursor_pos()
        print(f"🔍 DEBUG: Mouse position BEFORE move: ({current_x}, {current_y})")
        
        # Move to casting position with virtual mouse (instant - no delays needed)
        virtual_mouse.smooth_move_to(target_x, target_y)
        
        # DEBUG: Check mouse position AFTER moving
        after_x, after_y = virtual_mouse.get_cursor_pos()
        print(f"🔍 DEBUG: Mouse position AFTER move: ({after_x}, {after_y})")
        print(f"🔍 DEBUG: Target was: ({target_x}, {target_y})")
        print(f"🔍 DEBUG: Difference: ({after_x - target_x:+d}, {after_y - target_y:+d})")
        
        # Check which monitor the mouse ended up on
        if after_x < 1920:
            print("⚠️  DEBUG: Mouse is on PRIMARY monitor (left screen)")
        else:
            print("✅ DEBUG: Mouse is on SECONDARY monitor (right screen) - where Roblox should be")
        
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
        
        print(f"Fallback casting at ({final_x}, {final_y}) for {actual_hold:.2f}s")
        
        pyautogui.mouseDown(final_x, final_y, button='left')
        time.sleep(actual_hold)
        pyautogui.mouseUp(final_x, final_y, button='left')
        
        print("Fallback casting completed!")
    
    return True

def Zoom_In(x, y, duration=0.05):
    # Simulate pressing 'i' 45 times to zoom in. Ensures Roblox focus first.
    # x,y are kept for API compatibility but aren't used for key presses.
    
    # Ensure Roblox window is focused for keyboard input
    if WINDOW_MANAGER_AVAILABLE:
        ensure_roblox_focused()
    
    for _ in range(45):
        pyautogui.press('i')
        time.sleep(duration)  # Delay for Roblox key registration

def Zoom_Out(x, y, duration=0.05):
    # Simulate pressing 'o' four times to zoom out. Ensures Roblox focus first.
    # x,y are kept for API compatibility but aren't used for key presses.
    
    # Ensure Roblox window is focused for keyboard input
    if WINDOW_MANAGER_AVAILABLE:
        ensure_roblox_focused()
    
    for _ in range(4):
        pyautogui.press('o')
        time.sleep(duration)  # Delay for Roblox key registration

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
        
        # Get click position - ONLY use Roblox window center
        if not WINDOW_MANAGER_AVAILABLE:
            print("ERROR: Window manager not available - cannot start minigame!")
            return False
            
        click_x, click_y = get_roblox_coordinates()
        if click_x is None or click_y is None:
            print("ERROR: Cannot get Roblox coordinates for minigame click!")
            return False
        
        print(f"Using Roblox center ({click_x}, {click_y}) for minigame click")
        
        # Use virtual mouse for minigame start if available
        if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
            print(f"Virtual mouse starting minigame at ({click_x}, {click_y})")
            
            # First click (instant - no delays needed with virtual mouse)
            success1 = virtual_mouse.human_click(click_x, click_y)
            
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
            
            # First click with minimal timing
            pyautogui.mouseDown(final_x, final_y, button='left')
            time.sleep(0.05)  # Minimal click duration
            pyautogui.mouseUp(final_x, final_y, button='left')
            
            # Short delay between clicks for system registration
            time.sleep(0.02)
            
            # Second click to ensure minigame starts
            pyautogui.mouseDown(final_x, final_y, button='left')
            time.sleep(0.05)  # Minimal click duration
            pyautogui.mouseUp(final_x, final_y, button='left')
            
            print("Fallback minigame clicks completed!")
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
    MINIGAME_BAR_TPL = safe_load_template(IMAGES_DIR / 'MiniGame_Bar.png')
except Exception:
    # set templates to None if loading fails
    POWER_MAX_TPL = None
    POWER_ACTIVE_TPL = None
    FISH_ON_HOOK_TPL = None
    FISH_LEFT_TPL = None
    FISH_RIGHT_TPL = None
    SHIFT_LOCK_TPL = None
    MINIGAME_BAR_TPL = None


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


def detect_minigame_elements():
    """
    Detect minigame UI elements using image-based detection in specific region.
    Minigame bar spawns at coordinates (489, 774) to (1413, 873).
    
    Returns dict with:
    - indicator_pos: float 0.0-1.0 (normalized position of white indicator)
    - fish_pos: float 0.0-1.0 (normalized position of fish)
    - minigame_active: bool (whether minigame UI is detected)
    """
    try:
        # Specific minigame bar coordinates (provided by user)
        minigame_left = 489
        minigame_top = 774
        minigame_right = 1413
        minigame_bottom = 873
        minigame_width = minigame_right - minigame_left
        minigame_height = minigame_bottom - minigame_top
        
        # Take screenshot of the specific minigame region only
        minigame_region = (minigame_left, minigame_top, minigame_width, minigame_height)
        screenshot = pyautogui.screenshot(region=minigame_region)
        screenshot_np = np.array(screenshot)
        
        # Convert to BGR for OpenCV
        screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
        
        print(f"🎯 Scanning minigame region: {minigame_region} ({minigame_width}x{minigame_height})")
        
        # Detect fish position using image-based detection in the cropped region
        fish_pos = detect_fish_position_image_based(screenshot_bgr)
        
        # Detect white indicator position using image-based detection
        indicator_pos = detect_white_indicator_image_based(screenshot_bgr)
        
        # Check if minigame is active using template matching for the bar itself
        minigame_active = detect_minigame_bar_presence(screenshot_bgr)
        
        # If elements detected but no bar, still consider active if we found elements
        if not minigame_active and (fish_pos is not None or indicator_pos is not None):
            minigame_active = True
        
        return {
            "minigame_active": minigame_active,
            "indicator_pos": indicator_pos if indicator_pos is not None else 0.5,
            "fish_pos": fish_pos if fish_pos is not None else 0.5
        }
        
    except Exception as e:
        print(f"Error detecting minigame elements: {e}")
        return {"minigame_active": False, "indicator_pos": 0.5, "fish_pos": 0.5}


def detect_fish_position_image_based(screenshot_bgr):
    """
    Optimized image-based fish detection using template matching and color analysis.
    Much faster than pixel scanning. Returns normalized position 0.0-1.0 or None if not found.
    """
    try:
        # First check if we have fish templates available
        fish_left_path = Path(__file__).parent.parent / "Images" / "Fish_Left.png"
        fish_right_path = Path(__file__).parent.parent / "Images" / "Fish_Right.png"
        
        # Try template matching first (fastest method)
        if fish_left_path.exists() and fish_right_path.exists():
            fish_left_template = cv2.imread(str(fish_left_path))
            fish_right_template = cv2.imread(str(fish_right_path))
            
            if fish_left_template is not None and fish_right_template is not None:
                # Convert to grayscale for faster matching
                gray_screenshot = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)
                gray_left = cv2.cvtColor(fish_left_template, cv2.COLOR_BGR2GRAY)
                gray_right = cv2.cvtColor(fish_right_template, cv2.COLOR_BGR2GRAY)
                
                # Template matching with normalized correlation
                result_left = cv2.matchTemplate(gray_screenshot, gray_left, cv2.TM_CCOEFF_NORMED)
                result_right = cv2.matchTemplate(gray_screenshot, gray_right, cv2.TM_CCOEFF_NORMED)
                
                # Find best matches
                _, max_val_left, _, max_loc_left = cv2.minMaxLoc(result_left)
                _, max_val_right, _, max_loc_right = cv2.minMaxLoc(result_right)
                
                # Use the better match if confidence is high enough
                confidence_threshold = 0.6  # Lower threshold for faster detection
                if max_val_left > max_val_right and max_val_left > confidence_threshold:
                    fish_x = max_loc_left[0] + gray_left.shape[1] // 2
                    fish_pos = fish_x / screenshot_bgr.shape[1]
                    return max(0.0, min(1.0, fish_pos))
                elif max_val_right > confidence_threshold:
                    fish_x = max_loc_right[0] + gray_right.shape[1] // 2
                    fish_pos = fish_x / screenshot_bgr.shape[1]
                    return max(0.0, min(1.0, fish_pos))
        
        # Fallback to optimized color detection if templates fail
        return detect_fish_position_color_fallback(screenshot_bgr)
        
    except Exception as e:
        print(f"Error in image-based fish detection: {e}")
        return None

def detect_fish_position_color_fallback(screenshot_bgr):
    """
    Fast color-based fish detection as fallback method.
    """
    try:
        # Use optimized color detection with smaller search area
        # Convert AHK hex color 0x5B4B43 to BGR (OpenCV uses BGR)
        fish_color_bgr = np.array([67, 75, 91])
        fish_tolerance = 8  # Slightly higher tolerance for speed
        
        # Create color range for fish detection  
        lower_fish = fish_color_bgr - fish_tolerance
        upper_fish = fish_color_bgr + fish_tolerance
        lower_fish = np.clip(lower_fish, 0, 255)
        upper_fish = np.clip(upper_fish, 0, 255)
        
        # Create mask and find contours
        mask = cv2.inRange(screenshot_bgr, lower_fish, upper_fish)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
            
        # Find largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Skip very small contours (noise)
        if cv2.contourArea(largest_contour) < 10:
            return None
            
        # Calculate center
        M = cv2.moments(largest_contour)
        if M['m00'] == 0:
            return None
            
        fish_x = int(M['m10'] / M['m00'])
        fish_pos = fish_x / screenshot_bgr.shape[1]
        return max(0.0, min(1.0, fish_pos))
        
    except Exception as e:
        print(f"Error in color fallback fish detection: {e}")
        return None


def detect_white_indicator_image_based(screenshot_bgr):
    """
    Optimized image-based white indicator detection.
    Uses morphological operations and contour filtering for fast, accurate detection.
    Returns normalized position 0.0-1.0 or None if not found.
    """
    try:
        # Convert to HSV for better white detection in varying lighting
        hsv = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2HSV)
        
        # Define optimized white detection range in HSV
        # More robust than RGB detection
        lower_white = np.array([0, 0, 200])    # Low saturation, high value
        upper_white = np.array([180, 30, 255])  # Any hue, low saturation, high value
        
        # Create mask for white regions
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # Apply morphological operations to clean up the mask (faster than large tolerance)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # Filter contours by size and aspect ratio (white indicator has specific characteristics)
        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 5:  # Skip tiny noise
                continue
                
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by aspect ratio (white indicator is typically wider than tall)
            aspect_ratio = w / max(h, 1)
            if 0.5 <= aspect_ratio <= 10.0:  # Reasonable aspect ratio range
                valid_contours.append((contour, area, x + w // 2))
        
        if not valid_contours:
            return None
            
        # Get the largest valid contour (most likely the indicator)
        best_contour = max(valid_contours, key=lambda x: x[1])
        indicator_x = best_contour[2]  # Center x coordinate
        
        # Normalize to 0.0-1.0 based on screenshot width
        indicator_pos = indicator_x / screenshot_bgr.shape[1]
        return max(0.0, min(1.0, indicator_pos))
        
    except Exception as e:
        print(f"Error in image-based white indicator detection: {e}")
        return None

def detect_minigame_bar_presence(screenshot_bgr):
    """
    Detect minigame bar presence using template matching with MiniGame_Bar.png.
    Fallback to edge detection if template is not available.
    Returns True if minigame bar is detected, False otherwise.
    """
    try:
        # Primary method: Template matching with MiniGame_Bar.png
        if MINIGAME_BAR_TPL is not None:
            # Convert screenshot to grayscale for template matching
            gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)
            
            # Perform template matching
            result = cv2.matchTemplate(gray, MINIGAME_BAR_TPL, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # Use a confidence threshold to determine if bar is present
            confidence_threshold = 0.7
            if max_val >= confidence_threshold:
                print(f"✓ Minigame bar detected using template matching (confidence: {max_val:.3f})")
                return True
            else:
                print(f"Minigame bar template match below threshold (confidence: {max_val:.3f})")
        else:
            print("Warning: MiniGame_Bar.png template not loaded, using fallback detection")
        
        # Fallback method: Edge detection and shape analysis
        gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Edge detection with optimized parameters
        edges = cv2.Canny(blurred, 50, 150)
        
        # Look for horizontal lines (characteristic of minigame bar)
        # Use HoughLinesP for faster line detection
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=100, maxLineGap=10)
        
        if lines is not None:
            # Count horizontal lines (minigame bar has distinct horizontal edges)
            horizontal_lines = 0
            for line in lines:
                x1, y1, x2, y2 = line[0]
                # Check if line is roughly horizontal
                angle = np.arctan2(abs(y2 - y1), abs(x2 - x1)) * 180 / np.pi
                if angle < 15:  # Within 15 degrees of horizontal
                    horizontal_lines += 1
                    
            # If we found multiple horizontal lines, likely a minigame bar
            if horizontal_lines >= 2:
                print(f"Minigame bar detected using fallback edge detection ({horizontal_lines} horizontal lines)")
                return True
        
        # Fallback: check for rectangular shapes (bar outline)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            # Approximate contour to polygon
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Check if it's roughly rectangular (4-6 vertices)
            if len(approx) >= 4 and len(approx) <= 6:
                area = cv2.contourArea(contour)
                if area > 1000:  # Large enough to be a minigame bar
                    print("Minigame bar detected using fallback contour analysis")
                    return True
        
        return False
        
    except Exception as e:
        print(f"Error detecting minigame bar presence: {e}")
        return False


def handle_fishing_minigame(minigame_controller):
    """
    Handle the fishing minigame by detecting the UI and making decisions.
    
    Returns True when minigame is complete, False to continue.
    """
    try:
        # Detect minigame elements
        elements = detect_minigame_elements()
        
        if not elements["minigame_active"]:
            print("Minigame UI not detected, ending minigame...")
            return True
            
        indicator_pos = elements["indicator_pos"]
        fish_pos = elements["fish_pos"]
        
        print(f"🎯 Minigame: Indicator at {indicator_pos:.3f}, Fish at {fish_pos:.3f}")
        
        # Update the minigame controller target to fish position
        # We need to modify the controller to use fish_pos instead of 0.5
        minigame_controller.cfg.fish_center = fish_pos
        
        # Get decision from controller
        decision = minigame_controller.decide(
            indicator=indicator_pos,
            arrow=None,  # We could detect arrow direction from UI later
            stable=True  # We could detect stability from UI changes later
        )
        
        action = decision["action"]
        intensity = decision["intensity"]
        
        print(f"🤖 Decision: {action} (intensity: {intensity:.3f}) - {decision['note']}")
        
        # Execute the AHK-style minigame action
        execute_minigame_action(decision)
        
        # Brief processing delay
        time.sleep(0.05)
        return False  # Continue minigame
        
    except Exception as e:
        print(f"Error in minigame handler: {e}")
        return True  # End minigame on error


def execute_minigame_action(decision):
    """
    Execute AHK-style minigame actions with sophisticated timing and control.
    Handles all 6 action types with proper duration, counter-strafe, and ankle break mechanics.
    """
    try:
        # Get click position (center of Roblox window)
        if not WINDOW_MANAGER_AVAILABLE:
            return
            
        click_x, click_y = get_roblox_coordinates()
        if click_x is None or click_y is None:
            return
            
        action_type = decision.get("action_type", 0)
        action = decision.get("action")
        duration_factor = decision.get("duration_factor", 0.05)
        counter_strafe = decision.get("counter_strafe", 0)
        
        print(f"🎮 Minigame Action {action_type}: {action} (duration: {duration_factor:.3f}s)")
        
        if action_type == 0:  # Stabilize - short click
            if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Left mouse down
                time.sleep(0.01)  # 10ms click
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Left mouse up
                time.sleep(0.01)
            else:
                pyautogui.mouseDown(click_x, click_y, button='left')
                time.sleep(0.01)
                pyautogui.mouseUp(click_x, click_y, button='left')
                time.sleep(0.01)
                
        elif action_type == 1:  # Stable left tracking
            if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Ensure mouse up first
                time.sleep(duration_factor)      # Wait duration
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Mouse down for counter-strafe
                time.sleep(counter_strafe)       # Counter-strafe duration
            else:
                pyautogui.mouseUp(click_x, click_y, button='left')
                time.sleep(duration_factor)
                pyautogui.mouseDown(click_x, click_y, button='left')
                time.sleep(counter_strafe)
                
        elif action_type == 2:  # Stable right tracking  
            if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Mouse down first
                time.sleep(duration_factor)      # Wait duration
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Mouse up for counter-strafe
                time.sleep(counter_strafe)       # Counter-strafe duration
            else:
                pyautogui.mouseDown(click_x, click_y, button='left')
                time.sleep(duration_factor)
                pyautogui.mouseUp(click_x, click_y, button='left')
                time.sleep(counter_strafe)
                
        elif action_type == 3:  # Max left boundary
            if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Force mouse up (move left)
                time.sleep(duration_factor)      # Side delay
            else:
                pyautogui.mouseUp(click_x, click_y, button='left')
                time.sleep(duration_factor)
                
        elif action_type == 4:  # Max right boundary
            if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Force mouse down (move right)
                time.sleep(duration_factor)      # Side delay
            else:
                pyautogui.mouseDown(click_x, click_y, button='left')
                time.sleep(duration_factor)
                
        elif action_type == 5:  # Unstable left (aggressive)
            if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Mouse up first
                time.sleep(duration_factor)      # Aggressive duration
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Mouse down for counter-strafe
                time.sleep(counter_strafe)       # Counter-strafe duration
            else:
                pyautogui.mouseUp(click_x, click_y, button='left')
                time.sleep(duration_factor)
                pyautogui.mouseDown(click_x, click_y, button='left') 
                time.sleep(counter_strafe)
                
        elif action_type == 6:  # Unstable right (aggressive)
            if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Mouse down first
                time.sleep(duration_factor)      # Aggressive duration
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Mouse up for counter-strafe
                time.sleep(counter_strafe)       # Counter-strafe duration
            else:
                pyautogui.mouseDown(click_x, click_y, button='left')
                time.sleep(duration_factor)
                pyautogui.mouseUp(click_x, click_y, button='left')
                time.sleep(counter_strafe)
                
    except Exception as e:
        print(f"Error executing minigame action: {e}")


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
    
    # Initialize minigame controller with AHK-style configuration
    minigame_config = MinigameConfig()
    
    # Set up AHK parameters for optimal performance
    minigame_config.control = 0.2  # Typical rod Control stat (adjust based on actual rod)
    
    # Calculate pixel scaling based on screen resolution (AHK-style)
    if WINDOW_MANAGER_AVAILABLE:
        roblox_region = get_roblox_window_region()
        if roblox_region:
            # Calculate fish bar dimensions from Roblox window
            window_width = roblox_region[2]
            window_height = roblox_region[3] 
            
            # AHK calculation: FishBarLeft = WindowWidth/3.3160, FishBarRight = WindowWidth/1.4317
            fish_bar_left = window_width / 3.3160
            fish_bar_right = window_width / 1.4317
            fish_bar_width = fish_bar_right - fish_bar_left
            
            # AHK pixel scaling: PixelScaling = 1034/(FishBarRight-FishBarLeft)
            minigame_config.pixel_scaling = 1034 / fish_bar_width
            
            # Set boundaries based on window dimensions
            minigame_config.max_left_bar = 0.15   # 15% from left edge
            minigame_config.max_right_bar = 0.85  # 85% from left edge (15% from right)
            
            print(f"🔧 AHK Config: Fish bar width={fish_bar_width:.1f}px, Pixel scaling={minigame_config.pixel_scaling:.3f}")
        else:
            print("Warning: Could not get Roblox window for pixel scaling calculation")
    else:
        print("Warning: Window manager not available for AHK configuration")
    
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
    cast_start_time = 0  # Track when we started waiting for fish
    fishing_timeout = 30.0  # 30 seconds timeout for fish to bite
    
    try:
        while True:
            # Validate Roblox periodically (not every loop to reduce debug spam)
            current_time = time.time()
            if current_time - last_validation_time > validation_interval:
                if not validate_roblox_and_game():
                    print("Roblox validation failed. Bringing to front and retrying...")
                    if not bring_roblox_to_front():
                        print("Failed to bring Roblox to front. Waiting 2 seconds...")
                        time.sleep(2)
                        continue
                    # Wait a moment after bringing to front
                    time.sleep(0.5)
                    # Revalidate after bringing to front
                    if not validate_roblox_and_game():
                        print("Still unable to validate Roblox. Waiting 2 seconds...")
                        time.sleep(2)
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
                
                # Wait for rod to equip with periodic checks
                print("Waiting for fishing rod to equip (checking every 0.5s)...")
                for wait_check in range(8):  # Check up to 4 seconds
                    time.sleep(0.5)
                    # Quick check if rod is now equipped
                    temp_result = check_region_and_act()
                    if temp_result is False:  # EQ detected
                        print(f"✓ Rod equipped successfully after {(wait_check + 1) * 0.5:.1f}s")
                        break
                    elif temp_result is None:
                        print(f"Checking rod status... ({wait_check + 1}/8)")
                else:
                    print("Rod may still be equipping, continuing with setup...")
                
                # After rod is equipped, perform zoom sequence and center mouse
                print("Performing post-equip setup: zoom in -> zoom out -> center mouse...")
                
                # Get Roblox window center for zoom operations - no fallbacks
                if not WINDOW_MANAGER_AVAILABLE:
                    print("ERROR: Window manager not available for post-equip setup!")
                    return False
                    
                center_x, center_y = get_roblox_coordinates()
                if center_x is None or center_y is None:
                    print("ERROR: Cannot get Roblox coordinates for zoom operations!")
                    return False
                
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
                print(f"✓ EQ rod detected! Current state: {fishing_state}")
                if fishing_state == "waiting" or fishing_state == "equipping":
                    print("→ Transitioning to casting state")
                    fishing_state = "casting"
                    cast_attempts = 0
                else:
                    print(f"→ Already in {fishing_state} state")
                    
            elif rod_result is None:  # No clear detection or error
                print(f"No clear rod detection (state: {fishing_state})")
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
                time.sleep(0.5)  # Minimal wait for cast to register
                
                fishing_state = "hooking"
                cast_start_time = time.time()  # Record when we start waiting for fish
                cast_attempts += 1
                print(f"Started waiting for fish at {cast_start_time:.1f} (30s timeout)")
                
            elif fishing_state == "hooking":
                # Check for 30-second timeout (Roblox thinks clicking too fast)
                current_time = time.time()
                time_waiting = current_time - cast_start_time
                time_remaining = fishing_timeout - time_waiting
                
                if time_waiting >= fishing_timeout:
                    print(f"⏰ TIMEOUT: No fish after {time_waiting:.1f}s - Roblox may think we're clicking too fast!")
                    print("🔄 Unequipping and re-equipping fishing rod to reset state...")
                    fishing_state = "waiting"  # This will trigger rod detection and re-equipping
                    cast_attempts = 0
                    time.sleep(0.2)  # Brief pause before restarting
                    continue
                
                # Show countdown every 5 seconds
                if int(time_waiting) % 5 == 0 and int(time_waiting) > 0:
                    print(f"🎣 Waiting for fish to bite... ({time_remaining:.0f}s remaining)")
                else:
                    print("🎣 Waiting for fish to bite...")
                
                # Check for fish on hook
                hook_result = Fish_On_Hook(0, 0)  # Coordinates not used in current implementation
                
                if hook_result:
                    print("🐟 Fish detected! Starting minigame...")
                    fishing_state = "minigame"
                    minigame_start_time = time.time()
                
                # Use fishing ability if available
                Use_Ability_Fishing(0, 0)
                
                # Check shift state
                Shift_State(0, 0)
                
                # Fallback timeout after max cast attempts
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
                    time.sleep(0.2)  # Brief pause before next cycle
                
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
