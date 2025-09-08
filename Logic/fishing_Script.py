import time
import sys
import cv2
import numpy as np
import pyautogui
from pathlib import Path
import importlib.util

pyautogui.FAILSAFE = True

def get_detector_module():
    """Lazily load the FishingRodDetector module.

    Returns the loaded module. Raises RuntimeError if the detector cannot be found
    or loaded. This avoids printing or exiting during import-time of this module.
    """
    detector_path = Path(__file__).resolve().parents[1] / 'Images' / 'FishingRodDetector.py'
    if not detector_path.exists():
        alt = Path(__file__).resolve().parents[1] / 'FishingRodDetector.py'
        if alt.exists():
            detector_path = alt
        else:
            raise RuntimeError(f"detector file not found. Tried: {detector_path} and {alt}")

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


def CastFishingRod(x, y, hold_seconds=0.894):
    # Use coordinates 20 pixels above the screen center regardless of inputs
    screen_w, screen_h = pyautogui.size()
    center_x = screen_w // 2
    center_y = screen_h // 2
    target_x = center_x
    target_y = center_y - 20

    # move to target and perform the hold
    pyautogui.moveTo(target_x, target_y)
    pyautogui.mouseDown(target_x, target_y)
    time.sleep(hold_seconds)
    pyautogui.mouseUp(target_x, target_y)

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
    # load detector templates lazily
    try:
        frod = get_detector_module()
    except RuntimeError:
        return False
    # prefer detector-provided generic template, fall back to module-level one
    generic_tpl = getattr(frod, 'FISH_ON_HOOK_TPL', None) or globals().get('FISH_ON_HOOK_TPL')
    if generic_tpl is None:
        return False

    # search the full screen for the Fish_On_Hook template
    screen_w, screen_h = pyautogui.size()
    region = (0, 0, screen_w, screen_h)
    found, score = _match_template_in_region(generic_tpl, region, threshold=0.84)
    if found:
        # click current mouse position (no coordinates passed)
        pyautogui.click()
        # small pause to avoid double-detecting the same hook
        time.sleep(duration)
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
try:
    POWER_MAX_TPL = cv2.imread(str(IMAGES_DIR / 'Power_Max.png'), cv2.IMREAD_GRAYSCALE)
    POWER_ACTIVE_TPL = cv2.imread(str(IMAGES_DIR / 'Power_Active.png'), cv2.IMREAD_GRAYSCALE)
    FISH_ON_HOOK_TPL = cv2.imread(str(IMAGES_DIR / 'Fish_On_Hook.png'), cv2.IMREAD_GRAYSCALE)
    FISH_LEFT_TPL = cv2.imread(str(IMAGES_DIR / 'Fish_Left.png'), cv2.IMREAD_GRAYSCALE)
    FISH_RIGHT_TPL = cv2.imread(str(IMAGES_DIR / 'Fish_Right.png'), cv2.IMREAD_GRAYSCALE)
    SHIFT_LOCK_TPL = cv2.imread(str(IMAGES_DIR / 'Shift_Lock.png'), cv2.IMREAD_GRAYSCALE)
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
    if template is None:
        return False, 0.0
    x, y, w, h = region
    pil = pyautogui.screenshot(region=(x, y, w, h))
    hay = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    hay_gray = cv2.cvtColor(hay, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(hay_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return (max_val >= threshold), float(max_val)


def _estimate_bar_fill(region, brightness_thresh=110):
    """Estimate fill fraction (0.0-1.0) of the bar under the icon inside region.
    Uses a heuristic: sample the lower 30% of the region and compute the fraction
    of bright pixels across a central horizontal slice.
    """
    x, y, w, h = region
    # sample the lower part of the region where the bar usually appears
    sample_y = y + int(h * 0.6)
    sample_h = max(3, int(h * 0.3))
    sample_x = x + int(w * 0.05)
    sample_w = max(10, int(w * 0.9))
    pil = pyautogui.screenshot(region=(sample_x, sample_y, sample_w, sample_h))
    img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # take the central row (or average a few rows) to be robust
    row = gray[sample_h // 2 - 1: sample_h // 2 + 2, :]
    # use ndarray.mean to keep typing happy
    row_mean = row.mean(axis=0)
    filled = np.count_nonzero(row_mean > brightness_thresh)
    total = row_mean.shape[0]
    return float(filled) / float(total) if total > 0 else 0.0


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

    left_tpl = left_tpl or globals().get('FISH_LEFT_TPL')
    right_tpl = right_tpl or globals().get('FISH_RIGHT_TPL')

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

    active_tpl = getattr(frod, 'POWER_ACTIVE_TPL', None) or POWER_ACTIVE_TPL
    power_max_tpl = getattr(frod, 'POWER_MAX_TPL', None) or POWER_MAX_TPL
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
