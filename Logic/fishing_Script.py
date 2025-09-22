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
except ImportError as e:
    virtual_mouse = None
    VIRTUAL_MOUSE_AVAILABLE = False

# Import window manager for proper Roblox window handling
try:
    from BackGroud_Logic.WindowManager import roblox_window_manager, get_roblox_coordinates, get_roblox_window_region, ensure_roblox_focused # type: ignore
    WINDOW_MANAGER_AVAILABLE = True
except ImportError as e:
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
            pass
    
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
            pass
        
        if not success:
            try:
                # Alternative method: Use ShowWindow
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.BringWindowToTop(hwnd)
                success = True
            except Exception as e:
                pass
        
        if not success and VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
            try:
                # Method 3: Click on the window to bring it to front
                rect = win32gui.GetWindowRect(hwnd)
                center_x = (rect[0] + rect[2]) // 2
                center_y = (rect[1] + rect[3]) // 2
                
                # Click on window center to focus it
                virtual_mouse.human_click(center_x, center_y)
                time.sleep(0.5)
                success = True
            except Exception as e:
                pass
        
        if success:
            time.sleep(0.5)  # Give window time to come to front
            return True
        else:
            return False
    
    except Exception as e:
        return False


def validate_roblox_and_game():
    """Check if Roblox is running, in foreground, and playing Blox Fruits.
    Enhanced for Roblox update - more forgiving when API endpoints fail.
    """
    try:
        # Import the Roblox checker
        from BackGroud_Logic.IsRoblox_Open import RobloxChecker
        
        checker = RobloxChecker()
        
        # Check if Roblox is running
        if not checker.is_roblox_running():
            print("ERROR: Roblox is not running!")
            return False
        
        # Try API detection, but allow graceful fallback if APIs fail (Roblox update issue)
        try:
            game_result = checker.detect_game_via_api()
            if isinstance(game_result, tuple):
                is_blox, game_name, _ = game_result
                if is_blox:
                    print(f"✅ Confirmed Blox Fruits via API: {game_name}")
                    return True
                else:
                    print(f"⚠️ API says not Blox Fruits: {game_name}")
                    # Continue to fallback validation
            else:
                print("⚠️ API detection failed - using fallback validation")
        except Exception as api_error:
            print(f"⚠️ API detection error: {api_error} - using fallback validation")
        
        # Fallback validation: Just check if Roblox window exists and is focused
        # This is more lenient for when Roblox updates break API detection
        foreground_hwnd = win32gui.GetForegroundWindow()
        foreground_title = win32gui.GetWindowText(foreground_hwnd).lower()
        
        if 'roblox' in foreground_title:
            print("✅ Roblox window detected and focused - assuming Blox Fruits (API fallback)")
            return True
        else:
            print("❌ Roblox window not in foreground")
            return False
        
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False


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

    _detector_module_cache = module
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


def CastFishingRod(x, y, hold_seconds=0.93):
    # Validate Roblox before casting
    if not validate_roblox_and_game():
        return False
    
    # ALWAYS use Roblox window coordinates - no fallbacks to screen center
    if not WINDOW_MANAGER_AVAILABLE:
        return False
        
    if not ensure_roblox_focused():
        return False
    
    # Get proper Roblox window coordinates
    target_x, target_y = get_roblox_coordinates()
    if target_x is None or target_y is None:
        return False
    
    # Human-like hold duration with slight variation
    actual_hold = hold_seconds + random.uniform(-0.1, 0.1)
    
    # Use virtual mouse for casting if available
    if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
        # Move to casting position with virtual mouse (instant - no delays needed)
        virtual_mouse.smooth_move_to(target_x, target_y)
        
        # Perform virtual drag for casting (more realistic than click-hold)
        end_x = target_x + random.randint(-5, 5)  # Slight cast variation
        end_y = target_y + random.randint(-5, 5)
        virtual_mouse.drag(target_x, target_y, end_x, end_y, actual_hold)
        
    else:
        # Fallback to pyautogui
        offset_x = random.randint(-3, 3)
        offset_y = random.randint(-3, 3)
        final_x = target_x + offset_x
        final_y = target_y + offset_y
        
        smooth_move_to(final_x, final_y)
        
        pyautogui.mouseDown(final_x, final_y, button='left')
        time.sleep(actual_hold)
        pyautogui.mouseUp(final_x, final_y, button='left')
    
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

def _match_template_multi_scale(template, region, threshold=0.7):
    """
    Enhanced template matching with multiple scales for Roblox update compatibility.
    Tests different scales to handle UI size changes.
    """
    try:
        # Validate template before processing
        if template is None or template.size == 0:
            print("Error: Template is None or empty")
            return False, 0.0
        
        # Ensure template is in the correct format (BGR, 8-bit)
        if len(template.shape) == 3 and template.shape[2] == 3:
            # Template is already 3-channel BGR
            template_processed = template.astype(np.uint8)
        elif len(template.shape) == 3 and template.shape[2] == 4:
            # Template is 4-channel (BGRA), convert to BGR
            template_processed = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR).astype(np.uint8)
        elif len(template.shape) == 2:
            # Template is grayscale, convert to BGR
            template_processed = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR).astype(np.uint8)
        else:
            print(f"Error: Unexpected template shape: {template.shape}")
            return False, 0.0
        
        # Take screenshot of the region
        screenshot = pyautogui.screenshot(region=region)
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR).astype(np.uint8)
        
        # Template matching with multiple scales for robustness
        scales = [0.8, 0.9, 1.0, 1.1, 1.2]  # Try different scales
        best_score = 0
        
        for scale in scales:
            # Resize template
            height, width = template_processed.shape[:2]
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            if new_width < 10 or new_height < 10:  # Skip very small templates
                continue
            
            if new_width > screenshot_cv.shape[1] or new_height > screenshot_cv.shape[0]:
                # Skip templates larger than screenshot
                continue
                
            scaled_template = cv2.resize(template_processed, (new_width, new_height))
            
            # Ensure both images have the same data type
            if screenshot_cv.dtype != scaled_template.dtype:
                scaled_template = scaled_template.astype(screenshot_cv.dtype)
            
            # Perform template matching
            result = cv2.matchTemplate(screenshot_cv, scaled_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val > best_score:
                best_score = max_val
            
            if max_val >= threshold:
                print(f"🐟 FISH ON HOOK DETECTED! (confidence: {max_val:.3f}, scale: {scale})")
                return True, max_val
        
        # If we get here, no match at any scale
        if best_score > 0.5:  # Show near-misses for debugging
            print(f"🔍 Fish detection near-miss (best: {best_score:.3f}, threshold: {threshold})")
        
        return False, best_score
        
    except Exception as e:
        print(f"Error in multi-scale Fish_On_Hook detection: {e}")
        print(f"Template shape: {template.shape if template is not None else 'None'}")
        print(f"Template dtype: {template.dtype if template is not None else 'None'}")
        return False, 0.0

def _fish_on_hook_fallback():
    """
    Fallback detection method using alternative approaches.
    For use when template matching fails after Roblox updates.
    """
    try:
        # This is a placeholder for alternative detection methods
        # You might need to add specific color detection or OCR here
        # based on what the new Fish_On_Hook indicator looks like
        
        # For now, return False to prevent false positives
        # TODO: Implement color-based or OCR-based detection if needed
        return False
        
    except Exception as e:
        print(f"Error in fallback Fish_On_Hook detection: {e}")
        return False

def Fish_On_Hook(x, y, duration=0.011):
    """Detect the fish-on-hook indicator and click the current mouse position.
    
    Enhanced with multi-scale template matching and fallback detection
    for Roblox update compatibility.

    Returns True when fish detected and minigame started, False otherwise.
    """
    # Validate Roblox before checking for fish
    if not validate_roblox_and_game():
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
        print("Warning: Fish_On_Hook template not loaded, using fallback detection")
        return _fish_on_hook_fallback()

    # Get screen dimensions for fallback clicking
    screen_w, screen_h = pyautogui.size()
    
    # Use broader fish on hook detection region - covers center area where indicator appears
    # Based on 1920x1080 resolution, fish indicator typically appears in center-upper area
    fish_region_left = 600
    fish_region_top = 200  
    fish_region_right = 1320
    fish_region_bottom = 500
    fish_region_width = fish_region_right - fish_region_left
    fish_region_height = fish_region_bottom - fish_region_top
    
    # Create region tuple (left, top, width, height) for screenshot
    region = (fish_region_left, fish_region_top, fish_region_width, fish_region_height)
    
    # Enhanced multi-scale template matching for Roblox update compatibility
    # Lower threshold for better detection of new fish indicator
    found, score = _match_template_multi_scale(generic_tpl, region, threshold=0.6)
    
    # Save debug screenshot of detection region for template creation help (every 5 seconds)
    global _last_debug_screenshot_time
    if '_last_debug_screenshot_time' not in globals():
        _last_debug_screenshot_time = 0
    
    if time.time() - _last_debug_screenshot_time > 5.0:
        try:
            debug_screenshot = pyautogui.screenshot(region=region)
            debug_screenshot.save("fish_detection_region_debug.png")
            print(f"🔍 Fish detection region saved as: fish_detection_region_debug.png (score: {score:.3f})")
            _last_debug_screenshot_time = time.time()
        except Exception as e:
            print(f"Debug screenshot failed: {e}")
    
    # If multi-scale fails, try original single-scale method as fallback
    if not found and score == 0.0:
        print("Multi-scale detection failed, trying original method...")
        try:
            found, score = _match_template_in_region(generic_tpl, region, threshold=0.6)
        except Exception as e:
            print(f"Original template matching also failed: {e}")
            return _fish_on_hook_fallback()
    
    if found:
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
        # Load as color image to match screenshot format
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is not None and img.size > 0:
            # Only print template info if it's unusually large (potential issue)
            if img.shape[0] > 200 or img.shape[1] > 200:
                print(f"⚠️ Large template: {path.name} (shape: {img.shape}) - consider resizing for better performance")
            else:
                print(f"✅ Template loaded: {path.name} (shape: {img.shape})")
            return img
        else:
            print(f"❌ Template failed to load: {path.name}")
    except Exception as e:
        print(f"❌ Template loading error: {path.name} - {e}")
    return None

try:
    POWER_MAX_TPL = safe_load_template(IMAGES_DIR / 'Power_Max.png')
    POWER_ACTIVE_TPL = safe_load_template(IMAGES_DIR / 'Power_Active.png')
    FISH_ON_HOOK_TPL = safe_load_template(IMAGES_DIR / 'Fish_On_Hook.jpg')
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
    Minigame bar spawns at coordinates (510, 794) to (1418, 855).
    
    Returns dict with:
    - indicator_pos: float 0.0-1.0 (normalized position of white indicator)
    - fish_pos: float 0.0-1.0 (normalized position of fish)
    - minigame_active: bool (whether minigame UI is detected)
    """
    try:
        # Specific minigame bar coordinates (provided by user)
        minigame_left = 510
        minigame_top = 794
        minigame_right = 1418
        minigame_bottom = 855
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
    Handles both normal brown fish color and green hover state for basic fishing rod.
    """
    try:
        # Use dual color detection for basic fishing rod
        # Normal brown fish color: AHK hex color 0x5B4B43 to BGR (OpenCV uses BGR)
        brown_fish_color = np.array([67, 75, 91])
        brown_tolerance = 8
        
        # Green hover state color (when white indicator hovers over fish)
        green_fish_color = np.array([0, 180, 0])  # Bright green in BGR
        green_tolerance = 30  # Higher tolerance for green variations
        
        # Create color ranges for both states
        lower_brown = np.clip(brown_fish_color - brown_tolerance, 0, 255)
        upper_brown = np.clip(brown_fish_color + brown_tolerance, 0, 255)
        
        lower_green = np.clip(green_fish_color - green_tolerance, 0, 255)
        upper_green = np.clip(green_fish_color + green_tolerance, 0, 255)
        
        # Create masks for both colors
        mask_brown = cv2.inRange(screenshot_bgr, lower_brown, upper_brown)
        mask_green = cv2.inRange(screenshot_bgr, lower_green, upper_green)
        
        # Combine masks (detect either brown OR green)
        mask = cv2.bitwise_or(mask_brown, mask_green)
        
        # Debug: Check which color was detected
        brown_pixels = cv2.countNonZero(mask_brown)
        green_pixels = cv2.countNonZero(mask_green)
        
        color_state = "normal" if brown_pixels > green_pixels else "hover" if green_pixels > 0 else "none"
        if brown_pixels > 0 or green_pixels > 0:
            print(f"🎣 Fish color state: {color_state} (brown:{brown_pixels}, green:{green_pixels})")
        
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
    Detect minigame bar presence using template matching with MiniGame_Bar.png only.
    No pixel scanning fallbacks - pure image-based detection.
    Returns True if minigame bar is detected, False otherwise.
    """
    try:
        # Only use template matching with MiniGame_Bar.png
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
                return False
        else:
            print("Warning: MiniGame_Bar.png template not loaded - minigame detection unavailable")
            return False
        
    except Exception as e:
        print(f"Error detecting minigame bar presence: {e}")
        return False


def handle_fishing_minigame(minigame_controller):
    """
    Handle the fishing minigame by detecting the UI and making decisions.
    Only runs after Fish_On_Hook detection - not for casting minigame.
    
    Returns True when minigame is complete, False to continue.
    """
    try:
        # Additional validation: Only run if we're truly in fish-catching minigame
        # (This function should only be called after Fish_On_Hook detection)
        
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
        pass


def main_fishing_loop():
    """Main fishing automation loop."""
    
    # Import the rod detector and minigame logic
    try:
        from BackGroud_Logic.FishingRodDetector import check_region_and_act
        from BackGroud_Logic.Fishing_MiniGame import MinigameController, MinigameConfig
    except ImportError as e:
        return
    
    # Initialize minigame controller with AHK-style configuration for BASIC FISHING ROD
    minigame_config = MinigameConfig()
    
    # Set up AHK parameters optimized for basic fishing rod
    minigame_config.control = 0.18  # Basic fishing rod Control stat (lower than advanced rods)
    
    # Enhanced color detection for basic fishing rod (handles green hover state)
    minigame_config.fish_bar_color_tolerance = 15  # Higher tolerance for dual color detection
    minigame_config.white_bar_color_tolerance = 20  # Increased for better white indicator detection
    
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
            
            pass
        else:
            pass
    else:
        pass
    
    minigame_controller = MinigameController(minigame_config)
    
    # Fishing state variables
    fishing_state = "waiting"  # "waiting", "casting", "hooking", "minigame", "reeling"
    cast_attempts = 0
    max_cast_attempts = 3
    minigame_start_time = 0
    last_rod_click_time = 0  # Track when we last clicked the rod
    rod_click_cooldown = 3.0  # Wait 3 seconds before clicking rod again
    last_validation_time = 0  # Track when we last validated Roblox
    validation_interval = 10.0  # Only validate every 10 seconds to reduce spam (extended for Roblox update)
    cast_start_time = 0  # Track when we started waiting for fish
    fishing_timeout = 60.0  # 60 seconds timeout for fish to bite (extended for Roblox update)
    
    try:
        while True:
            # Validate Roblox periodically (not every loop to reduce debug spam)
            current_time = time.time()
            if current_time - last_validation_time > validation_interval:
                if not validate_roblox_and_game():
                    if not bring_roblox_to_front():
                        time.sleep(2)
                        continue
                    # Wait a moment after bringing to front
                    time.sleep(0.5)
                    # Revalidate after bringing to front
                    if not validate_roblox_and_game():
                        time.sleep(2)
                        continue
                last_validation_time = current_time
            
            # Check for fishing rod state only when in waiting/equipping state (with cooldown to prevent spam clicking)
            current_time = time.time()
            if fishing_state in ["waiting", "equipping"]:
                if current_time - last_rod_click_time < rod_click_cooldown:
                    # Still in cooldown period, skip rod detection
                    time.sleep(0.1)
                    rod_result = None
                else:
                    rod_result = check_region_and_act()
            else:
                # Skip rod detection when casting/hooking/minigame
                rod_result = None
            
            if rod_result is True:  # UN (unequipped) detected and clicked
                fishing_state = "equipping"
                cast_attempts = 0
                last_rod_click_time = current_time  # Record click time
                
                # Wait for rod to equip with periodic checks
                for wait_check in range(8):  # Check up to 4 seconds
                    time.sleep(0.5)
                    # Quick check if rod is now equipped
                    temp_result = check_region_and_act()
                    if temp_result is False:  # EQ detected
                        break
                    elif temp_result is None:
                        pass
                else:
                    pass
                
                # After rod is equipped, center mouse for fishing
                # Get Roblox window center for mouse positioning
                if not WINDOW_MANAGER_AVAILABLE:
                    print("ERROR: Window manager not available - waiting...")
                    time.sleep(2)
                    continue
                    
                center_x, center_y = get_roblox_coordinates()
                if center_x is None or center_y is None:
                    print("ERROR: Cannot get Roblox coordinates - waiting...")
                    time.sleep(2)
                    continue
                
                # Move mouse to center of Roblox window/screen
                if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
                    virtual_mouse.smooth_move_to(center_x, center_y)
                else:
                    smooth_move_to(center_x, center_y)
                
                time.sleep(0.5)  # Brief pause before continuing
                
            elif rod_result is False:  # EQ (equipped) detected - rod is ready
                if fishing_state == "waiting" or fishing_state == "equipping":
                    fishing_state = "casting"
                    cast_attempts = 0
                else:
                    pass
                    
            elif rod_result is None:  # No clear detection or error
                # Continue with current state but add small delay
                time.sleep(0.2)
                
            if fishing_state == "casting":
                # Get Roblox window center for casting
                center_x, center_y = get_roblox_coordinates()
                if center_x is None or center_y is None:
                    # Fallback to screen center
                    screen_w, screen_h = pyautogui.size()
                    center_x, center_y = screen_w // 2, screen_h // 2
                
                # Cast the rod at center position
                print(f"🎣 Casting fishing rod...")
                CastFishingRod(center_x, center_y - 20)
                time.sleep(2.0)  # Wait longer for casting minigame to fully disappear
                
                print(f"🔎 Entering hooking state - waiting for fish...")
                fishing_state = "hooking"
                cast_start_time = time.time()  # Record when we start waiting for fish
                cast_attempts += 1
                
            elif fishing_state == "hooking":
                # Check for 60-second timeout (extended for Roblox update compatibility)
                current_time = time.time()
                time_waiting = current_time - cast_start_time
                time_remaining = fishing_timeout - time_waiting
                
                if time_waiting >= fishing_timeout:
                    print(f"⏰ Hooking timeout reached ({fishing_timeout}s), resetting to waiting...")
                    fishing_state = "waiting"  # This will trigger rod detection and re-equipping
                    cast_attempts = 0
                    time.sleep(0.2)  # Brief pause before restarting
                    continue
                
                # Save debug screenshot every 10 seconds for Roblox update analysis
                if int(time_waiting) % 10 == 0 and abs(time_waiting - int(time_waiting)) < 0.5:
                    try:
                        debug_screenshot = pyautogui.screenshot()
                        debug_path = f"debug_roblox_update_{int(current_time)}.png"
                        debug_screenshot.save(debug_path)
                        print(f"📸 Debug screenshot saved: {debug_path}")
                    except Exception as e:
                        print(f"Debug screenshot failed: {e}")
                
                # Check for fish on hook
                hook_result = Fish_On_Hook(0, 0)  # Coordinates not used in current implementation
                
                if hook_result:
                    print(f"🐟 FISH ON HOOK DETECTED! Starting minigame... (hook_result: {hook_result})")
                    fishing_state = "minigame"
                    minigame_start_time = time.time()
                else:
                    # Debug: Show we're still waiting for fish (but don't spam)
                    if int(current_time) % 5 == 0 and abs(current_time - int(current_time)) < 0.1:
                        print(f"⏳ Waiting for fish... ({time_remaining:.1f}s remaining)")
                
                # Use fishing ability if available
                Use_Ability_Fishing(0, 0)
                
                # Check shift state
                Shift_State(0, 0)
                
                # Fallback timeout after max cast attempts
                if cast_attempts >= max_cast_attempts:
                    fishing_state = "waiting"
                    cast_attempts = 0
                
            elif fishing_state == "minigame":
                # Handle the fishing minigame
                minigame_result = handle_fishing_minigame(minigame_controller)
                
                if minigame_result or (time.time() - minigame_start_time) > 15:  # 15 second timeout
                    print("Minigame done! Fishing cycle complete, resetting...")
                    fishing_state = "waiting"
                    cast_attempts = 0
                    time.sleep(0.2)  # Brief pause before next cycle
                
            # Small delay between iterations
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        pass
    except Exception as e:
        pass
    finally:
        pass


if __name__ == "__main__":
    main_fishing_loop()
