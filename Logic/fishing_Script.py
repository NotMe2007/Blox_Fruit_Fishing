import time
import sys
import os
import cv2
import numpy as np
import random
import math
import win32gui
import win32con
from pathlib import Path

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import all common dependencies from centralized Import_Utils
from BackGround_Logic.Import_Utils import (
    debug_log, LogCategory, DEBUG_LOGGER_AVAILABLE,
    virtual_mouse, VIRTUAL_MOUSE_AVAILABLE,
    is_virtual_mouse_available,
    virtual_keyboard, VIRTUAL_KEYBOARD_AVAILABLE,
    is_virtual_keyboard_available,
    screenshot, SCREEN_CAPTURE_AVAILABLE,
    is_screen_capture_available,
    roblox_window_manager, get_roblox_coordinates, 
    get_roblox_window_region, ensure_roblox_focused, 
    WINDOW_MANAGER_AVAILABLE, is_window_manager_available
)

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
    EnhancedFishDetector = None  # type: ignore
    debug_log(LogCategory.SYSTEM, f"Warning: Enhanced Fish Detector not available: {e}")

# Import pyautogui for fallback mouse control (detection risk - use Virtual_Mouse instead)
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    pyautogui = None  # type: ignore


def smooth_move_to(target_x, target_y, duration=None):
    """
    Move mouse to target position using Virtual Mouse (undetected).
    Falls back to manual cursor positioning if Virtual Mouse unavailable.
    """
    # If virtual mouse is available, use it (undetected)
    if is_virtual_mouse_available():
        try:
            virtual_mouse.move_to(target_x, target_y)
            return
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Virtual mouse move failed: {e}")
    
    # Fallback: Use Windows API directly for cursor positioning
    try:
        import ctypes
        ctypes.windll.user32.SetCursorPos(target_x, target_y)
    except Exception as e:
        debug_log(LogCategory.ERROR, f"Fallback cursor positioning failed: {e}")


def fallback_mouse_action(x, y, action, duration=0.01):
    """Fallback mouse action using Windows API when Virtual Mouse unavailable."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.SetCursorPos(x, y)
        
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        
        if action == "down":
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        elif action == "up":
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif action == "click":
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(duration)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    except Exception as e:
        debug_log(LogCategory.ERROR, f"Fallback mouse action failed: {e}")


def fallback_key_press(key_code):
    """Fallback key press using Windows API when Virtual Keyboard unavailable."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        KEYEVENTF_KEYUP = 0x0002
        
        user32.keybd_event(key_code, 0, 0, 0)  # Key down
        user32.keybd_event(key_code, 0, KEYEVENTF_KEYUP, 0)  # Key up
    except Exception as e:
        debug_log(LogCategory.ERROR, f"Fallback key press failed: {e}")


def get_mouse_position():
    """Get current mouse position using Virtual Mouse or Windows API fallback."""
    if is_virtual_mouse_available():
        try:
            return virtual_mouse.get_cursor_pos()
        except Exception:
            pass
    
    # Fallback to Windows API
    try:
        import ctypes
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        point = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
        return point.x, point.y
    except Exception as e:
        debug_log(LogCategory.ERROR, f"Get mouse position failed: {e}")
        return 0, 0


def get_screen_size():
    """Get screen dimensions using Windows API."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
        screen_h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
        return screen_w, screen_h
    except Exception as e:
        debug_log(LogCategory.ERROR, f"Get screen size failed: {e}")
        return 1920, 1080  # Default fallback








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
    if is_virtual_mouse_available():
        print("🛡️ [ULTRA-STEALTH] Using enhanced hardware-level casting")
        
        # Enhanced anti-detection: Larger random offset range
        cast_offset_x = random.randint(-8, 8)
        cast_offset_y = random.randint(-8, 8)
        final_cast_x = target_x + cast_offset_x
        final_cast_y = target_y + cast_offset_y
        
        # Phase 1: Pre-cast natural movement (critical for avoiding detection)
        # Move to a random position near the target first
        approach_distance = random.randint(25, 50)
        approach_angle = random.uniform(0, 2 * 3.14159)
        approach_x = final_cast_x + int(approach_distance * math.cos(approach_angle))
        approach_y = final_cast_y + int(approach_distance * math.sin(approach_angle))
        
        # Get current mouse position for natural movement
        current_pos = virtual_mouse.get_cursor_pos()
        if current_pos:
            print(f"🛡️ [ULTRA-STEALTH] Natural pre-cast movement from ({current_pos[0]}, {current_pos[1]})")
            # Move naturally to approach position
            virtual_mouse.human_like_move(current_pos[0], current_pos[1], approach_x, approach_y, 
                                        random.uniform(0.3, 0.7))
        else:
            virtual_mouse.move_to(approach_x, approach_y)
        
        # Phase 2: Human hesitation and adjustment
        hesitation_delay = random.uniform(0.2, 0.5)
        print(f"🛡️ [ULTRA-STEALTH] Human-like hesitation ({hesitation_delay:.2f}s)")
        time.sleep(hesitation_delay)
        
        # Small adjustment movement (like a human fine-tuning position)
        adjust_x = approach_x + random.randint(-10, 10)
        adjust_y = approach_y + random.randint(-10, 10)
        virtual_mouse.move_to(adjust_x, adjust_y)
        time.sleep(random.uniform(0.1, 0.25))
        
        # Phase 3: Final approach to cast position with natural curve
        print(f"🎣 [ULTRA-STEALTH] Natural approach to cast position ({final_cast_x}, {final_cast_y})")
        virtual_mouse.human_like_move(adjust_x, adjust_y, final_cast_x, final_cast_y, 
                                    random.uniform(0.2, 0.4))
        
        # Phase 4: Pre-cast stabilization (human behavior)
        stabilize_delay = random.uniform(0.1, 0.3)
        print(f"🛡️ [ULTRA-STEALTH] Pre-cast stabilization ({stabilize_delay:.2f}s)")
        time.sleep(stabilize_delay)
        
        print(f"🎣 [ULTRA-STEALTH] Enhanced hardware casting for {actual_hold:.2f}s")
        
        # Phase 5: Enhanced casting with variable timing
        cast_start_delay = random.uniform(0.05, 0.15)  # Human reaction time
        time.sleep(cast_start_delay)
        
        # Use separate mouse_down/mouse_up for proper casting hold with hardware input
        virtual_mouse.mouse_down(final_cast_x, final_cast_y, 'left')  # Press down
        time.sleep(actual_hold)  # Hold for the full duration (~0.9s)
        virtual_mouse.mouse_up(final_cast_x, final_cast_y, 'left')    # Release
        
        # Phase 6: Post-cast natural behavior
        post_cast_delay = random.uniform(0.2, 0.6)
        print(f"🛡️ [ULTRA-STEALTH] Post-cast natural delay ({post_cast_delay:.2f}s)")
        time.sleep(post_cast_delay)
        
        # Optional natural post-cast movement (50% chance)
        if random.choice([True, False]):
            post_move_x = final_cast_x + random.randint(-15, 15)
            post_move_y = final_cast_y + random.randint(-15, 15)
            virtual_mouse.move_to(post_move_x, post_move_y)
            print(f"🛡️ [ULTRA-STEALTH] Natural post-cast movement to ({post_move_x}, {post_move_y})")
        
        print("✅ [ULTRA-STEALTH] Enhanced hardware casting completed")
        
    else:
        # Fallback: Use Windows API directly for mouse control
        try:
            import ctypes
            user32 = ctypes.windll.user32
            
            # Add random offset for human-like variation
            offset_x = random.randint(-3, 3)
            offset_y = random.randint(-3, 3)
            final_x = target_x + offset_x
            final_y = target_y + offset_y
            
            # Move to position
            user32.SetCursorPos(final_x, final_y)
            time.sleep(0.1)
            
            # Mouse down and up (left button)
            MOUSEEVENTF_LEFTDOWN = 0x0002
            MOUSEEVENTF_LEFTUP = 0x0004
            
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(actual_hold)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Fallback mouse input failed: {e}")
            return False
    
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
        # Fallback: Use Windows API for key input
        try:
            import ctypes
            user32 = ctypes.windll.user32
            VK_I = 0x49  # Virtual key code for 'i'
            KEYEVENTF_KEYUP = 0x0002
            
            for _ in range(45):
                user32.keybd_event(VK_I, 0, 0, 0)  # Key down
                user32.keybd_event(VK_I, 0, KEYEVENTF_KEYUP, 0)  # Key up
                time.sleep(duration)
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Zoom in fallback failed: {e}")

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
        # Fallback: Use Windows API for key input
        try:
            import ctypes
            user32 = ctypes.windll.user32
            VK_O = 0x4F  # Virtual key code for 'o'
            KEYEVENTF_KEYUP = 0x0002
            
            for _ in range(4):
                user32.keybd_event(VK_O, 0, 0, 0)  # Key down
                user32.keybd_event(VK_O, 0, KEYEVENTF_KEYUP, 0)  # Key up
                time.sleep(duration)
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Zoom out fallback failed: {e}")

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
        
        # Take screenshot of the region using Windows API
        if SCREEN_CAPTURE_AVAILABLE and screenshot is not None:
            screenshot_img = screenshot(region=region)
        else:
            # Final fallback - try to use PIL directly
            try:
                from PIL import ImageGrab
                screenshot_img = ImageGrab.grab(bbox=region)
            except Exception as e:
                debug_log(LogCategory.ERROR, f"Screenshot capture failed: {e}")
                return False, 0.0
        
        if screenshot_img is None:
            debug_log(LogCategory.ERROR, "Failed to capture screenshot")
            return False, 0.0
        
        screenshot_cv = cv2.cvtColor(np.array(screenshot_img), cv2.COLOR_RGB2BGR).astype(np.uint8)
        
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
        # Take screenshot of the fish detection region using Windows API
        if SCREEN_CAPTURE_AVAILABLE and screenshot is not None:
            screenshot_img = screenshot(region=region)
        else:
            # Final fallback - try to use PIL directly
            try:
                from PIL import ImageGrab
                screenshot_img = ImageGrab.grab(bbox=region)
            except Exception as e:
                debug_log(LogCategory.ERROR, f"Screenshot capture failed: {e}")
                return False, 0.0
        
        if screenshot_img is None:
            debug_log(LogCategory.ERROR, "Failed to capture screenshot")
            return False, 0.0
        
        screenshot_np = np.array(screenshot_img)
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
    
    IMPORTANT: This function now ONLY detects fish - it does NOT start minigame clicks.
    Minigame clicks are handled separately by _start_minigame_clicks() for better control.

    Returns True when fish detected, False otherwise.
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

    # CRITICAL CHANGE: Only return detection result, don't start minigame
    # Minigame clicking is now handled separately for better verification
    return found

def _verify_fish_on_hook_template():
    """
    Additional verification using strict template matching to reduce false positives.
    This function specifically looks for the Fish_On_Hook template with high confidence.
    
    Returns True only if there's a high-confidence template match.
    """
    try:
        # Same detection region as main Fish_On_Hook function
        fish_region_left = 600
        fish_region_top = 180
        fish_region_right = 1300
        fish_region_bottom = 450
        fish_region_width = fish_region_right - fish_region_left
        fish_region_height = fish_region_bottom - fish_region_top
        
        region = (fish_region_left, fish_region_top, fish_region_width, fish_region_height)
        
        # Use template detection with HIGH threshold only
        found, confidence = _detect_fish_on_hook_template(region)
        
        print(f"🔍 Template verification: found={found}, confidence={confidence:.3f}")
        
        # Require HIGH confidence (0.75+) for verification
        if found and confidence >= 0.75:
            print(f"✅ High-confidence template verification passed!")
            return True
        else:
            print(f"❌ Template verification failed - confidence too low")
            return False
            
    except Exception as e:
        print(f"❌ Template verification error: {e}")
        return False

def _start_minigame_clicks():
    """
    Start the minigame by performing the required clicks with enhanced AHK-style focus.
    This replaces the clicking logic that was built into Fish_On_Hook.
    
    Based on Reddit post insights: Proper window focus before clicks is CRITICAL for Roblox.
    
    Returns True if clicks were performed successfully.
    """
    try:
        # CRITICAL: Enhanced window focus using AHK-style methods (Reddit solution)
        print("🎯 [AHK-STYLE] Ensuring aggressive window focus before minigame clicks...")
        if not (WINDOW_MANAGER_AVAILABLE and ensure_roblox_focused()):
            print("❌ Critical: Cannot ensure window focus - minigame may fail!")
            return False
        
        # Get click position - ONLY use Roblox window center
        click_x, click_y = get_roblox_coordinates()
        if click_x is None or click_y is None:
            print("ERROR: Cannot get Roblox coordinates for minigame click!")
            return False
        
        print(f"🎯 Starting minigame clicks at Roblox center ({click_x}, {click_y})")
        
        # Use virtual mouse for minigame start if available (with ultimate stealth)
        if is_virtual_mouse_available():
            print(f"�️ [ULTRA-STEALTH] PostMessage stealth clicking at ({click_x}, {click_y})")
            
            # First click using ultimate stealth method (PostMessage if possible)
            click_success1 = virtual_mouse.ultimate_stealth_click(click_x, click_y)
            if click_success1:
                print("🛡️ [ULTRA-STEALTH] PostMessage first click completed")
            else:
                print("🛡️ [ULTRA-STEALTH] Enhanced first click completed")
            
            # Brief delay between clicks for Roblox processing
            time.sleep(0.1)
            
            # Second click to ensure minigame starts (with stealth re-verification)
            click_success2 = virtual_mouse.ultimate_stealth_click(click_x, click_y)
            if click_success2:
                print("🛡️ [ULTRA-STEALTH] PostMessage second click completed")
            else:
                print("🛡️ [ULTRA-STEALTH] Enhanced second click completed")
            
            print("🛡️ [ULTRA-STEALTH] PostMessage minigame clicks completed - bypassing anti-cheat!")
            return True
                
        else:
            # Fallback to Windows API for mouse input
            print("Using Windows API fallback for minigame clicks")
            try:
                import ctypes
                user32 = ctypes.windll.user32
                
                offset_x = random.randint(-5, 5)
                offset_y = random.randint(-5, 5)
                final_x = click_x + offset_x
                final_y = click_y + offset_y
                
                # Move to position
                user32.SetCursorPos(final_x, final_y)
                time.sleep(0.05)
                
                # Mouse down and up (left button)
                MOUSEEVENTF_LEFTDOWN = 0x0002
                MOUSEEVENTF_LEFTUP = 0x0004
                
                # First click
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.05)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                
                # Brief delay between clicks
                time.sleep(0.1)
                
                # Second click
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.05)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                
                print("🎮 Windows API minigame clicks completed!")
                return True
                
            except Exception as e:
                print(f"❌ Windows API fallback failed: {e}")
                return False
            
    except Exception as e:
        print(f"❌ Minigame click error: {e}")
        return False


def Shift_State(x, y, duration=0.011):
    """Simulate pressing 'shift' to change the fishing state. Presses occur every `duration` seconds.
    x,y are kept for API compatibility but aren't used for key presses.
    """
    # check a 200x200 region centered on screen (100px around center)
    screen_w, screen_h = get_screen_size()
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
            # Fallback: Use Windows API for key input
            try:
                import ctypes
                user32 = ctypes.windll.user32
                VK_SHIFT = 0x10  # Virtual key code for Shift
                KEYEVENTF_KEYUP = 0x0002
                
                user32.keybd_event(VK_SHIFT, 0, 0, 0)  # Key down
                time.sleep(duration)
                user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)  # Key up
            except Exception as e:
                debug_log(LogCategory.ERROR, f"Shift key fallback failed: {e}")
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
if ENHANCED_FISH_DETECTOR_AVAILABLE and EnhancedFishDetector is not None:
    try:
        enhanced_fish_detector = EnhancedFishDetector(IMAGES_DIR)  # type: ignore
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
        
        # Use Windows API screen capture
        if SCREEN_CAPTURE_AVAILABLE and screenshot is not None:
            pil_img = screenshot(region=(x, y, w, h))
        else:
            # Final fallback - try to use PIL directly
            try:
                from PIL import ImageGrab
                pil_img = ImageGrab.grab(bbox=(x, y, x+w, y+h))
            except Exception as e:
                debug_log(LogCategory.ERROR, f"Screenshot capture failed: {e}")
                return False, 0.0
        
        if pil_img is None:
            debug_log(LogCategory.ERROR, "Failed to capture screenshot")
            return False, 0.0
        
        hay = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
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
        
        # Use Windows API screen capture
        if SCREEN_CAPTURE_AVAILABLE and screenshot is not None:
            pil_img = screenshot(region=(sample_x, sample_y, sample_w, sample_h))
        else:
            # Final fallback - try to use PIL directly
            try:
                from PIL import ImageGrab
                pil_img = ImageGrab.grab(bbox=(sample_x, sample_y, sample_x+sample_w, sample_y+sample_h))
            except Exception as e:
                debug_log(LogCategory.ERROR, f"Screenshot capture failed: {e}")
                return 0.0
        
        if pil_img is None:
            debug_log(LogCategory.ERROR, "Failed to capture screenshot")
            return 0.0
        
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
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
        screen_w, screen_h = get_screen_size()
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
        # Use ultra-stealth PostMessage click for undetectable input
        if is_virtual_mouse_available():
            current_x, current_y = virtual_mouse.get_cursor_pos()
            success = virtual_mouse.ultimate_stealth_click(current_x, current_y)
            if success:
                debug_log(LogCategory.FISH_DETECTION, f"🛡️ [ULTRA-STEALTH] PostMessage left fish click at ({current_x}, {current_y})")
            else:
                debug_log(LogCategory.FISH_DETECTION, f"🛡️ [ULTRA-STEALTH] Enhanced left fish click at ({current_x}, {current_y})")
        else:
            # Ultra-stealth fallback: Create virtual mouse instance
            try:
                from .BackGround_Logic import Virtual_Mouse
                fallback_mouse = Virtual_Mouse.VirtualMouse()
                current_x, current_y = fallback_mouse.get_cursor_pos()
                success = fallback_mouse.ultimate_stealth_click(current_x, current_y)
                if success:
                    debug_log(LogCategory.FISH_DETECTION, f"🛡️ [ULTRA-STEALTH] PostMessage fallback left fish click at ({current_x}, {current_y})")
                else:
                    debug_log(LogCategory.FISH_DETECTION, f"🛡️ [ULTRA-STEALTH] Enhanced fallback left fish click at ({current_x}, {current_y})")
            except Exception as e:
                debug_log(LogCategory.ERROR, f"🛡️ [ULTRA-STEALTH] Fallback click failed: {e}")
        
        time.sleep(duration)
        return True
    return False


def Fish_Right(x, y, duration=0.011):
    """Detect right-moving fish using Fish_Right template. Returns True when detected and clicks."""
    direction = _detect_fish_direction(region=None, threshold=0.84)
    if direction == 'right':
        # Use ultra-stealth PostMessage click for undetectable input
        if is_virtual_mouse_available():
            current_x, current_y = virtual_mouse.get_cursor_pos()
            success = virtual_mouse.ultimate_stealth_click(current_x, current_y)
            if success:
                debug_log(LogCategory.FISH_DETECTION, f"🛡️ [ULTRA-STEALTH] PostMessage right fish click at ({current_x}, {current_y})")
            else:
                debug_log(LogCategory.FISH_DETECTION, f"🛡️ [ULTRA-STEALTH] Enhanced right fish click at ({current_x}, {current_y})")
        else:
            # Ultra-stealth fallback: Create virtual mouse instance
            try:
                from .BackGround_Logic import Virtual_Mouse
                fallback_mouse = Virtual_Mouse.VirtualMouse()
                current_x, current_y = fallback_mouse.get_cursor_pos()
                success = fallback_mouse.ultimate_stealth_click(current_x, current_y)
                if success:
                    debug_log(LogCategory.FISH_DETECTION, f"🛡️ [ULTRA-STEALTH] PostMessage fallback right fish click at ({current_x}, {current_y})")
                else:
                    debug_log(LogCategory.FISH_DETECTION, f"🛡️ [ULTRA-STEALTH] Enhanced fallback right fish click at ({current_x}, {current_y})")
            except Exception as e:
                debug_log(LogCategory.ERROR, f"🛡️ [ULTRA-STEALTH] Fallback click failed: {e}")
        
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
        if VIRTUAL_KEYBOARD_AVAILABLE and virtual_keyboard is not None:
            try:
                virtual_keyboard.key_press('z')
            except Exception as e:
                debug_log(LogCategory.ERROR, f"Virtual keyboard 'z' press failed: {e}")
        else:
            # Fallback: Use Windows API for key input
            try:
                import ctypes
                user32 = ctypes.windll.user32
                VK_Z = 0x5A  # Virtual key code for 'z'
                KEYEVENTF_KEYUP = 0x0002
                
                user32.keybd_event(VK_Z, 0, 0, 0)  # Key down
                user32.keybd_event(VK_Z, 0, KEYEVENTF_KEYUP, 0)  # Key up
            except Exception as e:
                debug_log(LogCategory.ERROR, f"Key press fallback failed: {e}")
        time.sleep(0.05)
        return

    # fallback: sample the bar fill and click if essentially full
    fill = _estimate_bar_fill(region)
    if fill >= 0.95:
        # fallback: treat as full and press activation key
        if VIRTUAL_KEYBOARD_AVAILABLE and virtual_keyboard is not None:
            try:
                virtual_keyboard.key_press('z')
            except Exception as e:
                debug_log(LogCategory.ERROR, f"Virtual keyboard 'z' press failed: {e}")
        else:
            # Fallback: Use Windows API for key input
            try:
                import ctypes
                user32 = ctypes.windll.user32
                VK_Z = 0x5A  # Virtual key code for 'z'
                KEYEVENTF_KEYUP = 0x0002
                
                user32.keybd_event(VK_Z, 0, 0, 0)  # Key down
                user32.keybd_event(VK_Z, 0, KEYEVENTF_KEYUP, 0)  # Key up
            except Exception as e:
                debug_log(LogCategory.ERROR, f"Key press fallback failed: {e}")
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
            if is_virtual_mouse_available():
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Left mouse down
                time.sleep(0.01)  # 10ms click
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Left mouse up
                time.sleep(0.01)
            else:
                # Fallback: Use Windows API directly
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    user32.SetCursorPos(click_x, click_y)
                    
                    MOUSEEVENTF_LEFTDOWN = 0x0002
                    MOUSEEVENTF_LEFTUP = 0x0004
                    
                    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(0.01)
                    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    time.sleep(0.01)
                except Exception as e:
                    debug_log(LogCategory.ERROR, f"Mouse operation failed: {e}")
                
        elif action_type == 1:  # Stable left tracking
            if is_virtual_mouse_available():
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Ensure mouse up first
                time.sleep(duration_factor)      # Wait duration
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Mouse down for counter-strafe
                time.sleep(counter_strafe)       # Counter-strafe duration
            elif PYAUTOGUI_AVAILABLE and pyautogui is not None:
                pyautogui.mouseUp(click_x, click_y, button='left')
                time.sleep(duration_factor)
                pyautogui.mouseDown(click_x, click_y, button='left')
                time.sleep(counter_strafe)
                
        elif action_type == 2:  # Stable right tracking  
            if is_virtual_mouse_available():
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Mouse down first
                time.sleep(duration_factor)      # Wait duration
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Mouse up for counter-strafe
                time.sleep(counter_strafe)       # Counter-strafe duration
            elif PYAUTOGUI_AVAILABLE and pyautogui is not None:
                pyautogui.mouseDown(click_x, click_y, button='left')
                time.sleep(duration_factor)
                pyautogui.mouseUp(click_x, click_y, button='left')
                time.sleep(counter_strafe)
                
        elif action_type == 3:  # Max left boundary
            if is_virtual_mouse_available():
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Force mouse up (move left)
                time.sleep(duration_factor)      # Side delay
            elif PYAUTOGUI_AVAILABLE and pyautogui is not None:
                pyautogui.mouseUp(click_x, click_y, button='left')
                time.sleep(duration_factor)
                
        elif action_type == 4:  # Max right boundary
            if is_virtual_mouse_available():
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Force mouse down (move right)
                time.sleep(duration_factor)      # Side delay
            elif PYAUTOGUI_AVAILABLE and pyautogui is not None:
                pyautogui.mouseDown(click_x, click_y, button='left')
                time.sleep(duration_factor)
                
        elif action_type == 5:  # Unstable left (aggressive)
            if is_virtual_mouse_available():
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Mouse up first
                time.sleep(duration_factor)      # Aggressive duration
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Mouse down for counter-strafe
                time.sleep(counter_strafe)       # Counter-strafe duration
            elif PYAUTOGUI_AVAILABLE and pyautogui is not None:
                pyautogui.mouseUp(click_x, click_y, button='left')
                time.sleep(duration_factor)
                pyautogui.mouseDown(click_x, click_y, button='left') 
                time.sleep(counter_strafe)
                
        elif action_type == 6:  # Unstable right (aggressive)
            if is_virtual_mouse_available():
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Mouse down first
                time.sleep(duration_factor)      # Aggressive duration
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Mouse up for counter-strafe
                time.sleep(counter_strafe)       # Counter-strafe duration
            elif PYAUTOGUI_AVAILABLE and pyautogui is not None:
                pyautogui.mouseDown(click_x, click_y, button='left')
                time.sleep(duration_factor)
                pyautogui.mouseUp(click_x, click_y, button='left')
                time.sleep(counter_strafe)
                
    except Exception as e:
        pass


def initialize_camera_setup():
    """
    One-time camera setup for optimal fishing view.
    Moves mouse to center, adjusts camera angle, and sets zoom level.
    """
    print("🎥 [CAMERA SETUP] Initializing optimal fishing camera view...")
    
    # Ensure we have virtual mouse available
    if not is_virtual_mouse_available():
        print("⚠️ [CAMERA SETUP] Virtual mouse not available, skipping camera setup")
        return False
    
    # Get Roblox window center coordinates
    target_x, target_y = get_roblox_coordinates()
    if target_x is None or target_y is None:
        print("⚠️ [CAMERA SETUP] Could not get Roblox coordinates, skipping camera setup")
        return False
    
    try:
        # Phase 1: Move to center of screen for camera adjustment
        print("🎥 [CAMERA SETUP] Moving to screen center for camera adjustment...")
        center_x, center_y = target_x, target_y  # Use Roblox window center
        
        # Natural movement to center
        current_pos = virtual_mouse.get_cursor_pos()
        if current_pos:
            virtual_mouse.human_like_move(current_pos[0], current_pos[1], center_x, center_y, 
                                        random.uniform(0.5, 0.8))
        else:
            virtual_mouse.move_to(center_x, center_y)
        
        time.sleep(random.uniform(0.3, 0.5))  # Human-like pause
        
        # Phase 2: Right-click and drag down for camera angle
        print("🎥 [CAMERA SETUP] Adjusting camera angle (right-click drag)...")
        
        # Calculate drag end position (600 pixels down)
        drag_end_x = center_x + random.randint(-20, 20)  # Slight horizontal variation
        drag_end_y = center_y + 600 + random.randint(-30, 30)  # 600 pixels down with variation
        
        # Ensure end position is valid
        if WINDOW_MANAGER_AVAILABLE:
            roblox_region = get_roblox_window_region()
            if roblox_region:
                max_y = roblox_region[1] + roblox_region[3] - 50  # Window bottom minus margin
                drag_end_y = min(drag_end_y, max_y)
        
        # Enhanced right-click drag for camera adjustment
        print(f"🎥 [CAMERA SETUP] Dragging from ({center_x}, {center_y}) to ({drag_end_x}, {drag_end_y})")
        
        # Right mouse down
        virtual_mouse.mouse_down(center_x, center_y, 'right')
        time.sleep(random.uniform(0.1, 0.2))  # Brief hold before drag
        
        # Smooth drag movement
        virtual_mouse.human_like_move(center_x, center_y, drag_end_x, drag_end_y, 
                                    random.uniform(0.8, 1.2))
        
        # Right mouse up
        virtual_mouse.mouse_up(drag_end_x, drag_end_y, 'right')
        time.sleep(random.uniform(0.5, 0.8))  # Pause after camera adjustment
        
        # Phase 3: Zoom in with 'I' key (45 times at 0.01s intervals)
        print("🎥 [CAMERA SETUP] Zooming in (pressing 'I' 45 times)...")
        
        if VIRTUAL_KEYBOARD_AVAILABLE and virtual_keyboard is not None:
            for i in range(45):
                virtual_keyboard.key_press('i', duration=0.005)  # Very short press duration
                time.sleep(0.01)  # Exact 0.01s interval as requested
                if i % 15 == 0:  # Progress indicator every 15 presses
                    print(f"🎥 [CAMERA SETUP] Zoom progress: {i+1}/45")
        else:
            print("⚠️ [CAMERA SETUP] Virtual keyboard not available, skipping zoom in")
        
        time.sleep(random.uniform(0.3, 0.5))  # Pause between zoom in and out
        
        # Phase 4: Zoom out with 'O' key (3 times)
        print("🎥 [CAMERA SETUP] Fine-tuning zoom (pressing 'O' 3 times)...")
        
        if VIRTUAL_KEYBOARD_AVAILABLE and virtual_keyboard is not None:
            for i in range(3):
                virtual_keyboard.key_press('o', duration=0.05)  # Normal press duration
                time.sleep(random.uniform(0.15, 0.25))  # Slightly longer interval for zoom out
        else:
            print("⚠️ [CAMERA SETUP] Virtual keyboard not available, skipping zoom out")
        
        time.sleep(random.uniform(0.5, 1.0))  # Final pause
        
        print("✅ [CAMERA SETUP] Camera initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ [CAMERA SETUP] Camera setup failed: {e}")
        return False


# Camera initialization flag - ensures camera setup only runs once per script session
camera_initialized = False

def main_fishing_loop():
    """Main fishing automation loop."""
    global camera_initialized  # Use the module-level flag
    
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
            
            # Adjusted boundaries for middle-focused gameplay (fish rarely goes to corners)
            minigame_config.max_left_bar = 0.10   # 10% from left edge (less restrictive)
            minigame_config.max_right_bar = 0.90  # 90% from left edge (10% from right)
            
            # Middle-focused gameplay adjustments
            minigame_config.deadzone = 0.03       # Smaller deadzone for more responsive middle tracking
            minigame_config.deadzone2 = 0.12      # Adjusted for better middle-area stable tracking
            
            # Enhanced middle-area tracking parameters
            minigame_config.stable_left_multiplier = 1.4    # Slightly more responsive left tracking
            minigame_config.stable_right_multiplier = 2.1   # Balanced right tracking for middle play
            minigame_config.stable_left_division = 1.2      # Fine-tuned for smoother middle tracking
            minigame_config.stable_right_division = 1.4     # Optimized for middle-area responsiveness
            
            # Reduced unstable action intensity for middle-focused gameplay
            minigame_config.unstable_left_multiplier = 1.8   # Less aggressive (was 2.19)
            minigame_config.unstable_right_multiplier = 2.2  # Less aggressive (was 2.665)
            minigame_config.unstable_left_division = 1.1     # Smoother unstable left
            minigame_config.unstable_right_division = 1.3    # Smoother unstable right
            
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
            # Camera Setup - Run once at the beginning when Roblox is confirmed active
            if not camera_initialized:
                # First validate that Roblox is active before camera setup
                if ISROBLOX_OPEN_AVAILABLE and IsRobloxOpen and IsRobloxOpen.validate_roblox_and_game():
                    print("🎮 Roblox confirmed active - starting one-time camera setup...")
                    camera_setup_success = initialize_camera_setup()
                    camera_initialized = True  # Mark as initialized regardless of success to prevent spam
                    
                    if camera_setup_success:
                        print("✅ Camera setup completed - beginning fishing automation...")
                    else:
                        print("⚠️ Camera setup had issues - continuing with fishing anyway...")
                    
                    time.sleep(1.0)  # Brief pause before starting main fishing logic
                else:
                    print("🔄 Waiting for Roblox to be active for camera setup...")
                    time.sleep(2.0)
                    continue
            
            # Validate Roblox periodically (not every loop to reduce debug spam)
            # Skip validation during minigame to prevent interruptions
            current_time = time.time()
            if (current_time - last_validation_time > validation_interval and 
                fishing_state != "minigame"):  # Don't interrupt minigame with validation
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
                if is_virtual_mouse_available():
                    virtual_mouse.move_to(center_x, center_y)
                else:
                    smooth_move_to(center_x, center_y)
                
                time.sleep(0.5)  # Brief pause after mouse movement
                
                # Re-check rod status after moving mouse to center to prevent EQ/UN loop
                print("🔍 Re-checking rod status after centering mouse...")
                verification_result = FishingRodDetector.check_region_and_act()
                if verification_result is False:  # EQ confirmed
                    print("✅ Rod status confirmed: EQ (equipped)")
                    fishing_state = "casting"
                elif verification_result is True:  # UN detected again
                    print("⚠️ Rod reverted to UN after centering - will retry")
                    fishing_state = "waiting"
                    last_rod_click_time = current_time - rod_click_cooldown  # Reset cooldown
                else:
                    print("❓ Rod status unclear after centering - assuming equipped")
                    fishing_state = "casting"
                
                time.sleep(0.3)  # Additional brief pause before continuing
                
            elif rod_result is False:  # EQ (equipped) detected - rod is ready
                if fishing_state == "waiting" or fishing_state == "equipping":
                    print("✅ Rod equipped - preparing for casting")
                    
                    # Get center coordinates for mouse positioning
                    center_x, center_y = get_roblox_coordinates()
                    if center_x is None or center_y is None:
                        # Fallback to screen center
                        screen_w, screen_h = get_screen_size()
                        center_x, center_y = screen_w // 2, screen_h // 2
                    
                    # Move mouse to center before switching to casting state
                    if is_virtual_mouse_available():
                        virtual_mouse.move_to(center_x, center_y)
                    else:
                        smooth_move_to(center_x, center_y)
                    
                    time.sleep(0.3)  # Brief pause after mouse movement
                    
                    # Re-check rod status after moving mouse to prevent state confusion
                    verification_result = FishingRodDetector.check_region_and_act()
                    if verification_result is False:  # EQ still confirmed
                        print("✅ Rod status verified: EQ (equipped) - switching to casting")
                        fishing_state = "casting"
                        cast_attempts = 0
                    elif verification_result is True:  # UN detected after movement
                        print("⚠️ Rod became unequipped after mouse movement - resetting")
                        fishing_state = "waiting"
                        last_rod_click_time = current_time - rod_click_cooldown  # Reset cooldown
                    else:
                        print("❓ Rod status unclear - assuming equipped and proceeding")
                        fishing_state = "casting"
                        cast_attempts = 0
                        
                    time.sleep(0.2)  # Additional brief pause
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
                    screen_w, screen_h = get_screen_size()
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
                

                # Check for fish on hook with enhanced verification
                fish_detected = Fish_On_Hook(0, 0)  # This now only detects, doesn't click
                
                if fish_detected:
                    print(f"🐟 FISH DETECTED! Verifying with template matching...")
                    # Additional verification using strict template matching
                    time.sleep(0.2)  # Brief pause for stability
                    
                    # Double-check with template matching to avoid false positives
                    verification_passed = _verify_fish_on_hook_template()
                    
                    if verification_passed:
                        print(f"✅ FISH VERIFIED! Starting minigame...")
                        # Start the minigame manually with proper clicking
                        minigame_started = _start_minigame_clicks()
                        
                        if minigame_started:
                            print(f"🎮 Minigame started successfully!")
                            time.sleep(1.0)  # Wait for minigame UI to load
                            fishing_state = "minigame"
                            minigame_start_time = time.time()
                        else:
                            print(f"❌ Failed to start minigame, continuing to wait...")
                    else:
                        print(f"⚠️ Fish detection not verified by template matching - likely false positive")
                        # Continue waiting instead of starting minigame
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
                
                # Debug: Show exactly why minigame is ending
                current_time = time.time()
                minigame_duration = current_time - minigame_start_time
                timeout_reached = minigame_duration > 45  # Extended to 45 seconds for complex fishing sequences
                
                if minigame_result:
                    print(f"🔍 [DEBUG] Minigame ending due to handler returning True (duration: {minigame_duration:.1f}s)")
                elif timeout_reached:
                    print(f"🔍 [DEBUG] Minigame ending due to 45s timeout (duration: {minigame_duration:.1f}s)")
                
                if minigame_result or timeout_reached:
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
