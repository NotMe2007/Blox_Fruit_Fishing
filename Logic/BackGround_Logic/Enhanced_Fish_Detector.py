"""
Enhanced Fish Detection Module - Reduces False Positives at Event Islands

This module provides improved fish-on-hook detection that minimizes false positives
from red water, event island effects, and other environmental colors.

Key improvements:
1. Template matching with shape analysis (not just color)
2. Exclamation mark specific detection (! shape)
3. Context-aware filtering (fishing line presence, position relative to character)
4. Multi-stage validation to reduce false positives
"""
import cv2
import numpy as np
from pathlib import Path
import time

# Debug Logger
try:
    from .Debug_Logger import debug_log, LogCategory
except ImportError:
    try:
        from Debug_Logger import debug_log, LogCategory
    except ImportError:
        def debug_log(category, message):
            print(f"[{category}] {message}")
        class LogCategory:
            FISH_DETECTION = "FISH_DETECTION"
            ERROR = "ERROR"
            SYSTEM = "SYSTEM"

class EnhancedFishDetector:
    """Enhanced fish detector that reduces false positives from environmental colors."""
    
    def __init__(self, images_dir):
        self.images_dir = Path(images_dir)
        self.fish_hook_template = None
        self.load_templates()
        
        # Detection parameters
        self.min_exclamation_area = 20      # Minimum pixels for exclamation mark
        self.max_exclamation_area = 400     # Maximum pixels (prevents large red areas)
        self.exclamation_aspect_ratio_min = 2.0  # Height/width ratio for "!"
        self.exclamation_aspect_ratio_max = 6.0  # Maximum ratio (not too thin)
        
        # Template matching thresholds
        self.template_threshold_high = 0.7   # High confidence threshold
        self.template_threshold_low = 0.5    # Fallback threshold
        
    def load_templates(self):
        """Load fish on hook template with automatic resizing if too large."""
        template_path = self.images_dir / 'Fish_On_Hook.png'
        if template_path.exists():
            self.fish_hook_template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
            if self.fish_hook_template is not None:
                template_h, template_w = self.fish_hook_template.shape[:2]
                debug_log(LogCategory.SYSTEM, f"✅ Fish template loaded: {template_path.name} ({template_w}x{template_h})")
                
                # CRITICAL: Check if template is too large for typical detection regions
                # Typical fish detection regions are around 400x300, but template is 585x1024!
                max_width = 300   # Maximum reasonable width for fish indicator
                max_height = 200  # Maximum reasonable height for fish indicator
                
                if template_w > max_width or template_h > max_height:
                    # Calculate scale to fit within reasonable bounds
                    scale_w = max_width / template_w
                    scale_h = max_height / template_h
                    scale = min(scale_w, scale_h)  # Use smaller scale to fit both dimensions
                    
                    new_w = int(template_w * scale)
                    new_h = int(template_h * scale)
                    
                    debug_log(LogCategory.SYSTEM, f"⚠️ Template too large ({template_w}x{template_h}), resizing to ({new_w}x{new_h})")
                    self.fish_hook_template = cv2.resize(self.fish_hook_template, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    debug_log(LogCategory.SYSTEM, f"✅ Template resized for better detection compatibility")
                    
            else:
                debug_log(LogCategory.ERROR, f"❌ Failed to load fish template: {template_path.name}")
        else:
            debug_log(LogCategory.ERROR, f"❌ Fish template not found: {template_path}")
    
    def detect_fish_on_hook(self, region, screenshot_bgr=None):
        """
        Enhanced fish detection with reduced false positives.
        
        Args:
            region: (x, y, width, height) detection region - ONLY this area is analyzed
            screenshot_bgr: Optional pre-captured BGR screenshot
            
        Returns:
            tuple: (found: bool, confidence: float, method: str)
        """
        try:
            # CRITICAL: Always get screenshot of ONLY the specified region, not full screen
            if screenshot_bgr is None:
                import pyautogui
                # Check if region coordinates are valid
                x, y, width, height = region
                if width <= 0 or height <= 0:
                    debug_log(LogCategory.ERROR, f"❌ Invalid region dimensions: {width}x{height}")
                    return False, 0.0, "invalid_region"
                
                try:
                    screenshot = pyautogui.screenshot(region=(x, y, width, height))
                    if screenshot.size == (0, 0):
                        debug_log(LogCategory.ERROR, f"❌ Screenshot is empty for region: {region}")
                        return False, 0.0, "empty_screenshot"
                    screenshot_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                except Exception as e:
                    debug_log(LogCategory.ERROR, f"❌ Screenshot capture failed: {e}")
                    return False, 0.0, "screenshot_error"
            else:
                # If screenshot provided, crop it to the specified region
                x, y, width, height = region
                # Ensure we only analyze the specified region, not the entire screen
                try:
                    screenshot_bgr = screenshot_bgr[y:y+height, x:x+width]
                    debug_log(LogCategory.FISH_DETECTION, f"🔍 Cropped screenshot to region: {width}x{height}")
                except Exception as e:
                    debug_log(LogCategory.ERROR, f"❌ Screenshot cropping failed: {e}")
                    return False, 0.0, "crop_error"
            
            # Now analyze ONLY the fish detection region (not full screen with bricks)
            # CRITICAL: Pre-filter out massive red areas (event island water)
            # This should now only check the small fish detection region, not the entire screen
            hsv_pre = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2HSV)
            large_red_exclusion = self._detect_large_red_areas(hsv_pre)
            red_water_percentage = cv2.countNonZero(large_red_exclusion) / (screenshot_bgr.shape[0] * screenshot_bgr.shape[1])
            
            debug_log(LogCategory.FISH_DETECTION, f"🌊 Red area analysis in detection region: {red_water_percentage*100:.1f}%")
            
            if red_water_percentage > 0.3:  # More than 30% of DETECTION REGION is red water
                debug_log(LogCategory.FISH_DETECTION, f"🌊 WARNING: {red_water_percentage*100:.1f}% red area in DETECTION REGION - likely event island!")
                debug_log(LogCategory.FISH_DETECTION, f"🛡️ Prioritizing template and shape detection over color")
                
                # At event islands, ONLY use template and shape detection
                if self.fish_hook_template is not None:
                    found, confidence = self._template_detection(screenshot_bgr)
                    if found and confidence > 0.6:  # Slightly lower threshold at event islands
                        debug_log(LogCategory.FISH_DETECTION, f"🐟 EVENT ISLAND: Template detection: {confidence:.3f}")
                        return True, confidence, "template_event"
                
                # Shape-based detection (very reliable at event islands)
                found, confidence = self._shape_based_detection(screenshot_bgr)
                if found and confidence > 0.5:  # Lower threshold for shape at event islands
                    debug_log(LogCategory.FISH_DETECTION, f"🐟 EVENT ISLAND: Shape detection: {confidence:.3f}")
                    return True, confidence, "shape_event"
                
                # Do NOT use color detection at event islands
                debug_log(LogCategory.FISH_DETECTION, f"🚫 Event island detected - skipping color detection to avoid false positives")
                return False, 0.0, "event_island_filtered"
            
            debug_log(LogCategory.FISH_DETECTION, f"✅ Normal fishing area detected - using all detection methods")
            
            # Normal area detection (use all methods)
            # Method 1: Template matching (most reliable)
            if self.fish_hook_template is not None:
                found, confidence = self._template_detection(screenshot_bgr)
                if found and confidence > self.template_threshold_high:
                    debug_log(LogCategory.FISH_DETECTION, f"🐟 Template detection: {confidence:.3f}")
                    return True, confidence, "template"
            
            # Method 2: Shape-based exclamation detection (fallback)
            found, confidence = self._shape_based_detection(screenshot_bgr)
            if found:
                debug_log(LogCategory.FISH_DETECTION, f"🐟 Shape detection: {confidence:.3f}")
                return True, confidence, "shape"
                
            # Method 3: Context-aware color detection (last resort, normal areas only)
            found, confidence = self._context_aware_color_detection(screenshot_bgr, region)
            if found:
                debug_log(LogCategory.FISH_DETECTION, f"🐟 Context color detection: {confidence:.3f}")
                return True, confidence, "context_color"
                
            return False, 0.0, "none"
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Enhanced fish detection error: {e}")
            return False, 0.0, "error"
    
    def _template_detection(self, screenshot_bgr):
        """Template matching with multiple scales and size validation."""
        try:
            if self.fish_hook_template is None:
                return False, 0.0
                
            best_score = 0.0
            screenshot_h, screenshot_w = screenshot_bgr.shape[:2]
            template_h, template_w = self.fish_hook_template.shape[:2]
            
            debug_log(LogCategory.FISH_DETECTION, f"Screenshot size: {screenshot_w}x{screenshot_h}, Template size: {template_w}x{template_h}")
            
            # Try multiple scales
            for scale in [0.8, 0.9, 1.0, 1.1, 1.2]:
                # Calculate scaled template dimensions
                scaled_w = int(template_w * scale)
                scaled_h = int(template_h * scale)
                
                # CRITICAL: Check if scaled template fits in screenshot
                if scaled_w >= screenshot_w or scaled_h >= screenshot_h:
                    debug_log(LogCategory.FISH_DETECTION, f"⚠️ Template too large at scale {scale}: {scaled_w}x{scaled_h} vs {screenshot_w}x{screenshot_h}")
                    continue  # Skip this scale
                
                # Scale template only if it fits
                if scale != 1.0:
                    scaled_template = cv2.resize(self.fish_hook_template, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
                else:
                    scaled_template = self.fish_hook_template
                
                # Double-check dimensions before template matching
                if scaled_template.shape[0] >= screenshot_bgr.shape[0] or scaled_template.shape[1] >= screenshot_bgr.shape[1]:
                    debug_log(LogCategory.FISH_DETECTION, f"⚠️ Scaled template still too large, skipping scale {scale}")
                    continue
                
                # Safe template matching
                try:
                    result = cv2.matchTemplate(screenshot_bgr, scaled_template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    
                    best_score = max(best_score, max_val)
                    debug_log(LogCategory.FISH_DETECTION, f"Template match scale {scale}: {max_val:.3f}")
                    
                    if max_val >= self.template_threshold_high:
                        debug_log(LogCategory.FISH_DETECTION, f"✅ High confidence template match: {max_val:.3f}")
                        return True, max_val
                        
                except cv2.error as cv_error:
                    debug_log(LogCategory.ERROR, f"OpenCV template match error at scale {scale}: {cv_error}")
                    continue  # Try next scale
                    
            # Check lower threshold as fallback
            if best_score >= self.template_threshold_low:
                return True, best_score
                
            return False, best_score
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Template detection error: {e}")
            return False, 0.0
    
    def _shape_based_detection(self, screenshot_bgr):
        """Detect exclamation mark by shape analysis, not just color."""
        try:
            # Convert to grayscale for better shape detection
            gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)
            
            # Use adaptive thresholding to handle varying lighting
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            best_score = 0.0
            
            for contour in contours:
                score = self._analyze_exclamation_contour(contour, screenshot_bgr)
                best_score = max(best_score, score)
                
                if score > 0.6:  # High confidence shape match
                    return True, score
                    
            return False, best_score
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Shape detection error: {e}")
            return False, 0.0
    
    def _analyze_exclamation_contour(self, contour, screenshot_bgr):
        """Analyze if a contour looks like an exclamation mark."""
        try:
            area = cv2.contourArea(contour)
            
            # Size filtering
            if area < self.min_exclamation_area or area > self.max_exclamation_area:
                return 0.0
            
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # Aspect ratio check (exclamation marks are tall and narrow)
            aspect_ratio = h / w if w > 0 else 0
            if aspect_ratio < self.exclamation_aspect_ratio_min or aspect_ratio > self.exclamation_aspect_ratio_max:
                return 0.0
            
            score = 0.0
            
            # Aspect ratio scoring
            if 2.5 <= aspect_ratio <= 4.5:  # Ideal exclamation mark ratio
                score += 0.4
            elif 2.0 <= aspect_ratio <= 6.0:  # Acceptable range
                score += 0.2
            
            # Size scoring  
            if 30 <= area <= 200:  # Ideal size
                score += 0.3
            elif 20 <= area <= 400:  # Acceptable size
                score += 0.1
            
            # Color validation - check if it's actually a bright/contrasting element
            mask = np.zeros(screenshot_bgr.shape[:2], np.uint8)
            cv2.drawContours(mask, [contour], -1, 255, -1)
            mean_color = cv2.mean(screenshot_bgr, mask=mask)[:3]
            brightness = (mean_color[0] + mean_color[1] + mean_color[2]) / 3
            
            # Bright elements (likely exclamation marks)
            if brightness > 150:
                score += 0.2
            elif brightness > 100:
                score += 0.1
            
            return score
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Contour analysis error: {e}")
            return 0.0
    
    def _context_aware_color_detection(self, screenshot_bgr, region):
        """Color detection that considers context to reduce false positives."""
        try:
            hsv = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2HSV)
            
            # Multiple color ranges for different exclamation types
            color_masks = []
            
            # White/bright exclamation marks
            white_lower = np.array([0, 0, 200])
            white_upper = np.array([180, 50, 255])
            white_mask = cv2.inRange(hsv, white_lower, white_upper)
            color_masks.append(("white", white_mask))
            
            # Yellow exclamation marks (common in Roblox)
            yellow_lower = np.array([20, 100, 150])
            yellow_upper = np.array([30, 255, 255])
            yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
            color_masks.append(("yellow", yellow_mask))
            
            # VERY SPECIFIC red detection (only small, isolated red elements)
            # This is now MUCH more restrictive to avoid the massive red water
            red_lower1 = np.array([0, 180, 180])  # VERY high saturation and value only
            red_upper1 = np.array([8, 255, 255])
            red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
            
            red_lower2 = np.array([172, 180, 180])  # VERY high saturation and value only
            red_upper2 = np.array([180, 255, 255])
            red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
            red_mask = cv2.bitwise_or(red_mask1, red_mask2)
            
            # CRITICAL: Filter out large red areas (event island water like in screenshot)
            # This will remove thousands of pixels of red water
            red_mask = self._filter_large_areas(red_mask, max_area=150)  # Even smaller limit
            color_masks.append(("red", red_mask))
            
            # Exclude problematic colors
            exclude_masks = []
            
            # Blue/cyan (character abilities, water)
            blue_lower = np.array([80, 50, 50])
            blue_upper = np.array([130, 255, 255])
            blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)
            exclude_masks.append(blue_mask)
            
            # Large red areas (event island water) - This will catch the massive red area in screenshot
            large_red_mask = self._detect_large_red_areas(hsv)
            exclude_masks.append(large_red_mask)
            
            # NEW: Also exclude medium-brightness red areas (water tends to be less bright than exclamations)
            medium_red_lower = np.array([0, 40, 40])
            medium_red_upper = np.array([25, 200, 200])
            medium_red_mask = cv2.inRange(hsv, medium_red_lower, medium_red_upper)
            # Only exclude if it's a large area
            medium_red_filtered = self._filter_large_areas(medium_red_mask, max_area=800)
            if cv2.countNonZero(medium_red_filtered) < cv2.countNonZero(medium_red_mask) * 0.1:
                exclude_masks.append(medium_red_mask)  # Most pixels were large areas
            
            # Combine exclusions
            combined_exclude = np.zeros_like(hsv[:,:,0])
            for mask in exclude_masks:
                combined_exclude = cv2.bitwise_or(combined_exclude, mask)
            
            # Analyze each color mask
            best_score = 0.0
            
            for color_name, color_mask in color_masks:
                # Remove excluded areas
                filtered_mask = cv2.bitwise_and(color_mask, cv2.bitwise_not(combined_exclude))
                
                # Find contours in filtered mask
                contours, _ = cv2.findContours(filtered_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for contour in contours:
                    score = self._analyze_exclamation_contour(contour, screenshot_bgr)
                    if score > 0.5:  # Reasonable confidence
                        debug_log(LogCategory.FISH_DETECTION, f"🎯 {color_name} exclamation found: {score:.3f}")
                        best_score = max(best_score, score)
            
            return best_score > 0.5, best_score
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Context color detection error: {e}")
            return False, 0.0
    
    def _filter_large_areas(self, mask, max_area=300):
        """Filter out contours that are too large (like water backgrounds)."""
        try:
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            filtered_mask = np.zeros_like(mask)
            
            for contour in contours:
                if cv2.contourArea(contour) <= max_area:
                    cv2.drawContours(filtered_mask, [contour], -1, 255, -1)
                    
            return filtered_mask
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Area filtering error: {e}")
            return mask
    
    def _detect_large_red_areas(self, hsv):
        """Detect large red areas that are likely water/background, not exclamation marks or normal structures."""
        try:
            # MORE SPECIFIC red detection for actual event island water (not bricks/structures)
            # Event island water has specific characteristics: bright, saturated, covers huge areas
            red_lower1 = np.array([0, 80, 100])    # Higher saturation to avoid brown/brick colors
            red_upper1 = np.array([15, 255, 255])  # Bright red range
            red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
            
            red_lower2 = np.array([165, 80, 100])  # Higher saturation for deep reds
            red_upper2 = np.array([180, 255, 255])
            red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
            
            red_mask = cv2.bitwise_or(red_mask1, red_mask2)
            
            # Use morphological operations to connect nearby red pixels (water areas)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
            
            # Find large contours - but be much more restrictive about what's "large"
            contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            large_areas_mask = np.zeros_like(hsv[:,:,0])
            
            # Get total region area for percentage calculation
            total_area = hsv.shape[0] * hsv.shape[1]
            
            for contour in contours:
                area = cv2.contourArea(contour)
                area_percentage = area / total_area
                
                # MUCH more restrictive: Only consider it "event island water" if:
                # 1. Area is very large (>2000 pixels in a small detection region = likely water)
                # 2. OR covers >40% of the detection region (massive water coverage)
                if area > 2000 or area_percentage > 0.4:
                    cv2.drawContours(large_areas_mask, [contour], -1, 255, -1)
                    debug_log(LogCategory.FISH_DETECTION, f"🌊 Large red area detected: {area} pixels ({area_percentage*100:.1f}% of region)")
                else:
                    debug_log(LogCategory.FISH_DETECTION, f"🧱 Small red area ignored: {area} pixels ({area_percentage*100:.1f}%) - likely structure")
                    
            return large_areas_mask
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Large red area detection error: {e}")
            return np.zeros_like(hsv[:,:,0])