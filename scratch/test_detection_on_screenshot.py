import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import cv2  # noqa: E402
from app.detection.vision import VisionDetector, get_active_slots  # noqa: E402
from app.draft import DraftManager  # noqa: E402

# Load the debug screenshot
repo_root = backend_dir.parent
screenshot_path = repo_root / "data" / "debug_crops" / "full_screenshot.png"
if not screenshot_path.exists():
    print(f"Error: {screenshot_path} not found!")
    sys.exit(1)

img = cv2.imread(str(screenshot_path))
h_orig, w_orig = img.shape[:2]
print(f"Loaded debug screenshot: {w_orig}x{h_orig}")


# Monkeypatch mss
class MockSct:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @property
    def monitors(self):
        return [None, {"left": 0, "top": 0, "width": w_orig, "height": h_orig}]

    def grab(self, monitor):
        return img.copy()


import mss  # noqa: E402

mss.mss = MockSct

# Initialize DraftManager and VisionDetector
draft_manager = DraftManager()
detector = VisionDetector(
    portraits_dir=repo_root / "data" / "portraits",
    draft_manager=draft_manager,
    on_match_callback=lambda: None,
)

print("\n--- Running step-by-step detection on full_screenshot.png ---")

# Let's run through all 16 steps of the draft
for step_idx in range(16):
    step = draft_manager.get_current_step()
    if not step:
        print("Draft complete!")
        break

    print(f"\nStep {step_idx}: {step.action} for {step.team}")

    # We will invoke the detection logic for this step multiple times to satisfy stability checks.
    for _ in range(3):
        detector._perform_detection()
        if draft_manager.get_current_step() != step:
            break

    # If the step didn't advance, it means detection failed.
    next_step = draft_manager.get_current_step()
    if next_step == step:
        print(
            f"  ==> DETECTION FAILED for Step {step_idx} ({step.action} {step.team}). Stopping."
        )

        if step.action == "pick":
            category = "ally_picks" if step.team == "my_team" else "enemy_picks"
        else:
            category = "ally_bans" if step.team == "my_team" else "enemy_bans"

        active_indices = get_active_slots(step_idx, step.action)
        print(f"  Debug active slots for {category}: {active_indices}")
        for idx in active_indices:
            slot = detector.coordinates[category][idx]
            scale_x = w_orig / 2560.0
            scale_y = h_orig / 1440.0
            x = int(slot["x"] * scale_x)
            y = int(slot["y"] * scale_y)
            w = int(slot["w"] * scale_x)
            h = int(slot["h"] * scale_y)

            # Template match debug
            cx, cy = x + w // 2, y + h // 2
            side = min(w, h)
            x_sq = max(0, cx - side // 2)
            y_sq = max(0, cy - side // 2)
            sq_side = min(w_orig - x_sq, h_orig - y_sq, side)
            square_crop = img[y_sq : y_sq + sq_side, x_sq : x_sq + sq_side]

            gray_crop = cv2.cvtColor(square_crop, cv2.COLOR_BGR2GRAY)
            resized_crop = cv2.resize(gray_crop, (100, 100))
            cl_crop = detector.clahe.apply(resized_crop)

            best_hero = None
            best_score = 0.0
            templates_dict = (
                detector.pick_templates
                if step.action == "pick"
                else detector.ban_templates
            )
            for hero_id, variants in templates_dict.items():
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
                        best_hero = hero_id
            print(
                f"    Slot [{idx}] center matching: best match = '{best_hero}' with score = {best_score:.3f}"
            )

            # Run grid search to find the optimal offset for this slot matching 'rehgar'
            best_dx, best_dy, opt_score = 0, 0, 0.0
            for dx in range(-25, 25):
                for dy in range(-25, 25):
                    x_try = x + dx
                    y_try = y + dy
                    cx_try, cy_try = x_try + w // 2, y_try + h // 2
                    x_sq_try = max(0, cx_try - side // 2)
                    y_sq_try = max(0, cy_try - side // 2)
                    sq_side_try = min(w_orig - x_sq_try, h_orig - y_sq_try, side)
                    square_crop_try = img[
                        y_sq_try : y_sq_try + sq_side_try,
                        x_sq_try : x_sq_try + sq_side_try,
                    ]

                    gray_crop_try = cv2.cvtColor(square_crop_try, cv2.COLOR_BGR2GRAY)
                    resized_crop_try = cv2.resize(gray_crop_try, (100, 100))
                    cl_crop_try = detector.clahe.apply(resized_crop_try)

                    for template in (
                        detector.pick_templates
                        if step.action == "pick"
                        else detector.ban_templates
                    ).get("rehgar", []):
                        if (
                            template.shape[0] > cl_crop_try.shape[0]
                            or template.shape[1] > cl_crop_try.shape[1]
                        ):
                            continue
                        res_try = cv2.matchTemplate(
                            cl_crop_try, template, cv2.TM_CCOEFF_NORMED
                        )
                        _, max_val_try, _, _ = cv2.minMaxLoc(res_try)
                        if max_val_try > opt_score:
                            opt_score = max_val_try
                            best_dx = dx
                            best_dy = dy
            print(
                f"    Optimal coordinate offset for '{category}[{idx}]': dx={best_dx}, dy={best_dy} (x={slot['x'] + best_dx}, y={slot['y'] + best_dy}) -> score={opt_score:.3f}"
            )
        break
    else:
        # Step advanced! Print what was added
        print("  ==> Step ADVANCED! Current state:")
        print(f"      My Bans: {draft_manager.my_team_bans}")
        print(f"      Enemy Bans: {draft_manager.enemy_bans}")
        print(f"      My Picks: {draft_manager.my_team_picks}")
        print(f"      Enemy Picks: {draft_manager.enemy_picks}")
