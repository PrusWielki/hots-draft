import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from app.detection.base import BaseDetector

try:
    import cv2

    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

DEFAULT_COORDINATES = {
    "ally_picks": [
        {"x": 41, "y": 73, "w": 249, "h": 258},
        {"x": 173, "y": 317, "w": 226, "h": 241},
        {"x": 29, "y": 535, "w": 237, "h": 268},
        {"x": 182, "y": 765, "w": 215, "h": 262},
        {"x": 37, "y": 994, "w": 232, "h": 246},
    ],
    "enemy_picks": [
        {"x": 2286, "y": 76, "w": 219, "h": 268},
        {"x": 2137, "y": 302, "w": 254, "h": 268},
        {"x": 2280, "y": 533, "w": 233, "h": 257},
        {"x": 2160, "y": 754, "w": 229, "h": 279},
        {"x": 2270, "y": 998, "w": 236, "h": 241},
    ],
    "ally_bans": [
        {"x": 352, "y": 9, "w": 132, "h": 136},
        {"x": 488, "y": 10, "w": 123, "h": 131},
        {"x": 612, "y": 10, "w": 147, "h": 131},
    ],
    "enemy_bans": [
        {"x": 1824, "y": 8, "w": 119, "h": 133},
        {"x": 1953, "y": 7, "w": 126, "h": 141},
        {"x": 2086, "y": 10, "w": 121, "h": 130},
    ],
}


class VisionDetector(BaseDetector):
    """OpenCV-based screen detection for HotS draft."""

    def __init__(self, portraits_dir: Path, draft_manager: Any, on_match_callback: Any):
        super().__init__()
        self.portraits_dir = portraits_dir
        self.draft_manager = draft_manager
        self.on_match_callback = on_match_callback
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.templates: Dict[str, Any] = {}
        self.coordinates = DEFAULT_COORDINATES
        self.detection_history: Dict[str, tuple[str, int]] = {}
        self.cooldown_until = 0.0

        if OPENCV_AVAILABLE:
            self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            self._load_templates()
        else:
            self.clahe = None
            print(
                "Warning: opencv-python is not installed. VisionDetector will run in mock mode."
            )

    def _load_templates(self):
        """Load portrait templates for OpenCV matching.

        Prefers real draft crops when available and pre-generates scaled
        variants to handle size differences.
        """
        portraits_dir = self.portraits_dir
        draft_dir = self.portraits_dir.parent / "draft_templates"

        scales = [0.5, 0.6, 0.7, 0.8, 0.9]
        border = 0.15
        for file in portraits_dir.iterdir():
            if file.suffix not in (".png", ".jpg", ".jpeg") or file.stem == ".gitkeep":
                continue
            draft_file = draft_dir / file.name
            is_draft = draft_file.exists()
            src = draft_file if is_draft else file
            img = cv2.imread(str(src))
            if img is not None:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                if is_draft:
                    h, w = gray.shape
                    b_h, b_w = int(h * border), int(w * border)
                    gray = gray[b_h : h - b_h, b_w : w - b_w]
                base = cv2.resize(gray, (100, 100))
                variants = []
                for s in scales:
                    w_s = int(100 * s)
                    h_s = int(100 * s)
                    scaled = cv2.resize(base, (w_s, h_s))
                    cl = self.clahe.apply(scaled)
                    variants.append(cl)
                self.templates[file.stem] = variants

        if draft_dir.exists():
            for file in draft_dir.iterdir():
                if (
                    file.suffix in (".png", ".jpg", ".jpeg")
                    and file.stem not in self.templates
                ):
                    img = cv2.imread(str(file))
                    if img is not None:
                        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        h, w = gray.shape
                        b_h, b_w = int(h * border), int(w * border)
                        gray = gray[b_h : h - b_h, b_w : w - b_w]
                        base = cv2.resize(gray, (100, 100))
                        self.templates[file.stem] = [
                            self.clahe.apply(
                                cv2.resize(base, (int(100 * s), int(100 * s)))
                            )
                            for s in scales
                        ]

        draft_count = (
            sum(1 for f in portraits_dir.iterdir() if (draft_dir / f.name).exists())
            if draft_dir.exists()
            else 0
        )
        print(
            f"Loaded {len(self.templates)} portrait templates "
            f"({draft_count} using real draft crops, {len(scales)} scales each)."
        )

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("VisionDetector background thread started.")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        print("VisionDetector background thread stopped.")

    def trigger_cooldown(self, seconds: float = 5.0):
        """Set a detection cooldown to prevent overriding manual overrides."""
        self.cooldown_until = time.time() + seconds

    def _loop(self):
        """Main detection loop running periodically."""
        while self.running:
            try:
                if time.time() < self.cooldown_until:
                    time.sleep(0.5)
                    continue

                if OPENCV_AVAILABLE and self.templates:
                    self._perform_detection()
                else:
                    time.sleep(2.0)
            except Exception as e:
                print(f"Error in vision detection loop: {e}")
                time.sleep(5.0)
            time.sleep(0.8)

    def _perform_detection(self):
        """Capture the target active slot and compare against templates."""
        import mss
        import numpy as np

        step = self.draft_manager.get_current_step()
        if not step:
            return

        category = None
        idx = None

        if step.action == "pick":
            if step.team == "my_team":
                category = "ally_picks"
                idx = len(self.draft_manager.my_team_picks)
            else:
                category = "enemy_picks"
                idx = len(self.draft_manager.enemy_picks)
        elif step.action == "ban":
            if step.team == "my_team":
                category = "ally_bans"
                idx = len(self.draft_manager.my_team_bans)
            else:
                category = "enemy_bans"
                idx = len(self.draft_manager.enemy_bans)

        if category is None or idx is None:
            return

        if idx >= len(self.coordinates[category]):
            return

        slot = self.coordinates[category][idx]

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)
            img_bgr = np.array(screenshot)
            if img_bgr.shape[2] == 4:
                img_bgr = cv2.cvtColor(img_bgr, cv2.COLOR_BGRA2BGR)

            height, width = img_bgr.shape[:2]
            scale_x = width / 2560.0
            scale_y = height / 1440.0

            x = int(slot["x"] * scale_x)
            y = int(slot["y"] * scale_y)
            w = int(slot["w"] * scale_x)
            h = int(slot["h"] * scale_y)

            if x < 0 or y < 0 or x + w > width or y + h > height:
                return

            crop = img_bgr[y : y + h, x : x + w]
            if crop.size == 0:
                return

            best_hero_id: Optional[str] = None
            best_score = 0.0

            if step.action == "pick":
                from app.detection.ocr import (  # noqa: PLC0415
                    ocr_available,
                    ocr_hero_from_crop,
                )

                if ocr_available():
                    is_ally = category == "ally_picks"
                    BANNER_PAD = 150
                    if is_ally:
                        x_ocr = max(0, x - BANNER_PAD)
                        w_ocr = (x + w) - x_ocr
                    else:
                        x_ocr = x
                        w_ocr = min(width - x_ocr, w + BANNER_PAD)
                    ocr_crop = img_bgr[y : y + h, x_ocr : x_ocr + w_ocr]
                    hero_id, conf = ocr_hero_from_crop(ocr_crop, is_ally=is_ally)
                    if hero_id and conf > 0.4:
                        best_hero_id = hero_id
                        best_score = conf
                        print(
                            f"VisionDetector OCR: '{hero_id}' in {category}[{idx}] (conf={conf:.2f})"
                        )

                # Fallback to template matching if OCR didn't fire
                if best_hero_id is None and self.templates:
                    gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    resized_crop = cv2.resize(gray_crop, (100, 100))
                    cl_crop = self.clahe.apply(resized_crop)
                    for hero_id, variants in self.templates.items():
                        for template in variants:
                            if (
                                template.shape[0] > cl_crop.shape[0]
                                or template.shape[1] > cl_crop.shape[1]
                            ):
                                continue
                            res = cv2.matchTemplate(
                                cl_crop, template, cv2.TM_CCOEFF_NORMED
                            )
                            _, max_val, _, _ = cv2.minMaxLoc(res)
                            if max_val > best_score:
                                best_score = max_val
                                best_hero_id = hero_id
                    if best_score < 0.75:
                        best_hero_id = None

            else:
                gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                resized_crop = cv2.resize(gray_crop, (100, 100))
                cl_crop = self.clahe.apply(resized_crop)
                for hero_id, variants in self.templates.items():
                    for template in variants:
                        if (
                            template.shape[0] > cl_crop.shape[0]
                            or template.shape[1] > cl_crop.shape[1]
                        ):
                            continue
                        res = cv2.matchTemplate(cl_crop, template, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, _ = cv2.minMaxLoc(res)
                        if max_val > best_score:
                            best_score = max_val
                            best_hero_id = hero_id
                if best_score < 0.75:
                    best_hero_id = None

            if best_hero_id:
                slot_key = f"{category}_{idx}"
                current_candidate, count = self.detection_history.get(
                    slot_key, (None, 0)
                )

                if current_candidate == best_hero_id:
                    count += 1
                else:
                    current_candidate = best_hero_id
                    count = 1

                self.detection_history[slot_key] = (current_candidate, count)

                if count >= 2:
                    print(
                        f"VisionDetector: Stably detected {best_hero_id} in {category}[{idx}] with score {best_score:.2f}"
                    )
                    success = self.draft_manager.apply_action(best_hero_id)
                    self.detection_history.pop(slot_key, None)
                    if success:
                        self.on_match_callback()
                    else:
                        print(
                            f"VisionDetector: Attempted to apply '{best_hero_id}' in {category}[{idx}] but draft manager rejected it (already picked/banned or invalid step)."
                        )
            else:
                slot_key = f"{category}_{idx}"
                if slot_key in self.detection_history:
                    self.detection_history.pop(slot_key, None)
