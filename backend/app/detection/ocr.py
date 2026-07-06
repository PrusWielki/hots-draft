"""
OCR-based pick-name detection using EasyOCR.

Reads the name banner at the bottom of each pick slot and maps the text
to a hero ID using the Polish/English name lookup table in name_map.py.

Only used for PICK slots — ban slots have no name tag and continue to use
template matching via vision.py.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

try:
    import easyocr  # type: ignore[import-untyped]

    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

from app.detection.name_map import name_to_hero_id

# EasyOCR reader is expensive to initialise; share a single instance.
_reader: "easyocr.Reader | None" = None


def _get_reader() -> "easyocr.Reader | None":
    global _reader
    if _reader is None and EASYOCR_AVAILABLE:
        import easyocr  # noqa: PLC0415

        # Polish + English; GPU auto-detected
        _reader = easyocr.Reader(["pl", "en"], gpu=True, verbose=False)
    return _reader


def extract_name_region(
    crop_bgr: "np.ndarray",
    is_ally: bool,
) -> "np.ndarray":
    """
    Extract the hero name banner from a pick slot crop.

    The crop passed here is already extended sideways (150 px left for ally /
    150 px right for enemy) so the full banner sweep is captured.  We take the
    vertical band that contains the hero name text (~55-82 % of slot height)
    and use the full width of the extended crop.
    """
    import cv2

    h, w = crop_bgr.shape[:2]
    name_y0 = int(h * 0.55)
    name_y1 = int(h * 0.82)

    # Use the full width — the banner text can be anywhere across the extended crop
    region = crop_bgr[name_y0:name_y1, :]

    # Upscale 3× for better OCR accuracy on small text
    scale = 3
    region = cv2.resize(
        region,
        (region.shape[1] * scale, region.shape[0] * scale),
        interpolation=cv2.INTER_CUBIC,
    )

    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    return clahe.apply(gray)


def ocr_hero_from_crop(
    crop_bgr: "np.ndarray",
    is_ally: bool,
    debug: bool = False,
) -> tuple[str | None, float]:
    """
    Run OCR on a pick slot crop and return (hero_id, confidence).

    Returns (None, 0.0) if no confident match.
    """
    reader = _get_reader()
    if reader is None:
        return None, 0.0

    name_region = extract_name_region(crop_bgr, is_ally=is_ally)

    results = reader.readtext(name_region, detail=1, paragraph=False)
    if not results:
        return None, 0.0

    # Noise patterns to skip: player tags, punctuation-only, very short text
    _NOISE_RE = re.compile(r"^(sl|si|[^a-zA-Z]+|.{1,2})$", re.IGNORECASE)

    def _is_player_name(t: str) -> bool:
        """Title-case single word → likely a player account name, not a hero name."""
        s = re.sub(r"[^a-zA-Z]", "", t)
        return len(s) >= 3 and s[0].isupper() and s[1:].islower()

    # Collect clean text segments with confidence
    texts: list[tuple[str, float]] = [
        (text, conf)
        for (_bbox, text, conf) in results
        if not _NOISE_RE.match(text.strip())
        and not _is_player_name(text.strip())
        and conf > 0.15
    ]

    if debug:
        print(f"  OCR raw results: {[(t, round(c, 4)) for _,t,c in results]}")
        print(f"  OCR clean segments: {texts}")

    # Try each segment from highest confidence, combining adjacent ones
    best_id: str | None = None
    best_conf = 0.0

    # Try individual segments
    for text, conf in sorted(texts, key=lambda x: x[1], reverse=True):
        hero_id = name_to_hero_id(text)
        if hero_id and conf > best_conf:
            best_id = hero_id
            best_conf = conf

    # Try concatenating all segments (catches "SIERZANT" + "PETARDA" → sgt-hammer)
    if not best_id:
        combined = " ".join(t for t, _ in texts)
        avg_conf = sum(c for _, c in texts) / len(texts) if texts else 0.0
        hero_id = name_to_hero_id(combined)
        if hero_id:
            best_id = hero_id
            best_conf = avg_conf

    return best_id, best_conf


def ocr_available() -> bool:
    return EASYOCR_AVAILABLE
