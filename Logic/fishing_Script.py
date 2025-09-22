import time
import sys
import os
import cv2
import numpy as np
import pyautogui
import random
import math
import win32gui
import win32con
from pathlib import Path

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

# Import fishing rod detector functions
try:
    import BackGroud_Logic.FishingRodDetector as FishingRodDetector
    FISHING_ROD_DETECTOR_AVAILABLE = True
except ImportError as e:
    FISHING_ROD_DETECTOR_AVAILABLE = False
    FishingRodDetector = None
    print(f"Warning: FishingRodDetector not available: {e}")

# Import minigame functions
try:
    import BackGroud_Logic.Fishing_MiniGame as FishingMiniGame
    FISHING_MINIGAME_AVAILABLE = True
except ImportError as e:
    FISHING_MINIGAME_AVAILABLE = False
    FishingMiniGame = None
    print(f"Warning: FishingMiniGame not available: {e}")

# Import Roblox detection functions
try:
    import BackGroud_Logic.IsRoblox_Open as IsRobloxOpen
    ISROBLOX_OPEN_AVAILABLE = True
except ImportError as e:
    ISROBLOX_OPEN_AVAILABLE = False
    IsRobloxOpen = None
    print(f"Warning: IsRoblox_Open not available: {e}")

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








def CastFishingRod(x, y, hold_seconds=0.93):
    # Validate Roblox before casting
    if not (ISROBLOX_OPEN_AVAILABLE and IsRobloxOpen and IsRobloxOpen.validate_roblox_and_game()):
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
        virtual_mouse.move_to(target_x, target_y)
        
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
    if not (ISROBLOX_OPEN_AVAILABLE and IsRobloxOpen and IsRobloxOpen.validate_roblox_and_game()):
        return False
    
    # load detector templates lazily
    try:
        if not FISHING_ROD_DETECTOR_AVAILABLE or FishingRodDetector is None:
            return False
        frod = FishingRodDetector.get_detector_module()
    except (RuntimeError, AttributeError):
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
            debug_path = os.path.join("debug", "fish_detection_region_debug.png")
            debug_screenshot.save(debug_path)
            print(f"🔍 Fish detection region saved as: {debug_path} (score: {score:.3f})")
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
            virtual_mouse.click_at(click_x, click_y)
            success1 = True
            
            # Second click to ensure minigame starts
            virtual_mouse.click_at(click_x, click_y)
            success2 = True
            
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
        if not FISHING_ROD_DETECTOR_AVAILABLE or FishingRodDetector is None:
            return False
        frod = FishingRodDetector.get_detector_module()
    except (RuntimeError, AttributeError):
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
    SHIFT_LOCK_TPL = safe_load_template(IMAGES_DIR / 'Shift_Lock.png')
except Exception:
    # set templates to None if loading fails
    POWER_MAX_TPL = None
    POWER_ACTIVE_TPL = None
    FISH_ON_HOOK_TPL = None
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
        if not FISHING_ROD_DETECTOR_AVAILABLE or FishingRodDetector is None:
            left_tpl = None
            right_tpl = None
        else:
            frod = FishingRodDetector.get_detector_module()
            left_tpl = getattr(frod, 'FISH_LEFT_TPL', None)
            right_tpl = getattr(frod, 'FISH_RIGHT_TPL', None)
    except (RuntimeError, AttributeError):
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
        if not FISHING_ROD_DETECTOR_AVAILABLE or FishingRodDetector is None:
            return
        frod = FishingRodDetector.get_detector_module()
    except (RuntimeError, AttributeError):
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
    
    # Check that required modules are available
    if not FISHING_ROD_DETECTOR_AVAILABLE or FishingRodDetector is None:
        print("ERROR: FishingRodDetector not available")
        return
    
    if not FISHING_MINIGAME_AVAILABLE or FishingMiniGame is None:
        print("ERROR: FishingMiniGame not available")
        return
    
    # Initialize minigame controller with AHK-style configuration for BASIC FISHING ROD
    minigame_config = FishingMiniGame.MinigameConfig()
    
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
    
    minigame_controller = FishingMiniGame.MinigameController(minigame_config)
    
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
                if not (ISROBLOX_OPEN_AVAILABLE and IsRobloxOpen and IsRobloxOpen.validate_roblox_and_game()):
                    if not (ISROBLOX_OPEN_AVAILABLE and IsRobloxOpen and IsRobloxOpen.bring_roblox_to_front()):
                        time.sleep(2)
                        continue
                    # Wait a moment after bringing to front
                    time.sleep(0.5)
                    # Revalidate after bringing to front
                    if not (ISROBLOX_OPEN_AVAILABLE and IsRobloxOpen and IsRobloxOpen.validate_roblox_and_game()):
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
                    rod_result = FishingRodDetector.check_region_and_act()
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
                    temp_result = FishingRodDetector.check_region_and_act()
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
                    virtual_mouse.move_to(center_x, center_y)
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
                        debug_path = os.path.join("debug", f"debug_roblox_update_{int(current_time)}.png")
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
                if FISHING_MINIGAME_AVAILABLE and FishingMiniGame is not None:
                    minigame_result = FishingMiniGame.handle_fishing_minigame(minigame_controller)
                else:
                    print("ERROR: FishingMiniGame not available")
                    minigame_result = True  # End minigame
                
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
