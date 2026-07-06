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
            self._load_templates()
        else:
            print(
                "Warning: opencv-python is not installed. VisionDetector will run in mock mode."
            )

    def _load_templates(self):
        """Load portrait templates from data/portraits/ for OpenCV matching."""
        if not self.portraits_dir.exists():
            return

        for file in self.portraits_dir.iterdir():
            if file.suffix in (".png", ".jpg", ".jpeg") and file.stem != ".gitkeep":
                img = cv2.imread(str(file))
                if img is not None:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    self.templates[file.stem] = gray
        print(
            f"Loaded {len(self.templates)} portrait templates for vision recognition."
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

            gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            resized_crop = cv2.resize(gray_crop, (100, 100))

            best_hero_id = None
            best_score = 0.0

            for hero_id, template in self.templates.items():
                res = cv2.matchTemplate(resized_crop, template, cv2.TM_CCOEFF_NORMED)
                score = res[0][0]
                if score > best_score:
                    best_score = score
                    best_hero_id = hero_id

            if best_score > 0.82 and best_hero_id:
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

                if count >= 3:
                    print(
                        f"VisionDetector: Stably detected {best_hero_id} in {category}[{idx}] with score {best_score:.2f}"
                    )
                    success = self.draft_manager.apply_action(best_hero_id)
                    if success:
                        self.detection_history.pop(slot_key, None)
                        self.on_match_callback()
            else:
                slot_key = f"{category}_{idx}"
                if slot_key in self.detection_history:
                    self.detection_history.pop(slot_key, None)
