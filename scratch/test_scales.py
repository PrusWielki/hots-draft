import sys
from pathlib import Path

# Add backend directory to path
repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root / "backend"))

import cv2  # noqa: E402


def test_scales():
    portraits_dir = repo_root / "data" / "portraits"
    debug_dir = repo_root / "data" / "debug_crops"

    if not portraits_dir.exists() or not debug_dir.exists():
        print("Missing directories.")
        return

    # Load templates in grayscale
    templates = {}
    for file in portraits_dir.iterdir():
        if file.suffix in (".png", ".jpg", ".jpeg") and file.stem != ".gitkeep":
            img = cv2.imread(str(file))
            if img is not None:
                templates[file.stem] = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    # Let's test enemy_picks_1.png (which is Medivh)
    crop_path = debug_dir / "enemy_picks_1.png"
    crop_bgr = cv2.imread(str(crop_path))
    if crop_bgr is None:
        print("Failed to read crop.")
        return

    gray_crop = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    resized_crop = cv2.resize(gray_crop, (100, 100))
    cl_crop = clahe.apply(resized_crop)

    # Let's try to match Medivh at multiple scales
    print("\nMatching enemy_picks_1.png (Medivh) at multiple scales:")
    # We will test scales of the template from 0.4 to 1.0
    scales = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    best_scale_matches = []

    for scale in scales:
        scale_matches = []
        for name, t in templates.items():
            # Resize template to scale
            w = int(t.shape[1] * scale)
            h = int(t.shape[0] * scale)
            if w < 10 or h < 10:
                continue
            resized_t = cv2.resize(t, (w, h))
            cl_t = clahe.apply(resized_t)

            # Match inside cl_crop
            res = cv2.matchTemplate(cl_crop, cl_t, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            scale_matches.append((name, max_val))

        scale_matches.sort(key=lambda m: m[1], reverse=True)
        print(f"Scale {scale:.1f}:")
        for rank, (name, score) in enumerate(scale_matches[:3]):
            print(f"  #{rank+1} - {name}: {score:.3f}")
            if name == "medivh":
                best_scale_matches.append((scale, score))

    print("\nMedivh match history across scales:")
    for scale, score in best_scale_matches:
        print(f"  Scale {scale:.1f} score: {score:.3f}")


if __name__ == "__main__":
    test_scales()
