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


def get_active_slots(step_idx: int, action: str) -> list[int]:
    """Map draft step index in sequence to physical screen slot indexes.

    This accounts for double pick phases where players can lock in out-of-order.
    """
    if action == "ban":
        if step_idx in (0, 1):
            return [0]
        elif step_idx in (2, 3):
            return [1]
        elif step_idx in (9, 10):
            return [2]
    elif action == "pick":
        return [0, 1, 2, 3, 4]
    return []


class VisionDetector(BaseDetector):
    """OpenCV-based screen detection for HotS draft."""

    def __init__(
        self,
        portraits_dir: Path,
        draft_manager: Any,
        on_match_callback: Any,
        on_debug_callback: Optional[Any] = None,
    ):
        super().__init__()
        self.portraits_dir = portraits_dir
        self.draft_manager = draft_manager
        self.on_match_callback = on_match_callback
        self.on_debug_callback = on_debug_callback
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.pick_templates: Dict[str, Any] = {}
        self.ban_templates: Dict[str, Any] = {}
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

        Separates templates into picks and bans, using clean portraits as fallback.
        """
        import numpy as np

        portraits_dir = self.portraits_dir
        draft_dir = self.portraits_dir.parent / "draft_templates"
        picks_dir = draft_dir / "picks"
        bans_dir = draft_dir / "bans"

        scales = [0.5, 0.6, 0.7, 0.8, 0.9]
        border = 0.15

        # Check if the ban overlay model is available
        model_w_path = portraits_dir.parent / "ban_model_w.png"
        model_overlay_path = portraits_dir.parent / "ban_model_overlay.png"
        has_ban_model = model_w_path.exists() and model_overlay_path.exists()

        W = None
        Overlay = None
        if has_ban_model:
            w_img = cv2.imread(str(model_w_path), cv2.IMREAD_GRAYSCALE)
            overlay_img = cv2.imread(str(model_overlay_path))
            if w_img is not None and overlay_img is not None:
                W = w_img.astype(float) / 255.0
                Overlay = overlay_img.astype(float)

        def load_variants(src, is_draft=False):
            if isinstance(src, (str, Path)):
                img = cv2.imread(str(src))
            else:
                img = src  # already a numpy array BGR image
            if img is None:
                return None
            if is_draft:
                h, w = img.shape[:2]
                cx, cy = w // 2, h // 2
                side = min(w, h)
                img = img[
                    cy - side // 2 : cy - side // 2 + side,
                    cx - side // 2 : cx - side // 2 + side,
                ]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if is_draft:
                h, w = gray.shape
                b_h, b_w = int(h * border), int(w * border)
                gray = gray[b_h : h - b_h, b_w : w - b_w]
            base = cv2.resize(gray, (100, 100))
            return [
                self.clahe.apply(cv2.resize(base, (int(100 * s), int(100 * s))))
                for s in scales
            ]

        # 1. Load clean portraits as baseline for picks, and synthesize/load for bans
        for file in portraits_dir.iterdir():
            if file.suffix not in (".png", ".jpg", ".jpeg") or file.stem == ".gitkeep":
                continue

            clean_img = cv2.imread(str(file))
            if clean_img is None:
                continue

            # Pick template baseline
            pick_vars = load_variants(clean_img, is_draft=False)
            if pick_vars:
                self.pick_templates[file.stem] = pick_vars

            # Ban template baseline
            if W is not None and Overlay is not None:
                # Synthesize BGR ban template
                # Resize clean image to 120x120 model size first
                clean_resized = cv2.resize(clean_img, (120, 120))
                synth = np.zeros((120, 120, 3), dtype=np.float64)
                for c in range(3):
                    synth[:, :, c] = clean_resized[:, :, c] * W + Overlay[:, :, c]
                synth = np.clip(synth, 0, 255).astype(np.uint8)

                # Load variants with is_draft=True because it contains the overlay & border
                ban_vars = load_variants(synth, is_draft=True)
            else:
                # Fallback to plain portrait
                ban_vars = load_variants(clean_img, is_draft=False)

            if ban_vars:
                self.ban_templates[file.stem] = ban_vars

        # 2. Overwrite with specific pick draft templates if present
        picks_count = 0
        if picks_dir.exists():
            for file in picks_dir.iterdir():
                if file.suffix in (".png", ".jpg", ".jpeg") and file.stem != ".gitkeep":
                    variants = load_variants(file, is_draft=True)
                    if variants:
                        self.pick_templates[file.stem] = variants
                        picks_count += 1

        # 3. Overwrite with specific ban draft templates if present
        bans_count = 0
        if bans_dir.exists():
            for file in bans_dir.iterdir():
                if file.suffix in (".png", ".jpg", ".jpeg") and file.stem != ".gitkeep":
                    variants = load_variants(file, is_draft=True)
                    if variants:
                        self.ban_templates[file.stem] = variants
                        bans_count += 1

        print(
            f"Loaded templates: {len(self.pick_templates)} picks ({picks_count} draft crops), "
            f"{len(self.ban_templates)} bans ({bans_count} draft crops)."
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

                if OPENCV_AVAILABLE and (self.pick_templates or self.ban_templates):
                    self._perform_detection()
                else:
                    time.sleep(2.0)
            except Exception as e:
                print(f"Error in vision detection loop: {e}")
                time.sleep(5.0)
            time.sleep(0.8)

    def capture_active_slot_as_template(self, hero_id: str):
        """Capture the screen region of the current active slot and save it as a template for hero_id."""
        if not OPENCV_AVAILABLE or not (self.pick_templates or self.ban_templates):
            return

        step = self.draft_manager.get_current_step()
        if not step:
            return

        category = None
        if step.action == "pick":
            category = "ally_picks" if step.team == "my_team" else "enemy_picks"
        elif step.action == "ban":
            category = "ally_bans" if step.team == "my_team" else "enemy_bans"

        if not category:
            return

        active_indices = get_active_slots(
            self.draft_manager.current_step_idx, step.action
        )
        if not active_indices:
            return

        idx = active_indices[0]
        if idx >= len(self.coordinates[category]):
            return

        slot = self.coordinates[category][idx]

        import mss
        import numpy as np

        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                width = monitor["width"]
                height = monitor["height"]

                sct_img = sct.grab(monitor)
                img_bgr = np.array(sct_img)
                img_bgr = cv2.cvtColor(img_bgr, cv2.COLOR_BGRA2BGR)

                scale_x = width / 2560.0
                scale_y = height / 1440.0

                x = int(slot["x"] * scale_x)
                y = int(slot["y"] * scale_y)
                w = int(slot["w"] * scale_x)
                h = int(slot["h"] * scale_y)

                if x < 0 or y < 0 or x + w > width or y + h > height:
                    return

                cx, cy = x + w // 2, y + h // 2
                side = min(w, h)
                x_sq = max(0, cx - side // 2)
                y_sq = max(0, cy - side // 2)
                sq_side = min(width - x_sq, height - y_sq, side)
                square_crop = img_bgr[y_sq : y_sq + sq_side, x_sq : x_sq + sq_side]

                if square_crop.size > 0:
                    subfolder = "picks" if step.action == "pick" else "bans"
                    save_dir = self.portraits_dir.parent / "draft_templates" / subfolder
                    save_dir.mkdir(parents=True, exist_ok=True)
                    save_path = save_dir / f"{hero_id}.png"

                    cv2.imwrite(str(save_path), square_crop)
                    print(
                        f"VisionDetector: Dynamically captured and saved {step.action} template for '{hero_id}' to {save_path}"
                    )

                    # Load template immediately into memory
                    gray = cv2.cvtColor(square_crop, cv2.COLOR_BGR2GRAY)
                    scales = [0.85, 0.9, 0.95, 1.0, 1.05]
                    variants = []
                    for s in scales:
                        target_w = int(100 * s)
                        target_h = int(100 * s)
                        resized = cv2.resize(gray, (target_w, target_h))
                        clahe_img = self.clahe.apply(resized)
                        variants.append(clahe_img)

                    if step.action == "pick":
                        self.pick_templates[hero_id] = variants
                    else:
                        self.ban_templates[hero_id] = variants
        except Exception as e:
            print(f"Error dynamically capturing template: {e}")

    def _match_templates(
        self, square_crop, action: str, match_top_only=False
    ) -> tuple[Optional[str], float]:
        templates_dict = self.pick_templates if action == "pick" else self.ban_templates
        if not templates_dict:
            return None, 0.0

        gray_crop = cv2.cvtColor(square_crop, cv2.COLOR_BGR2GRAY)

        # Skip template matching if this is a pick slot and it is empty/dark (intensity < 40.0)
        if action == "pick" and gray_crop.mean() < 40.0:
            return None, 0.0

        resized_crop = cv2.resize(gray_crop, (100, 100))
        cl_crop = self.clahe.apply(resized_crop)

        if match_top_only:
            # Crop top 60% of height to bypass the red/blue ban overlay bar at the bottom
            cl_crop = cl_crop[0:60, :]

        best_hero_id = None
        best_score = 0.0

        for hero_id, variants in templates_dict.items():
            for template in variants:
                t_temp = template
                if match_top_only:
                    t_temp = template[0:60, :]

                if (
                    t_temp.shape[0] > cl_crop.shape[0]
                    or t_temp.shape[1] > cl_crop.shape[1]
                ):
                    continue

                res = cv2.matchTemplate(cl_crop, t_temp, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val > best_score:
                    best_score = max_val
                    best_hero_id = hero_id

        return best_hero_id, best_score

    def _perform_detection(self):
        """Capture active slots for the current draft step and compare against templates."""
        import mss
        import numpy as np

        step = self.draft_manager.get_current_step()
        if not step:
            return

        category = None
        if step.action == "pick":
            category = "ally_picks" if step.team == "my_team" else "enemy_picks"
        elif step.action == "ban":
            category = "ally_bans" if step.team == "my_team" else "enemy_bans"

        if category is None:
            return

        # Find which slot index is active for this step.
        # For ban steps: use the static mapping (step_idx → ban slot position).
        # For pick steps: the next slot to fill is simply the current count of
        #   picks already recorded for this team — never scan ahead, which would
        #   cause hovers / prepicks in future slots to fire prematurely.
        if step.action == "ban":
            active_indices = get_active_slots(
                self.draft_manager.current_step_idx, step.action
            )
        else:
            # Picks can happen in any visual order on the screen, so scan all 5 slots
            active_indices = [0, 1, 2, 3, 4]

        if not active_indices:
            return

        debug_slots = []
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)
            img_bgr = np.array(screenshot)
            if img_bgr.shape[2] == 4:
                img_bgr = cv2.cvtColor(img_bgr, cv2.COLOR_BGRA2BGR)

            height, width = img_bgr.shape[:2]
            scale_x = width / 2560.0
            scale_y = height / 1440.0

            # Scan all active slot indices in this step
            for idx in active_indices:
                if idx >= len(self.coordinates[category]):
                    continue

                slot = self.coordinates[category][idx]
                x = int(slot["x"] * scale_x)
                y = int(slot["y"] * scale_y)
                w = int(slot["w"] * scale_x)
                h = int(slot["h"] * scale_y)

                if x < 0 or y < 0 or x + w > width or y + h > height:
                    continue

                crop = img_bgr[y : y + h, x : x + w]
                if crop.size == 0:
                    continue

                # Make a perfect square crop centered on the slot to avoid aspect ratio distortion during resizing
                cx, cy = x + w // 2, y + h // 2
                side = min(w, h)
                x_sq = max(0, cx - side // 2)
                y_sq = max(0, cy - side // 2)
                sq_side = min(width - x_sq, height - y_sq, side)
                square_crop = img_bgr[y_sq : y_sq + sq_side, x_sq : x_sq + sq_side]
                if square_crop.size == 0:
                    square_crop = crop

                best_hero_id: Optional[str] = None
                best_score = 0.0
                match_method = "unknown"

                if step.action == "pick":
                    # 1. Fast template matching first (bypass slow OCR if we have high-confidence match)
                    t_hero, t_score = self._match_templates(square_crop, action="pick")
                    if t_hero and t_score >= 0.85:
                        best_hero_id = t_hero
                        best_score = t_score
                        match_method = "template_fast"

                    # 2. OCR fallback
                    if best_hero_id is None:
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
                            hero_id, conf = ocr_hero_from_crop(
                                ocr_crop, is_ally=is_ally
                            )
                            if hero_id and conf > 0.4:
                                best_hero_id = hero_id
                                best_score = conf
                                match_method = "ocr"
                                print(
                                    f"VisionDetector OCR: '{hero_id}' in {category}[{idx}] (conf={conf:.2f})"
                                )

                    # 3. Soft template matching fallback (0.75 <= score < 0.85) if OCR didn't find anything
                    if best_hero_id is None and t_hero and t_score >= 0.75:
                        best_hero_id = t_hero
                        best_score = t_score
                        match_method = "template_soft"

                else:  # ban step
                    # 1. Try full template matching
                    t_hero, t_score = self._match_templates(square_crop, action="ban")
                    if t_hero and t_score >= 0.75:
                        best_hero_id = t_hero
                        best_score = t_score
                        match_method = "template_full"
                    else:
                        # 2. Try top-half-only template matching to bypass the red/blue ban overlay bar
                        t_hero, t_score = self._match_templates(
                            square_crop, action="ban", match_top_only=True
                        )
                        if t_hero and t_score >= 0.70:
                            best_hero_id = t_hero
                            best_score = t_score
                            match_method = "template_top_only"

                # Process stability tracking for this slot index
                slot_key = f"{category}_{idx}"

                # Ignore already picked or banned heroes
                is_already_taken = (
                    (
                        best_hero_id in self.draft_manager.my_team_picks
                        or best_hero_id in self.draft_manager.enemy_picks
                        or best_hero_id in self.draft_manager.my_team_bans
                        or best_hero_id in self.draft_manager.enemy_bans
                    )
                    if best_hero_id
                    else False
                )

                # Capture debug info before potential state advance
                import base64

                crop_base64 = ""
                try:
                    _, buffer = cv2.imencode(".jpg", square_crop)
                    crop_base64 = "data:image/jpeg;base64," + base64.b64encode(
                        buffer
                    ).decode("utf-8")
                except Exception as e:
                    print(f"Failed to encode debug crop: {e}")

                try:
                    gray_tmp = cv2.cvtColor(square_crop, cv2.COLOR_BGR2GRAY)
                    mean_val = float(gray_tmp.mean())
                except Exception:
                    mean_val = 0.0
                is_empty = mean_val < 40.0

                _, current_count = self.detection_history.get(slot_key, (None, 0))

                # If stable match is about to succeed, increment count for debug representation
                debug_count = current_count
                if best_hero_id and not is_already_taken:
                    current_candidate, _ = self.detection_history.get(
                        slot_key, (None, 0)
                    )
                    if current_candidate == best_hero_id:
                        debug_count += 1
                    else:
                        debug_count = 1

                display_hero_id = best_hero_id
                display_score = best_score
                display_method = match_method
                if display_hero_id is None and "t_hero" in locals() and t_hero:
                    display_hero_id = t_hero
                    display_score = t_score
                    display_method = "below_threshold"

                debug_slots.append(
                    {
                        "category": category,
                        "idx": idx,
                        "crop_base64": crop_base64,
                        "best_hero_id": display_hero_id,
                        "best_score": float(display_score),
                        "match_method": display_method,
                        "is_empty": bool(is_empty),
                        "is_already_taken": bool(is_already_taken),
                        "stability_count": int(debug_count),
                    }
                )

                if best_hero_id and not is_already_taken:
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
                            break  # Stop scanning other slots in this frame after successful match to allow step state to advance
                        else:
                            print(
                                f"VisionDetector: Attempted to apply '{best_hero_id}' in {category}[{idx}] but draft manager rejected it (already picked/banned or invalid step)."
                            )
                else:
                    if slot_key in self.detection_history:
                        self.detection_history.pop(slot_key, None)

        if self.on_debug_callback and debug_slots:
            self.on_debug_callback({"timestamp": time.time(), "slots": debug_slots})
