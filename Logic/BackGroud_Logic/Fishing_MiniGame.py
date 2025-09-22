"""
Minigame logic ported from the AutoHotkey fishing macro.

This module implements a configuration-driven controller that decides corrective
actions for a minigame "indicator" (the moving cursor/needle inside a fish bar).
It doesn't interact with GUI or input devices; it provides the decision logic
(your AHK or other automation layer can call into this to get what to do next).

Contract (inputs/outputs):
- Inputs: minigame state described by a dict or named args:
    - indicator: float (0..1) current normalized position of the indicator along the bar
    - arrow: "left"|"right"|None (direction the game is pushing the indicator)
    - stable: bool (whether the current state is "stable" or "unstable")
    - delta_time: float seconds since last update (optional)
- Outputs: action dict:
    - action: "none"|"move_left"|"move_right"
    - intensity: float (0..1) suggested strength / duration fraction
    - note: optional human readable note

Assumptions / simplifications vs original AHK script:
- Positions are normalized to 0..1 (0 = left, 1 = right).
- Fish bar is a centered subrange of the full bar; side bars and white bar logic
  are approximated using ratios and tolerances from the original settings.
- Multipliers/divisions are used to compute intensity as in the original script.

Edge cases handled:
- indicator outside 0..1 is clamped
- missing arrow/stable state treated as conservative (smaller corrections)

Usage:
    from minigame_logic import MinigameController
    cfg = {...}
    ctl = MinigameController(cfg)
    action = ctl.decide(indicator=0.82, arrow='right', stable=False)

"""
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict
import cv2
import numpy as np
import pyautogui
import time
import random
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

# Load minigame templates
IMAGES_DIR = Path(__file__).parent.parent.parent / 'Images'

def safe_load_template(path):
    """Safely load a template image, handling both None and empty array cases."""
    try:
        # Load as color image first
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is not None and img.size > 0:
            return img
        else:
            print(f"❌ Template failed to load: {path.name}")
    except Exception as e:
        print(f"❌ Template loading error: {path.name} - {e}")
    return None

def safe_load_template_gray(path):
    """Safely load a template as grayscale, handling both None and empty array cases."""
    try:
        # Load as grayscale image
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is not None and img.size > 0:
            return img
        else:
            print(f"❌ Template failed to load: {path.name}")
    except Exception as e:
        print(f"❌ Template loading error: {path.name} - {e}")
    return None

# Load minigame-related templates
try:
    MINIGAME_BAR_TPL = safe_load_template_gray(IMAGES_DIR / 'MiniGame_Bar.png')
    FISH_LEFT_TPL = safe_load_template(IMAGES_DIR / 'Fish_Left.png')
    FISH_RIGHT_TPL = safe_load_template(IMAGES_DIR / 'Fish_Right.png')
    
    # Print template load status
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
            print(f"✅ Minigame template loaded: {name} (shape: {shape_str})")
        else:
            print(f"❌ Minigame template failed to load: {name}")
            
except Exception as e:
    print(f"Warning: Could not load minigame template images: {e}")
    MINIGAME_BAR_TPL = None
    FISH_LEFT_TPL = None  
    FISH_RIGHT_TPL = None


@dataclass
class MinigameConfig:
    # Control stat from fishing rod (affects max duration calculations)
    control: float = 0.0  # 0.15-0.25+ based on rod stats
    
    # Color detection tolerances (from AHK script)
    fish_bar_color_tolerance: int = 5  # Brown fish color detection
    white_bar_color_tolerance: int = 15  # White bar detection
    arrow_color_tolerance: int = 6  # Arrow/indicator detection
    
    # Tolerances (normalized units)
    fish_bar_half_width: float = 0.08  # half-width of the fish bar (so full width = 2*half)
    white_bar_half_width: float = 0.02

    # Scanning delay (used by callers, returned for reference) - from AHK: 10ms
    scan_delay: float = 0.001  # 1ms converted to seconds
    
    # Dynamic fish center position (can be updated during minigame)
    fish_center: float = 0.5  # Default to center, updated by detection

    # Side bar ratio and delay (from AHK script)
    side_bar_ratio: float = 0.7  # AHK default
    side_delay: float = 0.4  # 400ms converted to seconds

    # Stability multipliers/divisions (from AHK script - exact values)
    stable_right_multiplier: float = 2.40
    stable_right_division: float = 1.60
    stable_left_multiplier: float = 1.1
    stable_left_division: float = 1.12

    # Unstable multipliers/divisions (simplified for easier fish game)
    unstable_right_multiplier: float = 1.8
    unstable_right_division: float = 1.3
    unstable_left_multiplier: float = 1.6
    unstable_left_division: float = 1.2

    # Ankle-break multipliers (from AHK script - exact values)
    right_ankle_break_multiplier: float = 0.40
    left_ankle_break_multiplier: float = 0.10

    # Pixel scaling and deadzone calculations (calculated dynamically)
    pixel_scaling: float = 1.0  # will be calculated based on bar width
    deadzone: float = 0.02  # small deadzone for stability (normalized)
    deadzone2: float = 0.04  # larger deadzone for aggressive actions (normalized)
    
    # Boundary calculations (normalized, calculated dynamically)
    max_left_bar: float = 0.15  # left boundary
    max_right_bar: float = 0.85  # right boundary

    # Minimal action intensity and max clamp
    min_intensity: float = 0.05
    max_intensity: float = 1.0


class MinigameController:
    def __init__(self, cfg: Optional[MinigameConfig] = None):
        self.cfg = cfg or MinigameConfig()

    def _clamp01(self, v: float) -> float:
        if v is None:
            return 0.0
        return max(0.0, min(1.0, v))

    def _compute_target(self) -> float:
        # The fish bar position - can be dynamic based on fish detection
        return self.cfg.fish_center

    def _inside_fish_bar(self, indicator: float) -> bool:
        target = self._compute_target()
        half = self.cfg.fish_bar_half_width
        return (target - half) <= indicator <= (target + half)

    def decide(self, indicator: float, arrow: Optional[str] = None, stable: bool = True,
               delta_time: Optional[float] = None) -> Dict:
        """
        Decide corrective action based on AHK minigame logic with 6 action types.
        
        Action types (matching AHK script):
        0 = stabilize (short click for minor correction)
        1 = stable left tracking (moderate left movement with counter-strafe)
        2 = stable right tracking (moderate right movement with counter-strafe)
        3 = max left boundary (indicator is too far right, strong left correction)
        4 = max right boundary (indicator is too far left, strong right correction)
        5 = unstable left (aggressive left movement for unstable conditions)
        6 = unstable right (aggressive right movement for unstable conditions)

        indicator: normalized 0..1 position (white bar position)
        arrow: 'left'|'right' or None (game pushing direction)
        stable: whether minigame is currently in a stable state
        delta_time: time since last decision (for adaptive duration)

        Returns a dict: {action, intensity, note, action_type, duration_factor}
        """
        indicator = self._clamp01(indicator)
        fish_center = self._compute_target()
        
        # Calculate direction from white bar to fish center
        direction = indicator - fish_center  # positive = white bar is right of fish
        distance_factor = abs(direction) / self.cfg.white_bar_half_width
        
        # Check boundary conditions (AHK Action 3 & 4) - based on indicator position
        if indicator < self.cfg.max_left_bar:
            # Indicator is at extreme left - force right movement  
            return {
                "action": "move_right", 
                "intensity": 1.1, 
                "note": "max_right_boundary",
                "action_type": 4,
                "duration_factor": self.cfg.side_delay
            }
        elif indicator > self.cfg.max_right_bar:
            # Indicator is at extreme right - force left movement
            return {
                "action": "move_left", 
                "intensity": 0.9, 
                "note": "max_left_boundary", 
                "action_type": 3,
                "duration_factor": self.cfg.side_delay
            }
        
        # Normal tracking logic based on deadzone thresholds
        if abs(direction) <= self.cfg.deadzone:
            # AHK Action 0: Stabilize - small correction at 5.537 CPS
            return {
                "action": "stabilize",
                "intensity": 0.1,
                "note": "stabilizing",
                "action_type": 0,
                "duration_factor": 0.1806  # 5.537 CPS (31 clicks / 5.598542 seconds)
            }
            
        elif self.cfg.deadzone < abs(direction) <= self.cfg.deadzone2:
            # AHK Action 1 & 2: Stable tracking
            if direction > 0:  # Move left (Action 1)
                intensity = abs(direction) * self.cfg.stable_left_multiplier * self.cfg.pixel_scaling
                adaptive_duration = 0.5 + 0.5 * (distance_factor ** 1.2)
                if distance_factor < 0.2:
                    adaptive_duration = 0.15 + 0.15 * distance_factor
                
                return {
                    "action": "move_left",
                    "intensity": min(intensity, self.cfg.max_intensity),
                    "note": "stable_left_tracking",
                    "action_type": 1,
                    "duration_factor": adaptive_duration,
                    "counter_strafe": adaptive_duration / self.cfg.stable_left_division
                }
            else:  # Move right (Action 2)
                intensity = abs(direction) * self.cfg.stable_right_multiplier * self.cfg.pixel_scaling
                adaptive_duration = 0.5 + 0.5 * (distance_factor ** 1.2)
                if distance_factor < 0.2:
                    adaptive_duration = 0.15 + 0.15 * distance_factor
                    
                return {
                    "action": "move_right",
                    "intensity": min(intensity, self.cfg.max_intensity),
                    "note": "stable_right_tracking",
                    "action_type": 2,
                    "duration_factor": adaptive_duration,
                    "counter_strafe": adaptive_duration / self.cfg.stable_right_division
                }
                
        else:  # abs(direction) > deadzone2
            # AHK Action 5 & 6: Unstable/aggressive tracking
            if direction > 0:  # Move left aggressively (Action 5)
                # Calculate max duration based on Control stat (AHK style)
                min_duration = 0.01
                # Use a base duration that scales with distance and control
                base_duration = abs(direction) * 2.0  # Scale up for visible differences
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
                
                return {
                    "action": "move_left",
                    "intensity": min(1.0, raw_duration),
                    "note": "unstable_left_aggressive", 
                    "action_type": 5,
                    "duration_factor": duration,
                    "counter_strafe": duration / self.cfg.unstable_left_division
                }
            else:  # Move right aggressively (Action 6)
                # Calculate max duration based on Control stat (AHK style)
                min_duration = 0.01
                # Use a base duration that scales with distance and control
                base_duration = abs(direction) * 2.0  # Scale up for visible differences
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
                
                return {
                    "action": "move_right",
                    "intensity": min(1.0, raw_duration),
                    "note": "unstable_right_aggressive",
                    "action_type": 6,
                    "duration_factor": duration,
                    "counter_strafe": duration / self.cfg.unstable_right_division
                }


# A simple step simulator to allow light unit testing or tuning
def simulate(controller: MinigameController, initial_indicator: float,
             steps: int = 50, step_dt: float = 0.05, noise: float = 0.0) -> Tuple[float, list]:
    """
    Simulate the indicator for a number of steps, applying controller.decide at each step.
    This sim is simplistic: it applies the controller's intensity as a velocity toward center.

    Returns the final indicator and a history of (indicator, action, intensity) tuples.
    """
    import random

    indicator = controller._clamp01(initial_indicator)
    history = []
    for i in range(steps):
        # For simulation, pretend arrow is random push
        arrow = random.choice([None, "left", "right"]) if noise > 0 else None
        stable = True if random.random() > 0.1 else False if noise > 0 else True
        decision = controller.decide(indicator=indicator, arrow=arrow, stable=stable, delta_time=step_dt)

        # Convert intensity to a velocity toward center
        if decision["action"] == "none":
            velocity = 0.0
        elif decision["action"] == "move_left":
            velocity = -decision["intensity"] * 0.02  # tuning constant for sim
        else:
            velocity = decision["intensity"] * 0.02

        # Arrow/environmental push (small)
        env_push = 0.0
        if arrow == "left":
            env_push -= 0.01
        elif arrow == "right":
            env_push += 0.01

        # Update indicator with velocity + environment + noise
        indicator = controller._clamp01(indicator + velocity + env_push + (random.random() - 0.5) * noise)
        history.append((indicator, decision["action"], decision["intensity"]))

    return indicator, history


# =============================================================================
# MINIGAME DETECTION AND HANDLING FUNCTIONS
# =============================================================================

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
        
        try:
            click_x, click_y = get_roblox_coordinates()
            if click_x is None or click_y is None:
                return
        except NameError:
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
                time.sleep(duration_factor)
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Hold to move left
                time.sleep(0.01)
                virtual_mouse.mouse_up(click_x, click_y, 'left')
            else:
                pyautogui.mouseUp(click_x, click_y, button='left')
                time.sleep(duration_factor)
                pyautogui.mouseDown(click_x, click_y, button='left')
                time.sleep(0.01)
                pyautogui.mouseUp(click_x, click_y, button='left')
                
        elif action_type == 2:  # Stable right tracking
            if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Hold to move right
                time.sleep(duration_factor)
                virtual_mouse.mouse_up(click_x, click_y, 'left')
                # Counter-strafe left
                if counter_strafe > 0:
                    virtual_mouse.mouse_up(click_x, click_y, 'left')
                    time.sleep(counter_strafe)
            else:
                pyautogui.mouseDown(click_x, click_y, button='left')
                time.sleep(duration_factor)
                pyautogui.mouseUp(click_x, click_y, button='left')
                # Counter-strafe left
                if counter_strafe > 0:
                    pyautogui.mouseUp(click_x, click_y, button='left')
                    time.sleep(counter_strafe)
                    
        elif action_type == 3:  # Ankle break left (release and wait)
            if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Release completely
                time.sleep(duration_factor)
            else:
                pyautogui.mouseUp(click_x, click_y, button='left')
                time.sleep(duration_factor)
                
        elif action_type == 4:  # Ankle break right (hold and wait)
            if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Hold down
                time.sleep(duration_factor)
                virtual_mouse.mouse_up(click_x, click_y, 'left')
            else:
                pyautogui.mouseDown(click_x, click_y, button='left')
                time.sleep(duration_factor)
                pyautogui.mouseUp(click_x, click_y, button='left')
                
        elif action_type == 5:  # Unstable left aggressive
            if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
                virtual_mouse.mouse_up(click_x, click_y, 'left')    # Release for left
                time.sleep(duration_factor)
                # Counter-strafe right
                if counter_strafe > 0:
                    virtual_mouse.mouse_down(click_x, click_y, 'left')
                    time.sleep(counter_strafe)
                    virtual_mouse.mouse_up(click_x, click_y, 'left')
            else:
                pyautogui.mouseUp(click_x, click_y, button='left')
                time.sleep(duration_factor)
                # Counter-strafe right
                if counter_strafe > 0:
                    pyautogui.mouseDown(click_x, click_y, button='left')
                    time.sleep(counter_strafe)
                    pyautogui.mouseUp(click_x, click_y, button='left')
                    
        elif action_type == 6:  # Unstable right aggressive
            if VIRTUAL_MOUSE_AVAILABLE and virtual_mouse is not None:
                virtual_mouse.mouse_down(click_x, click_y, 'left')  # Hold for right
                time.sleep(duration_factor)
                virtual_mouse.mouse_up(click_x, click_y, 'left')
                # Counter-strafe left
                if counter_strafe > 0:
                    virtual_mouse.mouse_up(click_x, click_y, 'left')
                    time.sleep(counter_strafe)
            else:
                pyautogui.mouseDown(click_x, click_y, button='left')
                time.sleep(duration_factor)
                pyautogui.mouseUp(click_x, click_y, button='left')
                # Counter-strafe left
                if counter_strafe > 0:
                    pyautogui.mouseUp(click_x, click_y, button='left')
                    time.sleep(counter_strafe)
                    
    except Exception as e:
        print(f"Error executing minigame action: {e}")


# Quick example / self-test
if __name__ == "__main__":
    cfg = MinigameConfig()
    ctl = MinigameController(cfg)

    print("Example decisions:")
    for pos in [0.02, 0.1, 0.3, 0.45, 0.6, 0.85, 0.98]:
        d = ctl.decide(indicator=pos, arrow=None, stable=True)
        print(f"pos={pos:.2f} -> {d}")

    # Run a small simulation
    final, hist = simulate(ctl, initial_indicator=0.9, steps=40, noise=0.02)
    print(f"Sim final indicator: {final:.3f}")
    print("Last 5 steps:")
    for x in hist[-5:]:
        print(x)
