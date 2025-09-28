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

# Debug Logger
try:
    from BackGround_Logic.Debug_Logger import debug_log, LogCategory
    DEBUG_LOGGER_AVAILABLE = True
except ImportError:
    DEBUG_LOGGER_AVAILABLE = False
    # Fallback log categories
    from enum import Enum
    class LogCategory(Enum):
        FISH_DETECTION = "FISH_DETECTION"
        FISHING_MAIN = "FISHING_MAIN"
        MINIGAME_ACTIONS = "MINIGAME_ACTIONS"
        SYSTEM = "SYSTEM"
        ERROR = "ERROR"
    def debug_log(category, message):
        print(f"[{category.value}] {message}")

# Import virtual mouse driver
virtual_mouse = None
VIRTUAL_MOUSE_AVAILABLE = False

try:
    from BackGround_Logic.Virtual_Mouse import VirtualMouse
    virtual_mouse = VirtualMouse()
    VIRTUAL_MOUSE_AVAILABLE = True
except ImportError as e:
    virtual_mouse = None
    VIRTUAL_MOUSE_AVAILABLE = False

# Import virtual keyboard driver
virtual_keyboard = None
VIRTUAL_KEYBOARD_AVAILABLE = False

try:
    from BackGround_Logic.Virtual_Keyboard import VirtualKeyboard
    virtual_keyboard = VirtualKeyboard()
    VIRTUAL_KEYBOARD_AVAILABLE = True
except ImportError as e:
    virtual_keyboard = None
    VIRTUAL_KEYBOARD_AVAILABLE = False

# Import window manager for proper Roblox window handling
try:
    from BackGround_Logic.Window_Manager import roblox_window_manager, get_roblox_coordinates, get_roblox_window_region, ensure_roblox_focused # type: ignore
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
    import BackGround_Logic.Fishing_Rod_Detector as FishingRodDetector
    FISHING_ROD_DETECTOR_AVAILABLE = True
except ImportError as e:
    FISHING_ROD_DETECTOR_AVAILABLE = False
    FishingRodDetector = None
    debug_log(LogCategory.SYSTEM, f"Warning: FishingRodDetector not available: {e}")

# Import minigame functions
try:
    import BackGround_Logic.Fishing_Mini_Game as FishingMiniGame
    FISHING_MINIGAME_AVAILABLE = True
except ImportError as e:
    FISHING_MINIGAME_AVAILABLE = False
    FishingMiniGame = None
    debug_log(LogCategory.SYSTEM, f"Warning: FishingMiniGame not available: {e}")

# Import Roblox detection functions
try:
    import BackGround_Logic.Is_Roblox_Open as IsRobloxOpen
    ISROBLOX_OPEN_AVAILABLE = True
except ImportError as e:
    ISROBLOX_OPEN_AVAILABLE = False
    IsRobloxOpen = None
    debug_log(LogCategory.SYSTEM, f"Warning: IsRoblox_Open not available: {e}")

# Import enhanced fish detector (reduces false positives at event islands)
try:
    from BackGround_Logic.Enhanced_Fish_Detector import EnhancedFishDetector
    ENHANCED_FISH_DETECTOR_AVAILABLE = True
except ImportError as e:
    ENHANCED_FISH_DETECTOR_AVAILABLE = False
    EnhancedFishDetector = None
    debug_log(LogCategory.SYSTEM, f"Warning: Enhanced Fish Detector not available: {e}")

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
        time.sleep(0.1)  # Brief delay after move
        
        # Use separate mouse_down/mouse_up for proper casting hold
        # This is the bypass method that avoids detection
        virtual_mouse.mouse_down(target_x, target_y, 'left')  # Press down
        time.sleep(actual_hold)  # Hold for the full duration (~0.9s)
        virtual_mouse.mouse_up(target_x, target_y, 'left')    # Release
        
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
    # Simulate pressing 'i' 45 times to zoom in using VirtualKeyboard bypass.
    # x,y are kept for API compatibility but aren't used for key presses.
    
    # Ensure Roblox window is focused for keyboard input
    if WINDOW_MANAGER_AVAILABLE:
        ensure_roblox_focused()
    
    # Use VirtualKeyboard if available (bypass method)
    if VIRTUAL_KEYBOARD_AVAILABLE and virtual_keyboard is not None:
        virtual_keyboard.tap_key_multiple('i', 45, delay=duration)
    else:
        # Fallback to PyAutoGUI (detectable)
        for _ in range(45):
            pyautogui.press('i')
            time.sleep(duration)  # Delay for Roblox key registration

def Zoom_Out(x, y, duration=0.05):
    # Simulate pressing 'o' four times to zoom out using VirtualKeyboard bypass.
    # x,y are kept for API compatibility but aren't used for key presses.
    
    # Ensure Roblox window is focused for keyboard input
    if WINDOW_MANAGER_AVAILABLE:
        ensure_roblox_focused()
    
    # Use VirtualKeyboard if available (bypass method)
    if VIRTUAL_KEYBOARD_AVAILABLE and virtual_keyboard is not None:
        virtual_keyboard.tap_key_multiple('o', 4, delay=duration)
    else:
        # Fallback to PyAutoGUI (detectable)
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
            debug_log(LogCategory.ERROR, "Error: Template is None or empty")
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
            debug_log(LogCategory.ERROR, f"Error: Unexpected template shape: {template.shape}")
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
                debug_log(LogCategory.FISH_DETECTION, f"🐟 FISH ON HOOK DETECTED! (confidence: {max_val:.3f}, scale: {scale})")
                return True, max_val
        
        # If we get here, no match at any scale
        if best_score > 0.5:  # Show near-misses for debugging
            debug_log(LogCategory.FISH_DETECTION, f"🔍 Fish detection near-miss (best: {best_score:.3f}, threshold: {threshold})")
        
        return False, best_score
        
    except Exception as e:
        debug_log(LogCategory.ERROR, f"Error in multi-scale Fish_On_Hook detection: {e}")
        debug_log(LogCategory.ERROR, f"Template shape: {template.shape if template is not None else 'None'}")
        debug_log(LogCategory.ERROR, f"Template dtype: {template.dtype if template is not None else 'None'}")
        return False, 0.0

def _detect_fish_on_hook_template(region):
    """
    Detect fish on hook using the improved Fish_On_Hook.png template.
    The template has been AI-processed to remove background and focus on key indicators.
    
    Returns: (found: bool, confidence: float)
    """
    try:
        # Check if template is loaded
        if FISH_ON_HOOK_TPL is None:
            debug_log(LogCategory.FISH_DETECTION, "⚠️ Fish_On_Hook template not loaded, using fallback detection")
            return _detect_exclamation_indicator_fallback(region)
        
        # DEBUG: Save screenshot of the detection region
        try:
            import pyautogui
            screenshot = pyautogui.screenshot(region=region)
            
            # Ensure debug directory exists
            debug_dir = Path(__file__).parent.parent / 'debug'
            debug_dir.mkdir(exist_ok=True)
            
            debug_path = debug_dir / 'fish_detection_region.png'
            screenshot.save(debug_path)
            debug_log(LogCategory.FISH_DETECTION, f"🔍 DEBUG: Saved detection region screenshot to {debug_path}")
        except Exception as debug_e:
            debug_log(LogCategory.ERROR, f"⚠️ Debug screenshot failed: {debug_e}")
        
        # Since this is a large AI-processed template, use multi-scale matching
        # for better accuracy across different game resolutions
        scales = [1.0, 0.8, 0.6, 0.4]  # Multiple scales for large template
        best_score = 0.0
        found_at_any_scale = False
        
        for scale in scales:
            try:
                # Resize template for this scale
                if scale != 1.0:
                    h, w = FISH_ON_HOOK_TPL.shape[:2]
                    new_h, new_w = int(h * scale), int(w * scale)
                    # Skip if template becomes too small
                    if new_h < 20 or new_w < 20:
                        continue
                    scaled_template = cv2.resize(FISH_ON_HOOK_TPL, (new_w, new_h))
                else:
                    scaled_template = FISH_ON_HOOK_TPL
                
                # Use lower threshold for AI-processed template (background removed)
                found, score = _match_template_in_region(scaled_template, region, threshold=0.55)
                
                if score > best_score:
                    best_score = score
                
                debug_log(LogCategory.FISH_DETECTION, f"🔍 Scale {scale:.1f}: score={score:.3f}, found={found}")
                
                if found:
                    debug_log(LogCategory.FISH_DETECTION, f"🐟 FISH ON HOOK DETECTED via template (scale {scale:.1f})! (score: {score:.3f})")
                    found_at_any_scale = True
                    break  # Found at this scale, no need to continue
                    
            except Exception as scale_error:
                debug_log(LogCategory.ERROR, f"⚠️ Error at scale {scale}: {scale_error}")
                continue
        
        # If no match at standard thresholds, try very low threshold as last resort
        if not found_at_any_scale and best_score > 0.35:
            print(f"🔍 Trying very low threshold detection (best score: {best_score:.3f})")
            # Try the original template with very low threshold
            found_low, score_low = _match_template_in_region(FISH_ON_HOOK_TPL, region, threshold=0.35)
            if found_low:
                print(f"🐟 FISH ON HOOK DETECTED via template (low threshold)! (score: {score_low:.3f})")
                return True, score_low
        
        # If still no detection, try simple color-based detection as emergency fallback
        if not found_at_any_scale and best_score < 0.3:
            print("🔍 Template detection failed, trying color-based emergency detection...")
            color_found, color_score = _detect_red_exclamation_simple(region)
            if color_found:
                print(f"🐟 FISH DETECTED via color fallback! (score: {color_score:.3f})")
                return True, color_score
        
        return found_at_any_scale, best_score
        
    except Exception as e:
        print(f"Error in template-based Fish_On_Hook detection: {e}")
        # Fallback to color-based detection if template fails
        return _detect_exclamation_indicator_fallback(region)


def _detect_red_exclamation_simple(region):
    """
    Simple color-based detection for red exclamation marks.
    Emergency fallback when template matching completely fails.
    """
    try:
        import pyautogui
        import numpy as np
        
        # Take screenshot of region
        screenshot = pyautogui.screenshot(region=region)
        screenshot_np = np.array(screenshot)
        screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
        
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2HSV)
        
        # Red color range (for red exclamation marks like in the screenshot)
        red_lower1 = np.array([0, 120, 120])
        red_upper1 = np.array([10, 255, 255])
        red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
        
        red_lower2 = np.array([170, 120, 120])
        red_upper2 = np.array([180, 255, 255])
        red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
        
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        red_pixels = cv2.countNonZero(red_mask)
        
        # Simple threshold - if we have enough red pixels, likely an exclamation
        if red_pixels > 30:  # Lowered from 50 - user has 86 pixels detected
            confidence = min(red_pixels / 300.0, 1.0)  # Adjusted scaling
            print(f"🔍 Simple color detection: {red_pixels} red pixels, confidence: {confidence:.3f}")
            return red_pixels > 60, confidence  # Lowered from 100 to 60 for detection
        
        return False, 0.0
        
    except Exception as e:
        print(f"Error in simple color detection: {e}")
        return False, 0.0


def _detect_exclamation_indicator_fallback(region):
    """
    Detect the exclamation mark "!" that appears when fish is on hook.
    Uses color analysis and shape detection instead of template matching.
    
    Returns: (found: bool, confidence: float)
    """
    try:
        # Take screenshot of the fish detection region
        screenshot = pyautogui.screenshot(region=region)
        screenshot_np = np.array(screenshot)
        screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
        
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2HSV)
        
        # Method 1: Look for white/bright exclamation marks
        # White range in HSV
        white_lower = np.array([0, 0, 180])    # Very bright
        white_upper = np.array([180, 50, 255]) # Low saturation, high value
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        
        # Method 2: Look for yellow/orange exclamation marks (common in games)
        # Yellow range in HSV  
        yellow_lower = np.array([15, 100, 150])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        # Method 3: Look for red exclamation marks
        # Red range in HSV (two ranges due to hue wraparound)
        red_lower1 = np.array([0, 120, 120])
        red_upper1 = np.array([10, 255, 255])
        red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
        
        red_lower2 = np.array([170, 120, 120])
        red_upper2 = np.array([180, 255, 255])
        red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        
        # EXCLUDE blue/cyan colors that match energy orbs
        # Blue/cyan range to exclude (your character's abilities)
        blue_lower = np.array([80, 50, 50])   # Cyan/blue range
        blue_upper = np.array([130, 255, 255])
        blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)
        
        # Combine exclamation color masks but subtract blue/cyan
        combined_mask = cv2.bitwise_or(cv2.bitwise_or(white_mask, yellow_mask), red_mask)
        combined_mask = cv2.bitwise_and(combined_mask, cv2.bitwise_not(blue_mask))  # Remove blue areas
        
        # Method 4: Edge detection for "!" shape
        gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Count pixels in each detection method
        white_pixels = cv2.countNonZero(white_mask)
        yellow_pixels = cv2.countNonZero(yellow_mask)
        red_pixels = cv2.countNonZero(red_mask)
        edge_pixels = cv2.countNonZero(edges)
        total_colored_pixels = cv2.countNonZero(combined_mask)
        
        # Look for contours that might be "!" shaped
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Analyze contours for "!" characteristics
        exclamation_score = 0.0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 15:  # Too small for exclamation mark
                continue
            if area > 800:  # Too large (likely energy orb, not exclamation)
                continue
                
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # "!" should be taller than it is wide (strict ratio)
            aspect_ratio = h / w if w > 0 else 0
            if aspect_ratio > 2.5:  # Very tall and narrow like "!" (stricter)
                exclamation_score += 0.4
                
            # "!" should have reasonable size (smaller range)
            if 15 <= area <= 300:  # Smaller area for actual exclamation marks
                exclamation_score += 0.3
                
            # Additional checks for "!" characteristics
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            if hull_area > 0:
                solidity = area / hull_area
                if solidity > 0.7:  # Fairly solid shape
                    exclamation_score += 0.2
        
        # Calculate overall confidence
        confidence = 0.0
        
        # Color-based confidence
        if total_colored_pixels > 50:
            confidence += min(total_colored_pixels / 500.0, 0.4)
        
        # Edge-based confidence
        if edge_pixels > 100:
            confidence += min(edge_pixels / 1000.0, 0.3)
            
        # Shape-based confidence
        confidence += min(exclamation_score, 0.3)
        
        # Determine if fish is detected (stricter criteria)
        found = (confidence >= 0.5 and exclamation_score > 0.3 and total_colored_pixels < 1000) or \
                (exclamation_score > 0.6 and total_colored_pixels > 20 and total_colored_pixels < 500)
        
        if found:
            print(f"🐟 EXCLAMATION DETECTED! Colors:{total_colored_pixels}, Edges:{edge_pixels}, Shape:{exclamation_score:.2f}")
        
        return found, confidence
        
    except Exception as e:
        print(f"Error in exclamation detection: {e}")
        return False, 0.0

def _fish_on_hook_fallback():
    """
    Fallback detection method using alternative approaches.
    For use when exclamation detection fails.
    """
    try:
        # This can be expanded with OCR or other methods if needed
        return False
        
    except Exception as e:
        print(f"Error in fallback Fish_On_Hook detection: {e}")
        return False

def _detect_fish_enhanced(region):
    """
    Enhanced fish detection that reduces false positives from event island red water.
    Uses shape analysis, context awareness, and improved template matching.
    
    Returns: (found: bool, confidence: float, method: str)
    """
    if enhanced_fish_detector is not None:
        try:
            return enhanced_fish_detector.detect_fish_on_hook(region)
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Enhanced detector error: {e}")
    
    # Fallback to original detection if enhanced detector fails
    found, confidence = _detect_fish_on_hook_template(region)
    return found, confidence, "template_fallback"

def Fish_On_Hook(x, y, duration=0.011):
    """Detect the fish-on-hook indicator using improved template matching.
    
    Updated to use the AI-processed Fish_On_Hook.png template with background removed.
    This provides much more reliable detection than color-based exclamation mark detection.

    Returns True when fish detected and minigame started, False otherwise.
    """
    # Validate Roblox before checking for fish
    if not (ISROBLOX_OPEN_AVAILABLE and IsRobloxOpen and IsRobloxOpen.validate_roblox_and_game()):
        return False
    
    # Detection region covering ONLY the fishing line area, avoiding character
    # EXPANDED area based on user screenshot - exclamation appears above character center
    fish_region_left = 600    # Start further left to cover wider area
    fish_region_top = 180     # Start higher up to catch exclamation above character
    fish_region_right = 1300  # Wider coverage to handle different screen positions
    fish_region_bottom = 450  # Lower to catch exclamation at various heights
    fish_region_width = fish_region_right - fish_region_left
    fish_region_height = fish_region_bottom - fish_region_top
    
    print(f"🔍 Fish detection region: ({fish_region_left}, {fish_region_top}) to ({fish_region_right}, {fish_region_bottom})")
    print(f"🔍 Region size: {fish_region_width}x{fish_region_height}")
    
    # Create region tuple (left, top, width, height) for screenshot
    region = (fish_region_left, fish_region_top, fish_region_width, fish_region_height)
    
    # Enhanced detection method: Reduces false positives from event island red water
    found, confidence, method = _detect_fish_enhanced(region)
    print(f"🔍 Enhanced fish detection: found={found}, confidence={confidence:.3f}, method={method}")
    
    # Log detailed detection info for debugging event island issues
    if found:
        debug_log(LogCategory.FISH_DETECTION, f"🐟 FISH DETECTED! Method: {method}, Confidence: {confidence:.3f}")
        if method == "context_color":
            print("⚠️ WARNING: Color-based detection used - may be affected by event island red water")
        elif method in ["template", "shape"]:
            print("✅ RELIABLE: Shape/template detection used - event island resistant")

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
            print(f"🖱️ Virtual mouse starting minigame at ({click_x}, {click_y})")
            
            # First click (instant - no delays needed with virtual mouse)
            virtual_mouse.click_at(click_x, click_y)
            print("✅ Virtual mouse first click completed")
            success1 = True
            
            # Brief delay between clicks
            time.sleep(0.1)
            
            # Second click to ensure minigame starts
            virtual_mouse.click_at(click_x, click_y)
            print("✅ Virtual mouse second click completed")
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
        # Use VirtualKeyboard if available (bypass method)
        if VIRTUAL_KEYBOARD_AVAILABLE and virtual_keyboard is not None:
            virtual_keyboard.key_down('shift')
            time.sleep(duration)
            virtual_keyboard.key_up('shift')
        else:
            # Fallback to PyAutoGUI (detectable)
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
    SHIFT_LOCK_TPL = safe_load_template(IMAGES_DIR / 'Shift_Lock.png')
    FISH_ON_HOOK_TPL = safe_load_template(IMAGES_DIR / 'Fish_On_Hook.png')
    print(f"✅ Fish on hook template loaded: Fish_On_Hook.png (shape: {FISH_ON_HOOK_TPL.shape if FISH_ON_HOOK_TPL is not None else 'None'})")
except Exception:
    # set templates to None if loading fails
    POWER_MAX_TPL = None
    POWER_ACTIVE_TPL = None
    SHIFT_LOCK_TPL = None
    FISH_ON_HOOK_TPL = None

# Initialize enhanced fish detector for reduced false positives
enhanced_fish_detector = None
if ENHANCED_FISH_DETECTOR_AVAILABLE:
    try:
        enhanced_fish_detector = EnhancedFishDetector(IMAGES_DIR)
        print("✅ Enhanced Fish Detector initialized - reduces false positives at event islands")
    except Exception as e:
        enhanced_fish_detector = None
        print(f"⚠️ Enhanced Fish Detector initialization failed: {e}")


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
        try:
            virtual_keyboard.key_press('z')
        except:
            pyautogui.press('z')  # fallback
        time.sleep(0.05)
        return

    # fallback: sample the bar fill and click if essentially full
    fill = _estimate_bar_fill(region)
    if fill >= 0.95:
        # fallback: treat as full and press activation key
        try:
            virtual_keyboard.key_press('z')
        except:
            pyautogui.press('z')  # fallback
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
    minigame_config.control = 0.17  # Basic fishing rod Control stat (lower than advanced rods)
    
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
    rod_click_cooldown = 5.0  # Wait 5 seconds before clicking rod again (prevent spam)
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
                    # Use gentle focus approach to avoid Roblox anti-cheat detection
                    focus_result = ISROBLOX_OPEN_AVAILABLE and IsRobloxOpen and IsRobloxOpen.bring_roblox_to_front()
                    if not focus_result:
                        print("🔄 Please manually click on Roblox window to continue fishing...")
                        time.sleep(3)  # Give user time to focus manually
                        continue
                    
                    # Wait a moment after gentle focus attempt
                    time.sleep(0.8)  # Slightly longer wait for human-like timing
                    
                    # Revalidate after focus attempt
                    if not (ISROBLOX_OPEN_AVAILABLE and IsRobloxOpen and IsRobloxOpen.validate_roblox_and_game()):
                        print("📋 Roblox validation failed. Make sure you're in Blox Fruits and the game is active.")
                        time.sleep(3)
                        continue
                last_validation_time = current_time
            
            # Check for fishing rod state only when in waiting/equipping state (with cooldown to prevent spam clicking)
            current_time = time.time()
            if fishing_state in ["waiting", "equipping"]:
                if current_time - last_rod_click_time < rod_click_cooldown:
                    # Still in cooldown period, skip rod detection
                    time.sleep(0.5)  # Longer delay to prevent spam
                    rod_result = None
                else:
                    rod_result = FishingRodDetector.check_region_and_act()
                    time.sleep(0.2)  # Brief delay after detection
            else:
                # Skip rod detection when casting/hooking/minigame - longer delay
                rod_result = None
                time.sleep(0.3)
            
            if rod_result is True:  # UN (unequipped) detected and clicked
                print("🔧 Rod unequipped - attempting to equip...")
                fishing_state = "equipping"
                cast_attempts = 0
                last_rod_click_time = current_time  # Record click time
                
                # Give more time for the click to register and rod to equip
                print("⏳ Waiting for rod to equip...")
                time.sleep(1.0)  # Initial delay for click to register
                
                # Wait for rod to equip with periodic checks
                equipped = False
                for wait_check in range(6):  # Check up to 3 seconds total
                    time.sleep(0.5)
                    # Check if rod is now equipped (without clicking)
                    temp_result = FishingRodDetector.check_region_and_act()
                    if temp_result is False:  # EQ detected - rod is equipped
                        print("✅ Rod successfully equipped!")
                        equipped = True
                        break
                    elif temp_result is None:  # No clear detection
                        continue
                    else:  # Still showing UN (unequipped)
                        continue
                
                if not equipped:
                    print("⚠️ Rod may not have equipped properly, continuing anyway...")
                    # Reset to waiting state to try again after cooldown
                    fishing_state = "waiting"
                
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
                    print("✅ Rod equipped - switching to casting state")
                    fishing_state = "casting"
                    cast_attempts = 0
                    time.sleep(0.5)  # Delay before entering casting state
                else:
                    print(f"🔄 Rod equipped but already in state: {fishing_state}")
                    pass
                    
            elif rod_result is None:  # No clear detection or error
                # Continue with current state but add small delay
                print(f"❓ No clear rod detection in state: {fishing_state}")
                time.sleep(0.2)
                
            if fishing_state == "casting":
                # Get Roblox window center for casting
                center_x, center_y = get_roblox_coordinates()
                if center_x is None or center_y is None:
                    # Fallback to screen center
                    screen_w, screen_h = pyautogui.size()
                    center_x, center_y = screen_w // 2, screen_h // 2
                
                # Cast the rod at center position
                print(f"🎣 Casting fishing rod at ({center_x}, {center_y - 20})...")
                cast_success = CastFishingRod(center_x, center_y - 20)
                
                if cast_success:
                    print("✅ Cast successful!")
                    time.sleep(3.0)  # Wait longer for casting animation and minigame to fully disappear
                    
                    print(f"🔎 Entering hooking state - waiting for fish...")
                    fishing_state = "hooking"
                    cast_start_time = time.time()  # Record when we start waiting for fish
                    cast_attempts += 1
                else:
                    print("❌ Cast failed! Returning to waiting state...")
                    fishing_state = "waiting"
                    time.sleep(2.0)  # Longer delay before retrying
                
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
                

                # Check for fish on hook
                hook_result = Fish_On_Hook(0, 0)  # Coordinates not used in current implementation
                

                if hook_result:
                    print(f"🐟 FISH ON HOOK DETECTED! Clicking and waiting for minigame...")
                    # Wait for minigame UI to load after fish click (Fish_On_Hook already clicked)
                    time.sleep(1.0)  # Wait 1 second for minigame to fully appear
                    print(f"🎮 Starting minigame detection...")
                    fishing_state = "minigame"
                    minigame_start_time = time.time()
                else:
                    # Show progress every 5 seconds
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
                print("🎮 Handling fishing minigame (post-click detection)")
                print("🎣 NOTE: Only detecting minigame AFTER fish click to avoid false positives")
                # Handle the fishing minigame
                if FISHING_MINIGAME_AVAILABLE and FishingMiniGame is not None:
                    minigame_result = FishingMiniGame.handle_fishing_minigame(minigame_controller)
                    print(f"🎮 Minigame handler result: {minigame_result}")
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
        print("🛑 Fishing script stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"❌ Fishing script error: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
    finally:
        print("🔄 Fishing script cleanup completed")


if __name__ == "__main__":
    main_fishing_loop()
