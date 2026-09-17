"""Casting-meter detection and bounded recovery, independent of live input."""
import cv2
import numpy as np


def has_casting_meter(image):
    """Find a tall green/yellow fill with dark rails, as in the casting HUD."""
    if image is None or image.size == 0:
        return False
    height, width = image.shape[:2]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([25, 120, 100]), np.array([90, 255, 255]))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if not (3 <= w <= max(24, width*0.05) and h >= max(30, height*0.05) and h >= w*4):
            continue
        if cv2.contourArea(contour) < w*h*0.65:
            continue
        rail = max(2, round(w*0.25))
        if x < rail or x+w+rail > width:
            continue
        left = gray[y:y+h, x-rail:x]
        right = gray[y:y+h, x+w:x+w+rail]
        if (left < 90).mean() > 0.45 and (right < 90).mean() > 0.45:
            return True
    return False


def cast_with_recovery(cast, recover, max_retries=2):
    """At most three cast attempts; never toggle after a confirmed cast."""
    for attempt in range(max_retries+1):
        if cast():
            return True
        if attempt == max_retries:
            break
        print(f"Casting meter not confirmed; resetting rod ({attempt+1}/{max_retries}).")
        if not recover():
            print("Rod reset could not be verified; stopping recovery.")
            return False
    return False
