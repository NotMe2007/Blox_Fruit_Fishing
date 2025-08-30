import time
import sys
import cv2
import numpy as np
import pyautogui
from pathlib import Path
import importlib.util

pyautogui.FAILSAFE = True

# Load the detector module from Images/FishingRodDetector.py (robust import by path)
detector_path = Path(__file__).parent / 'Images' / 'FishingRodDetector.py'
if not detector_path.exists():
    print('Error: detector file not found:', detector_path)
    sys.exit(1)

spec = importlib.util.spec_from_file_location('frod', str(detector_path))
frod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frod)


def screen_region_image():
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


def click_and_hold(x, y, hold_seconds=0.894):
    pyautogui.mouseDown(x, y)
    time.sleep(hold_seconds)
    pyautogui.mouseUp(x, y)


def main():
    # Load grayscale templates from detector helper
    try:
        un_gray, eq_gray = frod.load_templates()
    except Exception:
        # If detector exposes variables instead
        un_gray = getattr(frod, 'un_gray', None)
        eq_gray = getattr(frod, 'eq_gray', None)
    if un_gray is None or eq_gray is None:
        print('Error: templates not available from detector')
        sys.exit(1)

    # First capture
    img, gray, left, top = screen_region_image()

    un_val, un_loc, un_scale, un_size = frod.multi_scale_match(gray, un_gray)
    eq_val, eq_loc, eq_scale, eq_size = frod.multi_scale_match(gray, eq_gray)

    print(f'Detected scores -> UN: {un_val:.3f} (scale={un_scale}) EQ: {eq_val:.3f} (scale={eq_scale})')

    # If EQ present -> click and hold
    if eq_loc is not None and eq_size is not None and eq_val >= frod.threshold and eq_val > un_val:
        ex, ey = int(eq_loc[0]), int(eq_loc[1])
        ew, eh = int(eq_size[0]), int(eq_size[1])
        click_x = left + ex + ew // 2
        click_y = top + ey + eh // 2
        print(f'EQ detected, click-and-hold at ({click_x},{click_y})')
        click_and_hold(click_x, click_y, 0.894)
        return

    # If UN present -> click UN location then re-check EQ
    if un_loc is not None and un_size is not None and un_val >= frod.threshold and un_val > eq_val:
        ux, uy = int(un_loc[0]), int(un_loc[1])
        uw, uh = int(un_size[0]), int(un_size[1])
        click_x = left + ux + uw // 2
        click_y = top + uy + uh // 2
        print(f'UN detected, clicking at UN location ({click_x},{click_y})')
        pyautogui.click(click_x, click_y)
        time.sleep(0.25)

        # Re-capture and check EQ
        _, gray2, left2 = None, None, None
        img2, gray2, left2, top2 = screen_region_image()
        eq_val2, eq_loc2, eq_scale2, eq_size2 = frod.multi_scale_match(gray2, eq_gray)
        print(f'After clicking UN, EQ score {eq_val2:.3f} (threshold {frod.threshold})')
        if eq_loc2 is not None and eq_size2 is not None and eq_val2 >= frod.threshold and eq_val2 > un_val:
            ex2, ey2 = int(eq_loc2[0]), int(eq_loc2[1])
            ew2, eh2 = int(eq_size2[0]), int(eq_size2[1])
            click_x2 = left + ex2 + ew2 // 2
            click_y2 = top + ey2 + eh2 // 2
            print(f'Now EQ detected, click-and-hold at ({click_x2},{click_y2})')
            click_and_hold(click_x2, click_y2, 0.894)
            return

        print('Error cannot Equipt rod')
        return

    # Otherwise not found
    print('No UN or EQ detected in region')


if __name__ == '__main__':
    main()
