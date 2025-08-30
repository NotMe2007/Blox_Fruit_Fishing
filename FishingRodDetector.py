import cv2
import pyautogui
import numpy as np
import sys
import time

pyautogui.FAILSAFE = True

# Config
UN_PATH = 'Basic_Fishing_UN.png'
EQ_PATH = 'Basic_Fishing_EQ.png'
# Region to check: top-left and bottom-right (inclusive)
TOP_LEFT = (725, 1004)
BOTTOM_RIGHT = (1189, 1072)
threshold = 0.55   # matching threshold (0-1). Lower to be more permissive
debug = True       # set True to print info and save debug image


def load_templates():
    un_color = cv2.imread(UN_PATH)
    eq_color = cv2.imread(EQ_PATH)
    if un_color is None or eq_color is None:
        print('Error: Could not load template images. Ensure Basic_Fishing_UN.png and Basic_Fishing_EQ.png are in this folder.')
        sys.exit(1)
    return cv2.cvtColor(un_color, cv2.COLOR_BGR2GRAY), cv2.cvtColor(eq_color, cv2.COLOR_BGR2GRAY)


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
            best_val = combined
            best_loc = max_loc_i if max_loc_i is not None else max_loc_e
            best_scale = scale
            best_size = (new_w, new_h)

    return best_val, best_loc, best_scale, best_size


def check_region_and_act():
    un_gray, eq_gray = load_templates()

    left = max(0, TOP_LEFT[0])
    top = max(0, TOP_LEFT[1])
    right = max(left + 1, BOTTOM_RIGHT[0])
    bottom = max(top + 1, BOTTOM_RIGHT[1])
    w = right - left
    h = bottom - top
    region = (left, top, w, h)

    time.sleep(0.05)
    pil_img = pyautogui.screenshot(region=region)
    screenshot = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    best_un_val, best_un_loc, best_un_scale, best_un_size = multi_scale_match(screenshot_gray, un_gray)
    best_eq_val, best_eq_loc, best_eq_scale, best_eq_size = multi_scale_match(screenshot_gray, eq_gray)

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

    # Decide
    if best_un_loc is not None and best_un_size is not None and best_un_val >= threshold and best_un_val > best_eq_val:
        tw, th = best_un_size
        click_x = left + int(best_un_loc[0]) + tw // 2
        click_y = top + int(best_un_loc[1]) + th // 2
        pyautogui.click(click_x, click_y)
        print(f'Clicked at ({click_x}, {click_y}) - UN detected (score={best_un_val:.3f})')
        return True

    if best_eq_loc is not None and best_eq_size is not None and best_eq_val >= threshold and best_eq_val > best_un_val:
        print(f'EQ detected in region - Ending script (score={best_eq_val:.3f})')
        return False

    print('No UN or EQ detected in the region')
    return None


if __name__ == '__main__':
    res = check_region_and_act()
    if res is False:
        sys.exit(0)
