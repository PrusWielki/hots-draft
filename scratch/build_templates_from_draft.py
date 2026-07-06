"""
Build draft templates from actual in-game screenshots.

Usage:
  1. Join a custom draft lobby in Heroes of the Storm.
  2. Pick or ban a hero - let the portrait appear in the draft slot.
  3. Run: uv run python scratch/build_templates_from_draft.py
  4. The script saves the crop of the ACTIVE slot as a template.
  5. Repeat for each hero you want to capture.

The saved templates will be stored in data/draft_templates/ and will be
preferred over the default portrait icons.
"""

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root / "backend"))

import cv2  # noqa: E402
import mss  # noqa: E402
import numpy as np  # noqa: E402

from app.detection.vision import DEFAULT_COORDINATES  # noqa: E402

OUTPUT_DIR = repo_root / "data" / "draft_templates"


def capture_slot(category: str, slot_idx: int) -> np.ndarray | None:
    """Capture a single draft slot from the primary monitor."""
    slots = DEFAULT_COORDINATES.get(category)
    if not slots or slot_idx >= len(slots):
        print(f"Invalid category/idx: {category}[{slot_idx}]")
        return None

    slot = slots[slot_idx]

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        height, width = img.shape[:2]
        scale_x = width / 2560.0
        scale_y = height / 1440.0

        x = int(slot["x"] * scale_x)
        y = int(slot["y"] * scale_y)
        w = int(slot["w"] * scale_x)
        h = int(slot["h"] * scale_y)

        if x < 0 or y < 0 or x + w > width or y + h > height:
            print(f"Slot out of bounds: {x},{y} {w}x{h}")
            return None

        return img[y : y + h, x : x + w]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Draft Template Builder")
    print("======================")
    print(f"Templates will be saved to: {OUTPUT_DIR}")
    print()

    while True:
        print("Enter hero_id and slot to capture (e.g. 'thrall ally_picks 4')")
        print("or 'q' to quit:")
        raw = input("> ").strip()

        if raw.lower() == "q":
            break

        parts = raw.split()
        if len(parts) != 3:
            print("Usage: <hero_id> <category> <slot_idx>")
            print("Categories: ally_picks, ally_bans, enemy_picks, enemy_bans")
            continue

        hero_id, category, idx_str = parts
        try:
            idx = int(idx_str)
        except ValueError:
            print("slot_idx must be an integer (0-based)")
            continue

        crop = capture_slot(category, idx)
        if crop is None:
            continue

        out_path = OUTPUT_DIR / f"{hero_id}.png"
        cv2.imwrite(str(out_path), crop)
        print(f"Saved {out_path.name} ({crop.shape[1]}x{crop.shape[0]}px)")

        # Show preview
        preview = cv2.resize(crop, (200, 200))
        cv2.imshow(f"Preview: {hero_id}", preview)
        cv2.waitKey(1500)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
