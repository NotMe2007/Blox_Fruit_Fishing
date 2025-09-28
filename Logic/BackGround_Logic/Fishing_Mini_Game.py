"""
Fishing minigame logic ported from FischV12.ahk

This module implements the AHK fishing minigame logic with 6 action types:
0 = stabilize (rapid clicking for minor correction)
1 = stable left tracking (moderate left movement with counter-strafe)
2 = stable right tracking (moderate right movement with counter-strafe)  
3 = max left boundary (indicator too far right, strong left correction)
4 = max right boundary (indicator too far left, strong right correction)
5 = unstable left (aggressive left movement for unstable conditions)
6 = unstable right (aggressive right movement for unstable conditions)

Contract:
- Inputs: minigame state (indicator position, arrow direction, stable state)
- Outputs: action dict with type, intensity, duration, and counter-strafe values

Usage:
    cfg = MinigameConfig()
    controller = MinigameController(cfg)
    decision = controller.decide(indicator=0.82, arrow='right', stable=False)
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict
import cv2
import numpy as np
# PyAutoGUI removed to avoid detection - using Windows API only
import time
import random
from pathlib import Path

# Import centralized debug logger
try:
    from .Debug_Logger import debug_log, LogCategory
    DEBUG_LOGGER_AVAILABLE = True
except ImportError:
    try:
        from Debug_Logger import debug_log, LogCategory
        DEBUG_LOGGER_AVAILABLE = True
    except ImportError:
        DEBUG_LOGGER_AVAILABLE = False
        # Fallback log categories
        from enum import Enum
        class LogCategory(Enum):
            SYSTEM = "SYSTEM"
            MINIGAME_DECISIONS = "MINIGAME_DECISIONS"
            MINIGAME_DETECTION = "MINIGAME_DETECTION"
            FISH_DETECTION = "FISH_DETECTION"
            TEMPLATE_MATCHING = "TEMPLATE_MATCHING"
            MOUSE_INPUT = "MOUSE_INPUT"
            ERROR = "ERROR"
        def debug_log(category, message):
            print(f"[{category.value}] {message}")

# Import virtual mouse driver
virtual_mouse = None
VIRTUAL_MOUSE_AVAILABLE = False

# Minigame detection failure counter
_minigame_detection_failures = 0

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

# Import window manager for proper Roblox window handling
try:
    # Try relative import first (when imported as package)  
    from .WindowManager import get_roblox_coordinates, ensure_roblox_focused
    WINDOW_MANAGER_AVAILABLE = True
except ImportError:
    try:
        # Add current directory to path and try absolute import
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        from WindowManager import get_roblox_coordinates, ensure_roblox_focused
        WINDOW_MANAGER_AVAILABLE = True
    except ImportError:
        WINDOW_MANAGER_AVAILABLE = False
        # Define dummy functions for fallback
        def get_roblox_coordinates():
            return None, None
        def ensure_roblox_focused():
            return False

# Load minigame templates from Images directory
IMAGES_DIR = Path(__file__).parent.parent.parent / 'Images'

def safe_load_template(path):
    """Load template image safely."""
    try:
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is not None and img.size > 0:
            return img
        else:
            print(f"❌ Template failed to load: {path.name}")
    except Exception as e:
        print(f"❌ Template loading error: {path.name} - {e}")
    return None

def safe_load_template_gray(path):
    """Load template as grayscale safely."""
    try:
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is not None and img.size > 0:
            return img
        else:
            print(f"❌ Template failed to load: {path.name}")
    except Exception as e:
        print(f"❌ Template loading error: {path.name} - {e}")
    return None

# Load minigame templates (AHK equivalent of image detection)
try:
    MINIGAME_BAR_TPL = safe_load_template_gray(IMAGES_DIR / 'MiniGame_Bar.png')
    FISH_LEFT_TPL = safe_load_template(IMAGES_DIR / 'Fish_Left.png')
    FISH_RIGHT_TPL = safe_load_template(IMAGES_DIR / 'Fish_Right.png')
    
    # Print template status
    templates = [
        ("MiniGame_Bar.png", MINIGAME_BAR_TPL),
        ("Fish_Left.png", FISH_LEFT_TPL),
        ("Fish_Right.png", FISH_RIGHT_TPL)
    ]
    
    for name, template in templates:
        if template is not None:
            if len(template.shape) == 3:
                shape_str = f"{template.shape[0]}x{template.shape[1]}x{template.shape[2]}"
            else:
                shape_str = f"{template.shape[0]}x{template.shape[1]}"
            debug_log(LogCategory.TEMPLATE_MATCHING, f"Template loaded: {name} (shape: {shape_str})")
        else:
            debug_log(LogCategory.ERROR, f"Template failed to load: {name}")
            
except Exception as e:
    print(f"Warning: Could not load minigame template images: {e}")
    MINIGAME_BAR_TPL = None
    FISH_LEFT_TPL = None  
    FISH_RIGHT_TPL = None


@dataclass
class MinigameConfig:
    # Control stat from fishing rod (Check the Control stat of your Rod!)
    control: float = 0.0  
    
    # Color detection tolerances (AHK: FishBarColorTolerance, WhiteBarColorTolerance, ArrowColorTolerance)
    fish_bar_color_tolerance: int = 5  
    white_bar_color_tolerance: int = 15  
    arrow_color_tolerance: int = 6  
    
    # Tolerances (normalized units)
    fish_bar_half_width: float = 0.12  
    white_bar_half_width: float = 0.03  

    # Scanning delay (AHK: ScanDelay)
    scan_delay: float = 0.01  
    
    # Dynamic fish center position
    fish_center: float = 0.5  
    last_known_fish_pos: float = 0.5  

    # Side bar ratio and delay (AHK: SideBarRatio, SideDelay)
    side_bar_ratio: float = 0.7  
    side_delay: float = 0.4  

    # Stable multipliers/divisions (AHK: StableRightMultiplier, StableRightDivision, etc.)
    stable_right_multiplier: float = 2.36
    stable_right_division: float = 1.55
    stable_left_multiplier: float = 1.211
    stable_left_division: float = 1.12

    # Unstable multipliers/divisions (AHK: UnstableRightMultiplier, UnstableRightDivision, etc.)
    unstable_right_multiplier: float = 2.665  
    unstable_right_division: float = 1.5
    unstable_left_multiplier: float = 2.19   
    unstable_left_division: float = 1.0

    # Ankle-break multipliers (AHK: RightAnkleBreakMultiplier, LeftAnkleBreakMultiplier)
    right_ankle_break_multiplier: float = 0.75
    left_ankle_break_multiplier: float = 0.45

    # Pixel scaling and deadzone calculations
    pixel_scaling: float = 1.0  
    deadzone: float = 0.05      
    deadzone2: float = 0.15     
    
    # Boundary calculations (AHK: MaxLeftBar, MaxRightBar)
    max_left_bar: float = 0.25   
    max_right_bar: float = 0.75  

    # Action intensity limits
    min_intensity: float = 0.15  
    max_intensity: float = 1.5


class MinigameController:
    def __init__(self, cfg: Optional[MinigameConfig] = None):
        self.cfg = cfg or MinigameConfig()

    def _clamp01(self, v: float) -> float:
        if v is None:
            return 0.0
        return max(0.0, min(1.0, v))

    def _compute_target(self) -> float:
        # The fish bar position
        return self.cfg.fish_center

    def _inside_fish_bar(self, indicator: float) -> bool:
        target = self._compute_target()
        half = self.cfg.fish_bar_half_width
        return (target - half) <= indicator <= (target + half)

    def decide(self, indicator: float, arrow: Optional[str] = None, stable: bool = True,
               delta_time: Optional[float] = None) -> Dict:
        """
        AHK minigame decision logic with 6 action types:
        
        Action 0 = stabilize (rapid clicking for minor correction)
        Action 1 = stable left tracking (moderate left with counter-strafe)
        Action 2 = stable right tracking (moderate right with counter-strafe)
        Action 3 = max left boundary (strong left correction)
        Action 4 = max right boundary (strong right correction)
        Action 5 = unstable left (aggressive left movement)
        Action 6 = unstable right (aggressive right movement)

        Returns: {action, intensity, note, action_type, duration_factor}
        """
        indicator = self._clamp01(indicator)
        fish_center = self._compute_target()
        
        # Calculate direction from indicator to fish center
        direction = fish_center - indicator  
        distance_factor = abs(direction) / self.cfg.white_bar_half_width
        
        print(f"🎯 Indicator: {indicator:.3f}, Fish: {fish_center:.3f}, Direction: {direction:.3f} ({'RIGHT' if direction > 0 else 'LEFT' if direction < 0 else 'CENTER'})")
        debug_log(LogCategory.COORDINATES, f"Indicator: {indicator:.3f}, Fish: {fish_center:.3f}, Direction: {direction:.3f} ({'RIGHT' if direction > 0 else 'LEFT' if direction < 0 else 'CENTER'})")
        
        print(f"🔧 Config boundaries: left={self.cfg.max_left_bar}, right={self.cfg.max_right_bar}")
        debug_log(LogCategory.DEBUG, f"Config boundaries: left={self.cfg.max_left_bar}, right={self.cfg.max_right_bar}")
        
        # Check boundary conditions (Action 3 & 4)
        if indicator < self.cfg.max_left_bar:
            # Max right boundary action
            print(f"🚨 BOUNDARY: Indicator too far LEFT ({indicator:.3f} < {self.cfg.max_left_bar})")
            debug_log(LogCategory.MINIGAME, f"BOUNDARY: Indicator too far LEFT ({indicator:.3f} < {self.cfg.max_left_bar})")
            return {
                "action": "move_right", 
                "intensity": 1.1, 
                "note": "max_right_boundary",
                "action_type": 4,
                "duration_factor": self.cfg.side_delay
            }
        elif indicator > self.cfg.max_right_bar:
            # Max left boundary action
            print(f"🚨 BOUNDARY: Indicator too far RIGHT ({indicator:.3f} > {self.cfg.max_right_bar})")
            debug_log(LogCategory.MINIGAME, f"BOUNDARY: Indicator too far RIGHT ({indicator:.3f} > {self.cfg.max_right_bar})")
            return {
                "action": "move_left", 
                "intensity": 0.9, 
                "note": "max_left_boundary", 
                "action_type": 3,
                "duration_factor": self.cfg.side_delay
            }
        
        # Normal tracking logic based on deadzone thresholds
        if abs(direction) <= self.cfg.deadzone:
            # Action 0: Stabilize
            return {
                "action": "stabilize",
                "intensity": 0.8,  
                "note": "stabilizing",
                "action_type": 0,
                "duration_factor": 0.178,  
                "click_interval": 0.178,  
                "stabilize_duration": 1.0  
            }
            
        elif self.cfg.deadzone < abs(direction) <= self.cfg.deadzone2:
            # Actions 1 & 2: Stable tracking
            if direction < 0:  # Action 1: Stable left
                intensity = abs(direction) * self.cfg.stable_left_multiplier * self.cfg.pixel_scaling
                adaptive_duration = 0.5 + 0.5 * (distance_factor ** 1.2)
                if distance_factor < 0.2:
                    adaptive_duration = 0.15 + 0.15 * distance_factor
                
                print(f"🎯 STABLE LEFT: moving left to reach fish (direction: {direction:.3f})")
                debug_log(LogCategory.MINIGAME, f"STABLE LEFT: moving left to reach fish (direction: {direction:.3f})")
                return {
                    "action": "move_left",
                    "intensity": min(intensity, self.cfg.max_intensity),
                    "note": "stable_left_tracking",
                    "action_type": 1,
                    "duration_factor": adaptive_duration,
                    "counter_strafe": adaptive_duration / self.cfg.stable_left_division
                }
            else:  # Action 2: Stable right
                intensity = abs(direction) * self.cfg.stable_right_multiplier * self.cfg.pixel_scaling
                adaptive_duration = 0.5 + 0.5 * (distance_factor ** 1.2)
                if distance_factor < 0.2:
                    adaptive_duration = 0.15 + 0.15 * distance_factor
                
                print(f"🎯 STABLE RIGHT: moving right to reach fish (direction: {direction:.3f})")
                debug_log(LogCategory.MINIGAME, f"STABLE RIGHT: moving right to reach fish (direction: {direction:.3f})")
                return {
                    "action": "move_right",
                    "intensity": min(intensity, self.cfg.max_intensity),
                    "note": "stable_right_tracking",
                    "action_type": 2,
                    "duration_factor": adaptive_duration,
                    "counter_strafe": adaptive_duration / self.cfg.stable_right_division
                }
                
        else:  # abs(direction) > deadzone2
            # Actions 5 & 6: Unstable/aggressive tracking
            if direction < 0:  # Action 5: Unstable left
                # Calculate max duration based on Control stat
                min_duration = 0.01
                base_duration = abs(direction) * 2.0  
                if self.cfg.control >= 0.25:
                    max_duration = base_duration * 0.75
                elif self.cfg.control >= 0.2:
                    max_duration = base_duration * 0.8
                elif self.cfg.control >= 0.15:
                    max_duration = base_duration * 0.88
                else:
                    max_duration = base_duration + (abs(direction) * 0.2)
                
                raw_duration = abs(direction) * self.cfg.unstable_left_multiplier * self.cfg.pixel_scaling
                duration = max(min_duration, min(raw_duration, max_duration))
                
                print(f"🚀 UNSTABLE LEFT: aggressive left movement (direction: {direction:.3f})")
                return {
                    "action": "move_left",
                    "intensity": min(1.0, raw_duration),
                    "note": "unstable_left_aggressive", 
                    "action_type": 5,
                    "duration_factor": duration,
                    "counter_strafe": duration / self.cfg.unstable_left_division
                }
            else:  # Action 6: Unstable right
                # Calculate max duration based on Control stat
                min_duration = 0.01
                base_duration = abs(direction) * 2.0  
                if self.cfg.control >= 0.25:
                    max_duration = base_duration * 0.75
                elif self.cfg.control >= 0.2:
                    max_duration = base_duration * 0.8
                elif self.cfg.control >= 0.15:
                    max_duration = base_duration * 0.88
                else:
                    max_duration = base_duration + (abs(direction) * 0.2)
                    
                raw_duration = abs(direction) * self.cfg.unstable_right_multiplier * self.cfg.pixel_scaling
                duration = max(min_duration, min(raw_duration, max_duration))
                
                print(f"🚀 UNSTABLE RIGHT: aggressive right movement (direction: {direction:.3f})")
                return {
                    "action": "move_right",
                    "intensity": min(1.0, raw_duration),
                    "note": "unstable_right_aggressive",
                    "action_type": 6,
                    "duration_factor": duration,
                    "counter_strafe": duration / self.cfg.unstable_right_division
                }


# Simple step simulator for testing AHK logic
def simulate(controller: MinigameController, initial_indicator: float,
             steps: int = 50, step_dt: float = 0.05, noise: float = 0.0) -> Tuple[float, list]:
    """
    Simulate the minigame for testing purposes.
    Returns final indicator position and history of actions.
    """
    import random

    indicator = controller._clamp01(initial_indicator)
    history = []
    for i in range(steps):
        # Simulate random arrow/stable state if noise enabled
        arrow = random.choice([None, "left", "right"]) if noise > 0 else None
        stable = True if random.random() > 0.1 else False if noise > 0 else True
        decision = controller.decide(indicator=indicator, arrow=arrow, stable=stable, delta_time=step_dt)

        # Convert decision to velocity
        if decision["action"] == "none":
            velocity = 0.0
        elif decision["action"] == "move_left":
            velocity = -decision["intensity"] * 0.02  
        else:
            velocity = decision["intensity"] * 0.02

        # Environmental push
        env_push = 0.0
        if arrow == "left":
            env_push -= 0.01
        elif arrow == "right":
            env_push += 0.01

        # Update indicator
        indicator = controller._clamp01(indicator + velocity + env_push + (random.random() - 0.5) * noise)
        history.append((indicator, decision["action"], decision["intensity"]))

    return indicator, history


#======================================== MINIGAME DETECTION ========================================

def detect_minigame_elements():
    """
    Detect minigame UI elements in the fishing bar region.
    Returns: indicator_pos, fish_pos, minigame_active
    """
    try:
        # Updated minigame bar coordinates based on user-provided debug screenshot analysis
        # Precise region targeting the actual minigame bar: (498, 789) to (1465, 840)
        # This much smaller region (967x51) avoids false positives from casting bars
        # and focuses detection on the exact minigame UI area
        minigame_left = 498   # Left edge of minigame bar
        minigame_top = 789    # Top edge of minigame bar  
        minigame_right = 1465 # Right edge of minigame bar
        minigame_bottom = 840 # Bottom edge of minigame bar
        minigame_width = minigame_right - minigame_left  # 967 width
        minigame_height = minigame_bottom - minigame_top # 51 height
        
        # Take screenshot of the specific minigame region using Windows API
        minigame_region = (minigame_left, minigame_top, minigame_width, minigame_height)
        
        # Use Windows API for screenshot to avoid PyAutoGUI detection
        try:
            import win32gui
            import win32ui
            import win32con
            from PIL import Image
            
            # Get desktop DC
            hdesktop = win32gui.GetDesktopWindow()
            desktop_dc = win32gui.GetWindowDC(hdesktop)
            img_dc = win32ui.CreateDCFromHandle(desktop_dc)
            mem_dc = img_dc.CreateCompatibleDC()
            
            # Create bitmap
            screenshot_bmp = win32ui.CreateBitmap()
            screenshot_bmp.CreateCompatibleBitmap(img_dc, minigame_width, minigame_height)
            mem_dc.SelectObject(screenshot_bmp)
            
            # Copy screen region to bitmap
            mem_dc.BitBlt((0, 0), (minigame_width, minigame_height), img_dc, (minigame_left, minigame_top), win32con.SRCCOPY)
            
            # Convert to PIL Image
            bmpinfo = screenshot_bmp.GetInfo()
            bmpstr = screenshot_bmp.GetBitmapBits(True)
            screenshot = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)
            
            # Cleanup
            mem_dc.DeleteDC()
            win32gui.DeleteObject(screenshot_bmp.GetHandle())
            win32gui.ReleaseDC(hdesktop, desktop_dc)
            
        except ImportError:
            print("⚠️ win32gui not available, using cv2 screenshot fallback")
            # Fallback to cv2 if win32gui not available
            import mss
            with mss.mss() as sct:
                monitor = {"top": minigame_top, "left": minigame_left, "width": minigame_width, "height": minigame_height}
                screenshot = Image.fromarray(np.array(sct.grab(monitor))[:,:,:3])  # Remove alpha channel
        except Exception as e:
            print(f"⚠️ Windows API screenshot failed: {e}")
            # Final fallback - try MSS library
            try:
                import mss
                with mss.mss() as sct:
                    monitor = {"top": minigame_top, "left": minigame_left, "width": minigame_width, "height": minigame_height}
                    screenshot = Image.fromarray(np.array(sct.grab(monitor))[:,:,:3])  # Remove alpha channel
            except ImportError:
                print("❌ No screenshot method available - install win32gui or mss")
                return {"minigame_active": False, "indicator_pos": 0.5, "fish_pos": 0.5}
        
        screenshot_np = np.array(screenshot)
        
        # Convert to BGR for OpenCV
        screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
        
        print(f"🎯 Scanning minigame region: {minigame_region} ({minigame_width}x{minigame_height})")
        debug_log(LogCategory.COORDINATES, f"Minigame region: {minigame_region} ({minigame_width}x{minigame_height})")
        
        # Detect fish position using image-based detection in the cropped region
        fish_pos = detect_fish_position_image_based(screenshot_bgr)
        
        # Detect white indicator position using image-based detection
        indicator_pos = detect_white_indicator_image_based(screenshot_bgr)
        
        # Check if minigame is active using enhanced detection (strict mode since we're in minigame state)
        minigame_active = detect_minigame_bar_presence(screenshot_bgr, require_fish_indicators=True)
        
        # If elements detected but no bar, still consider active if we found elements
        if not minigame_active and (fish_pos is not None or indicator_pos is not None):
            minigame_active = True
            debug_log(LogCategory.MINIGAME_DETECT, "Minigame active based on element detection despite bar detection failure")
        
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
        # Try template matching first (fastest method) using loaded templates
        if FISH_LEFT_TPL is not None and FISH_RIGHT_TPL is not None:
            # Convert to grayscale for faster matching
            gray_screenshot = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)
            gray_left = cv2.cvtColor(FISH_LEFT_TPL, cv2.COLOR_BGR2GRAY)
            gray_right = cv2.cvtColor(FISH_RIGHT_TPL, cv2.COLOR_BGR2GRAY)
            
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


def detect_minigame_bar_presence(screenshot_bgr, require_fish_indicators=True):
    """
    Detect minigame bar presence using fish indicators as the primary method.
    Fish left/right arrows are unique to the fishing minigame and provide the most reliable detection.
    
    Args:
        screenshot_bgr: The screenshot to analyze
        require_fish_indicators: If True, requires fish-specific UI elements to avoid 
                               detecting casting charge bars or other UI elements
                               
    Returns True if minigame bar is detected, False otherwise.
    """
    try:
        # Convert screenshot to grayscale for template matching
        gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)
        image_h, image_w = gray.shape
        
        # PRIMARY METHOD: Fish indicators (left/right arrows) - most reliable
        fish_indicators_found = 0
        fish_detection_confidence = 0.0
        
        print("🔍 Primary detection: Looking for fish left/right indicators...")
        
        # Check for left fish indicator
        if FISH_LEFT_TPL is not None and FISH_LEFT_TPL.size > 0:
            try:
                # Convert template to grayscale if needed
                fish_left_gray = FISH_LEFT_TPL if len(FISH_LEFT_TPL.shape) == 2 else cv2.cvtColor(FISH_LEFT_TPL, cv2.COLOR_BGR2GRAY)
                
                # Multi-scale template matching for better detection
                best_confidence = 0.0
                for scale in [1.0, 0.9, 0.8, 1.1, 1.2]:
                    if scale != 1.0:
                        template_h, template_w = fish_left_gray.shape
                        new_w = int(template_w * scale)
                        new_h = int(template_h * scale)
                        if new_w <= image_w and new_h <= image_h and new_w > 0 and new_h > 0:
                            scaled_template = cv2.resize(fish_left_gray, (new_w, new_h))
                        else:
                            continue
                    else:
                        scaled_template = fish_left_gray
                    
                    result = cv2.matchTemplate(gray, scaled_template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    best_confidence = max(best_confidence, max_val)
                    
                    if max_val > 0.6:  # Reliable threshold
                        fish_indicators_found += 1
                        fish_detection_confidence = max(fish_detection_confidence, max_val)
                        print(f"✅ Fish LEFT indicator detected! (scale={scale:.1f}, confidence: {max_val:.3f})")
                        break
                
                if best_confidence < 0.6:
                    print(f"❌ Fish left indicator: best confidence {best_confidence:.3f} < 0.6")
                    
            except Exception as e:
                print(f"Fish left template matching error: {e}")
        
        # Check for right fish indicator
        if FISH_RIGHT_TPL is not None and FISH_RIGHT_TPL.size > 0:
            try:
                # Convert template to grayscale if needed
                fish_right_gray = FISH_RIGHT_TPL if len(FISH_RIGHT_TPL.shape) == 2 else cv2.cvtColor(FISH_RIGHT_TPL, cv2.COLOR_BGR2GRAY)
                
                # Multi-scale template matching for better detection
                best_confidence = 0.0
                for scale in [1.0, 0.9, 0.8, 1.1, 1.2]:
                    if scale != 1.0:
                        template_h, template_w = fish_right_gray.shape
                        new_w = int(template_w * scale)
                        new_h = int(template_h * scale)
                        if new_w <= image_w and new_h <= image_h and new_w > 0 and new_h > 0:
                            scaled_template = cv2.resize(fish_right_gray, (new_w, new_h))
                        else:
                            continue
                    else:
                        scaled_template = fish_right_gray
                    
                    result = cv2.matchTemplate(gray, scaled_template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    best_confidence = max(best_confidence, max_val)
                    
                    if max_val > 0.6:  # Reliable threshold
                        fish_indicators_found += 1
                        fish_detection_confidence = max(fish_detection_confidence, max_val)
                        print(f"✅ Fish RIGHT indicator detected! (scale={scale:.1f}, confidence: {max_val:.3f})")
                        break
                
                if best_confidence < 0.6:
                    print(f"❌ Fish right indicator: best confidence {best_confidence:.3f} < 0.6")
                    
            except Exception as e:
                print(f"Fish right template matching error: {e}")
        
        # Primary decision based on fish indicators
        if fish_indicators_found > 0:
            print(f"🎣 ✅ FISHING MINIGAME CONFIRMED! Found {fish_indicators_found} fish indicator(s) (confidence: {fish_detection_confidence:.3f})")
            return True
        
        # If fish indicators required but not found, return False
        if require_fish_indicators:
            print("🚫 No fish indicators found - not a fishing minigame (avoiding false positive)")
            return False
        
        print("⚠️ Fish indicators not found, falling back to secondary detection methods...")
        
        # FALLBACK METHOD: Template matching with MiniGame_Bar.png (less reliable)
        template_detected = False
        if MINIGAME_BAR_TPL is not None:
            template_h, template_w = MINIGAME_BAR_TPL.shape
            
            if template_h <= image_h and template_w <= image_w:
                # Perform template matching with multiple scales
                for scale in [1.0, 0.9, 0.8, 1.1, 1.2]:
                    if scale != 1.0:
                        # Resize template
                        new_w = int(template_w * scale)
                        new_h = int(template_h * scale)
                        if new_w <= image_w and new_h <= image_h:
                            scaled_template = cv2.resize(MINIGAME_BAR_TPL, (new_w, new_h))
                        else:
                            continue
                    else:
                        scaled_template = MINIGAME_BAR_TPL
                    
                    result = cv2.matchTemplate(gray, scaled_template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    
                    if max_val >= 0.6:  # Lower threshold for more detection
                        print(f"✓ Minigame bar detected with template (scale={scale:.1f}, confidence: {max_val:.3f})")
                        template_detected = True
                        break
                
                if not template_detected:
                    print(f"❌ Template matching failed (all scales tested)")
            else:
                print(f"⚠️ Template size mismatch: template({template_w}x{template_h}) > image({image_w}x{image_h})")
        
        # Method 2: Color-based detection for minigame elements
        color_detected = False
        
        # Look for characteristic minigame colors
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2HSV)
        
        # Look for white/light elements (indicator)
        white_lower = np.array([0, 0, 200])
        white_upper = np.array([180, 30, 255])
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        white_pixels = cv2.countNonZero(white_mask)
        
        # Look for colored bar elements (green/red zones)
        colored_pixels = 0
        for color_range in [
            ([35, 50, 50], [85, 255, 255]),    # Green range
            ([0, 50, 50], [10, 255, 255]),     # Red range  
            ([170, 50, 50], [180, 255, 255])  # Red range (wrap around)
        ]:
            lower, upper = color_range
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            colored_pixels += cv2.countNonZero(mask)
        
        # Adaptive thresholds based on region size (for new precise 967x51 region)
        region_pixels = image_h * image_w
        
        # Scale thresholds based on region size - new region is smaller so lower thresholds
        if region_pixels < 60000:  # Precise minigame region
            white_threshold = 30
            colored_threshold = 50
            edge_threshold = 120
        else:  # Larger regions (backward compatibility)
            white_threshold = 50
            colored_threshold = 100
            edge_threshold = 200
        
        # If we have significant white and colored elements, likely a minigame
        if white_pixels > white_threshold and colored_pixels > colored_threshold:
            print(f"✓ Minigame detected via color analysis (white: {white_pixels}>{white_threshold}, colored: {colored_pixels}>{colored_threshold})")
            color_detected = True
        else:
            print(f"❌ Color analysis failed (white: {white_pixels}<={white_threshold}, colored: {colored_pixels}<={colored_threshold})")
        
        # Method 3: Edge detection for UI elements
        edges = cv2.Canny(gray, 50, 150)
        edge_pixels = cv2.countNonZero(edges)
        
        # FALLBACK METHOD: Color-based detection (less reliable, kept for compatibility)
        print("🔍 Fallback method: Color-based detection...")
        color_detected = False
        
        # Look for characteristic minigame colors
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2HSV)
        
        # Look for white/light elements (indicator)
        white_lower = np.array([0, 0, 200])
        white_upper = np.array([180, 30, 255])
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        white_pixels = cv2.countNonZero(white_mask)
        
        # Look for colored bar elements (green/red zones)
        colored_pixels = 0
        for color_range in [
            ([35, 50, 50], [85, 255, 255]),    # Green range
            ([0, 50, 50], [10, 255, 255]),     # Red range  
            ([170, 50, 50], [180, 255, 255])  # Red range (wrap around)
        ]:
            lower, upper = color_range
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            colored_pixels += cv2.countNonZero(mask)
        
        # Adaptive thresholds based on region size
        region_pixels = image_h * image_w
        
        # Scale thresholds based on region size - new region is smaller so lower thresholds
        if region_pixels < 60000:  # Precise minigame region
            white_threshold = 30
            colored_threshold = 50
        else:  # Larger regions (backward compatibility)
            white_threshold = 50
            colored_threshold = 100
        
        # If we have significant white and colored elements, might be a minigame
        if white_pixels > white_threshold and colored_pixels > colored_threshold:
            color_detected = True
            print(f"✓ Color-based detection: white_pixels={white_pixels}>{white_threshold}, colored_pixels={colored_pixels}>{colored_threshold}")
        else:
            print(f"❌ Color-based detection failed: white_pixels={white_pixels}<={white_threshold}, colored_pixels={colored_pixels}<={colored_threshold}")
        
        # Final fallback decision (only for compatibility when fish indicators disabled)
        detected = template_detected or color_detected
        
        if detected:
            print("⚠️ Fallback detection positive - but WITHOUT fish indicators, this might be a false positive!")
        else:
            print("❌ All detection methods failed - no minigame found")
        
        # Save debug image with region info
        project_root = Path(__file__).parent.parent.parent
        debug_path = project_root / "debug" / "minigame_detection_debug.png"
        try:
            # Ensure debug directory exists
            debug_path.parent.mkdir(exist_ok=True)
            
            # Create annotated debug image showing the analyzed region
            debug_img = screenshot_bgr.copy()
            h, w = debug_img.shape[:2]
            
            # Add border and text to show this is the analyzed region
            cv2.rectangle(debug_img, (0, 0), (w-1, h-1), (0, 255, 0), 2)
            cv2.putText(debug_img, f"Analyzed Region: {w}x{h}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if detected:
                cv2.putText(debug_img, "MINIGAME DETECTED", (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(debug_img, "NO MINIGAME", (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            cv2.imwrite(str(debug_path), debug_img)
            print(f"📸 Minigame detection debug saved: {debug_path} ({w}x{h})")
        except Exception as e:
            print(f"Failed to save debug image: {e}")
        
        if detected:
            print("🎮 ✅ MINIGAME DETECTED!")
        else:
            print("🎮 ❌ No minigame detected")
            
        return detected
        
    except Exception as e:
        print(f"Error detecting minigame bar presence: {e}")
        import traceback
        traceback.print_exc()
        return False


def handle_fishing_minigame(minigame_controller):
    """
    Handle the fishing minigame by detecting the UI and making decisions.
    Only runs after Fish_On_Hook detection - not for casting minigame.
    
    Returns True when minigame is complete, False to continue.
    """
    try:
        # Wait for minigame UI to appear after fish click
        # This prevents detecting casting bars or other UI elements
        import time
        time.sleep(0.5)  # Wait 500ms for minigame to fully load after click
        
        # Additional validation: Only run if we're truly in fish-catching minigame
        # (This function should only be called after Fish_On_Hook detection)
        
        # Detect minigame elements
        elements = detect_minigame_elements()
        
        # Use a grace period - don't end minigame immediately on detection failure
        # The minigame UI might flicker or be temporarily obscured
        global _minigame_detection_failures
        
        if not elements["minigame_active"]:
            _minigame_detection_failures += 1
            print(f"⚠️ Minigame UI detection failed (attempt {_minigame_detection_failures}/3)")
            
            # Only end minigame after 3 consecutive failures
            if _minigame_detection_failures >= 3:
                print("❌ Minigame UI not detected for 3 attempts, ending minigame...")
                _minigame_detection_failures = 0  # Reset counter
                return True
            else:
                # Continue with default/last known positions
                print("🎮 Continuing minigame with default positions...")
                indicator_pos = 0.5  # Default center position
                fish_pos = 0.5       # Default center position
        else:
            # Reset failure counter on successful detection
            _minigame_detection_failures = 0
            
        indicator_pos = elements["indicator_pos"]
        fish_pos = elements["fish_pos"]
        
        # Validate fish position - if detection fails, use a more conservative approach
        if fish_pos == 0.5:  # Default value indicates detection failure
            # Try to use a previously detected fish position or use adaptive positioning
            if hasattr(minigame_controller.cfg, 'last_known_fish_pos'):
                fish_pos = minigame_controller.cfg.last_known_fish_pos
                print(f"🐟 Using last known fish position: {fish_pos:.3f}")
            else:
                # Use indicator position with slight offset as fish estimate
                fish_pos = max(0.3, min(0.7, indicator_pos))
                print(f"🐟 Using adaptive fish position based on indicator: {fish_pos:.3f}")
        else:
            # Save successful fish detection for future use
            minigame_controller.cfg.last_known_fish_pos = fish_pos
        
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
    Uses only Windows API - NO PyAutoGUI to avoid detection.
    """
    try:
        print(f"🎮 Starting minigame action execution...")
        debug_log(LogCategory.MOUSE, "Starting minigame action execution...")
        
        # Get click position (center of Roblox window)
        if not WINDOW_MANAGER_AVAILABLE:
            print("❌ Window manager not available, cannot execute minigame action")
            debug_log(LogCategory.ERROR, "Window manager not available, cannot execute minigame action")
            return
        
        try:
            click_x, click_y = get_roblox_coordinates()
            if click_x is None or click_y is None:
                print("❌ Could not get Roblox coordinates, cannot execute minigame action")
                debug_log(LogCategory.ERROR, "Could not get Roblox coordinates, cannot execute minigame action")
                return
            print(f"🎯 Using click position: ({click_x}, {click_y})")
            debug_log(LogCategory.COORDINATES, f"Using click position: ({click_x}, {click_y})")
        except NameError:
            print("❌ get_roblox_coordinates function not available")
            debug_log(LogCategory.ERROR, "get_roblox_coordinates function not available")
            return
            
        action_type = decision.get("action_type", 0)
        action = decision.get("action")
        duration_factor = decision.get("duration_factor", 0.05)
        counter_strafe = decision.get("counter_strafe", 0)
        
        print(f"🎮 Minigame Action {action_type}: {action} (duration: {duration_factor:.3f}s)")
        debug_log(LogCategory.MINIGAME, f"Action {action_type}: {action} (duration: {duration_factor:.3f}s)")
        
        # Use ONLY Windows API - no PyAutoGUI fallback to avoid detection
        if not (VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None):
            print("❌ VirtualMouse not available - cannot execute minigame actions without detection")
            print("💡 Solution: Ensure VirtualMouse module is working properly")
            debug_log(LogCategory.ERROR, "VirtualMouse not available - cannot execute minigame actions without detection")
            return
            
        if action_type == 0:  # Stabilize - continuous rapid clicking at 5.6 CPS
            click_interval = decision.get("click_interval", 0.178)  # 5.6 CPS
            stabilize_duration = decision.get("stabilize_duration", 1.0)
            
            # Calculate number of clicks needed
            num_clicks = max(1, int(stabilize_duration / click_interval))
            
            print(f"🎯 Stabilizing with {num_clicks} clicks at {1/click_interval:.1f} CPS")
            debug_log(LogCategory.MINIGAME, f"Stabilizing with {num_clicks} clicks at {1/click_interval:.1f} CPS")
            
            for i in range(num_clicks):
                try:
                    # Use low-level Windows API only
                    virtual_mouse.mouse_down(click_x, click_y, 'left')
                    time.sleep(0.01)  # Very brief click
                    virtual_mouse.mouse_up(click_x, click_y, 'left')
                    print(f"✅ API click {i+1}/{num_clicks}")
                    debug_log(LogCategory.MOUSE, f"API click {i+1}/{num_clicks}")
                except Exception as e:
                    print(f"❌ Click {i+1} failed with Windows API: {e}")
                    debug_log(LogCategory.ERROR, f"Click {i+1} failed with Windows API: {e}")
                    return  # Don't fallback to PyAutoGUI - avoid detection
                
                # Wait between clicks (but not after the last click)
                if i < num_clicks - 1:
                    time.sleep(click_interval - 0.01)  # Subtract click duration
                
        elif action_type == 1:  # Stable left tracking
            try:
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Ensure mouse up first
                time.sleep(duration_factor)
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Hold to move left
                time.sleep(0.01)
                virtual_mouse.mouse_up(click_x, click_y, 'left')
                print(f"✅ Windows API stable left tracking (duration: {duration_factor:.3f}s)")
            except Exception as e:
                print(f"❌ Stable left failed with Windows API: {e}")
                return
                
        elif action_type == 2:  # Stable right tracking
            try:
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Hold to move right
                time.sleep(duration_factor)
                virtual_mouse.mouse_up(click_x, click_y, 'left')
                # Counter-strafe left
                if counter_strafe > 0:
                    virtual_mouse.mouse_up(click_x, click_y, 'left')
                    time.sleep(counter_strafe)
                print(f"✅ Windows API stable right tracking (duration: {duration_factor:.3f}s)")
            except Exception as e:
                print(f"❌ Stable right failed with Windows API: {e}")
                return
                    
        elif action_type == 3:  # Ankle break left (release and wait)
            try:
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Release completely
                time.sleep(duration_factor)
                print(f"✅ Windows API ankle break left (duration: {duration_factor:.3f}s)")
            except Exception as e:
                print(f"❌ Ankle break left failed with Windows API: {e}")
                return
                
        elif action_type == 4:  # Ankle break right (hold and wait)
            try:
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Hold down
                time.sleep(duration_factor)
                virtual_mouse.mouse_up(click_x, click_y, 'left')
                print(f"✅ Windows API ankle break right (duration: {duration_factor:.3f}s)")
            except Exception as e:
                print(f"❌ Ankle break right failed with Windows API: {e}")
                return
                
        elif action_type == 5:  # Unstable left aggressive
            try:
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Release for left
                time.sleep(duration_factor)
                # Counter-strafe right
                if counter_strafe > 0:
                    virtual_mouse.mouse_down(click_x, click_y, 'left')
                    time.sleep(counter_strafe)
                    virtual_mouse.mouse_up(click_x, click_y, 'left')
                print(f"✅ Windows API unstable left aggressive (duration: {duration_factor:.3f}s)")
            except Exception as e:
                print(f"❌ Unstable left aggressive failed with Windows API: {e}")
                return
                    
        elif action_type == 6:  # Unstable right aggressive
            try:
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Hold for right
                time.sleep(duration_factor)
                virtual_mouse.mouse_up(click_x, click_y, 'left')
                # Counter-strafe left
                if counter_strafe > 0:
                    virtual_mouse.mouse_up(click_x, click_y, 'left')
                    time.sleep(counter_strafe)
                print(f"✅ Windows API unstable right aggressive (duration: {duration_factor:.3f}s)")
            except Exception as e:
                print(f"❌ Unstable right aggressive failed with Windows API: {e}")
                return
                    
    except Exception as e:
        print(f"Error executing minigame action: {e}")


# Quick self-test / example usage
if __name__ == "__main__":
    cfg = MinigameConfig()
    ctl = MinigameController(cfg)

    print("AHK Minigame Controller - Example decisions:")
    for pos in [0.02, 0.1, 0.3, 0.45, 0.6, 0.85, 0.98]:
        d = ctl.decide(indicator=pos, arrow=None, stable=True)
        print(f"pos={pos:.2f} -> {d}")

    # Run a small simulation to test AHK logic
    final, hist = simulate(ctl, initial_indicator=0.9, steps=40, noise=0.02)
    print(f"Simulation final indicator: {final:.3f}")
    print("Last 5 steps:")
    for x in hist[-5:]:
        print(x)
