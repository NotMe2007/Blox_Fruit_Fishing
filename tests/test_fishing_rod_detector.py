"""Unit tests for the fishing rod detector heuristics."""

import pathlib
import sys

import cv2
import numpy as np

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Logic.BackGround_Logic import Fishing_Rod_Detector as rod_detector

IMAGES_DIR = PROJECT_ROOT / "Images"
EQ_PATH = IMAGES_DIR / "Basic_Fishing_EQ.png"
UN_PATH = IMAGES_DIR / "Basic_Fishing_UN.png"


def _load_gray(path: pathlib.Path) -> np.ndarray:
    image = cv2.imread(str(path))
    if image is None:
        raise AssertionError(f"Failed to load template: {path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def test_eq_letters_match_better_than_un_letters():
    eq_gray = _load_gray(EQ_PATH)
    un_gray = _load_gray(UN_PATH)

    match_size = (eq_gray.shape[1], eq_gray.shape[0])
    eq_score = rod_detector._compute_letter_similarity(eq_gray, (0, 0), match_size, eq_gray)
    un_score = rod_detector._compute_letter_similarity(eq_gray, (0, 0), match_size, un_gray)

    assert eq_score is not None and un_score is not None
    assert eq_score >= rod_detector.LETTER_SCORE_THRESHOLD
    assert eq_score >= un_score + rod_detector.LETTER_DIFF_MARGIN / 2


def test_un_letters_match_better_than_eq_letters():
    eq_gray = _load_gray(EQ_PATH)
    un_gray = _load_gray(UN_PATH)

    match_size = (un_gray.shape[1], un_gray.shape[0])
    un_score = rod_detector._compute_letter_similarity(un_gray, (0, 0), match_size, un_gray)
    eq_score = rod_detector._compute_letter_similarity(un_gray, (0, 0), match_size, eq_gray)

    assert un_score is not None and eq_score is not None
    assert un_score >= rod_detector.LETTER_SCORE_THRESHOLD
    assert un_score >= eq_score + rod_detector.LETTER_DIFF_MARGIN / 2
