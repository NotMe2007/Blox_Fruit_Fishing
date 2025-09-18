import cv2
import pyautogui
import numpy as np
import sys
import time
import random
import math
import win32gui
from pathlib import Path

# Import virtual mouse driver
virtual_mouse = None
VIRTUAL_MOUSE_AVAILABLE = False

try:
    # Try relative import first (when imported as package)
    from .VirtualMouse import VirtualMouse
    virtual_mouse = VirtualMouse()
    VIRTUAL_MOUSE_AVAILABLE = True
except ImportError:
    try:
        # Add current directory to path and try absolute import
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        from VirtualMouse import VirtualMouse
        virtual_mouse = VirtualMouse()
        VIRTUAL_MOUSE_AVAILABLE = True
    except ImportError:
        virtual_mouse = None
        VIRTUAL_MOUSE_AVAILABLE = False

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

# Config
# Templates live in the Images/ folder relative to the project root
IMAGES_DIR = Path(__file__).parent.parent.parent / 'Images'
UN_PATH = IMAGES_DIR / 'Basic_Fishing_UN.png'
EQ_PATH = IMAGES_DIR / 'Basic_Fishing_EQ.png'
# Region to check: top-left and bottom-right (inclusive)
TOP_LEFT = (725, 1004)
BOTTOM_RIGHT = (1189, 1072)
threshold = 0.55   # matching threshold (0-1). Lower to be more permissive
debug = False      # set True to print info and save debug image


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
    # Quick validation - check if Roblox window is in foreground
    try:
        foreground_hwnd = win32gui.GetForegroundWindow()
        foreground_title = win32gui.GetWindowText(foreground_hwnd).lower()
        
        if 'roblox' not in foreground_title:
            print("WARNING: Roblox is not in foreground. Skipping rod detection.")
            return None
    except Exception as e:
        print(f"Error checking foreground window: {e}")
        return None
    
    try:
        un_gray, eq_gray = load_templates()
    except Exception as e:
        print(f"Error loading templates: {e}")
        return None

    try:
        left = max(0, TOP_LEFT[0])
        top = max(0, TOP_LEFT[1])
        screen_w, screen_h = pyautogui.size()
        right = min(screen_w, BOTTOM_RIGHT[0])
        bottom = min(screen_h, BOTTOM_RIGHT[1])
        w = max(1, right - left)
        h = max(1, bottom - top)
        region = (left, top, w, h)

        time.sleep(0.05)
        pil_img = pyautogui.screenshot(region=region)
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
        dbg_path = 'debug_region.png'
        cv2.imwrite(dbg_path, dbg)
        print(f'Saved debug image: {dbg_path}')

    # Decide - ensure all values are scalar
    best_un_val_scalar = float(best_un_val) if best_un_val is not None else -1.0
    best_eq_val_scalar = float(best_eq_val) if best_eq_val is not None else -1.0
    
    if (best_un_loc is not None and best_un_size is not None and 
        best_un_val_scalar >= threshold and best_un_val_scalar > best_eq_val_scalar):
        tw, th = best_un_size
        click_x = left + int(best_un_loc[0]) + tw // 2
        click_y = top + int(best_un_loc[1]) + th // 2
        
        print(f'UN rod detected at ({click_x}, {click_y}) - score={best_un_val_scalar:.3f}')
        
        # Use virtual mouse driver for undetectable input
        if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
            print("Using virtual mouse driver for hardware-level input")
            success = virtual_mouse.human_click(click_x, click_y)
            if success:
                print(f'Virtual mouse click performed at ({click_x}, {click_y})')
                return True
            else:
                print("Virtual mouse click failed, falling back to pyautogui")
        
        # Fallback to regular mouse if virtual mouse fails
        print("Using fallback pyautogui input")
        offset_x = random.randint(-2, 2)
        offset_y = random.randint(-2, 2)
        final_x = click_x + offset_x
        final_y = click_y + offset_y
        
        smooth_move_to(final_x, final_y)
        time.sleep(random.uniform(0.05, 0.15))
        
        # Super human-like click with varied patterns
        click_type = random.randint(1, 3)
        
        if click_type == 1:
            # Quick single click
            duration = random.uniform(0.04, 0.08)
            pyautogui.mouseDown(final_x, final_y, button='left')
            time.sleep(duration)
            pyautogui.mouseUp(final_x, final_y, button='left')
            
        elif click_type == 2:
            # Double click (sometimes humans do this accidentally)
            duration1 = random.uniform(0.03, 0.06)
            pyautogui.mouseDown(final_x, final_y, button='left')
            time.sleep(duration1)
            pyautogui.mouseUp(final_x, final_y, button='left')
            
            time.sleep(random.uniform(0.02, 0.05))  # Brief pause
            
            duration2 = random.uniform(0.03, 0.06)
            pyautogui.mouseDown(final_x, final_y, button='left')
            time.sleep(duration2)
            pyautogui.mouseUp(final_x, final_y, button='left')
            
        else:
            # Click with slight hold
            duration = random.uniform(0.08, 0.15)
            pyautogui.mouseDown(final_x, final_y, button='left')
            time.sleep(duration)
            pyautogui.mouseUp(final_x, final_y, button='left')
        
        print(f'Human-like click performed at ({final_x}, {final_y}) pattern: {click_type}')
        
        # Random pause after click to simulate human behavior
        time.sleep(random.uniform(0.15, 0.4))
        return True

    if (best_eq_loc is not None and best_eq_size is not None and 
        best_eq_val_scalar >= threshold and best_eq_val_scalar > best_un_val_scalar):
        print(f'EQ detected in region - Ending script (score={best_eq_val_scalar:.3f})')
        return False

    print('No UN or EQ detected in the region')
    return None


# Load templates that are expected by Fishing_Script.py
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
    FISH_ON_HOOK_TPL = safe_load_template(IMAGES_DIR / 'Fish_On_Hook.jpg')
    FISH_LEFT_TPL = safe_load_template(IMAGES_DIR / 'Fish_Left.png')
    FISH_RIGHT_TPL = safe_load_template(IMAGES_DIR / 'Fish_Right.png')
    SHIFT_LOCK_TPL = safe_load_template(IMAGES_DIR / 'Shift_Lock.png')
    POWER_MAX_TPL = safe_load_template(IMAGES_DIR / 'Power_Max.png')
    POWER_ACTIVE_TPL = safe_load_template(IMAGES_DIR / 'Power_Active.png')
except Exception as e:
    print(f"Warning: Could not load some template images: {e}")
    FISH_ON_HOOK_TPL = None
    FISH_LEFT_TPL = None
    FISH_RIGHT_TPL = None
    SHIFT_LOCK_TPL = None
    POWER_MAX_TPL = None
    POWER_ACTIVE_TPL = None


if __name__ == '__main__':
    res = check_region_and_act()
    if res is False:
        sys.exit(0)
