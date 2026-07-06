import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root / "backend"))

import cv2  # noqa: E402


def analyze():
    portraits_dir = repo_root / "data" / "portraits"
    debug_dir = repo_root / "data" / "debug_crops"

    if not portraits_dir.exists() or not debug_dir.exists():
        print(
            "Missing directories. Make sure data/portraits and data/debug_crops exist."
        )
        return

    templates = {}
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    for file in portraits_dir.iterdir():
        if file.suffix in (".png", ".jpg", ".jpeg") and file.stem != ".gitkeep":
            img = cv2.imread(str(file))
            if img is not None:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                resized = cv2.resize(gray, (100, 100))
                templates[file.stem] = {
                    "raw": resized,
                    "clahe": clahe.apply(resized),
                    "canny": cv2.Canny(resized, 50, 150),
                }
    print(f"Loaded {len(templates)} templates.")

    crop_files = sorted(list(debug_dir.glob("*.png")))
    for crop_file in crop_files:
        if crop_file.name == "full_screenshot.png":
            continue

        print("\n==========================================")
        print(f"Analyzing Crop: {crop_file.name}")
        print("==========================================")

        crop_bgr = cv2.imread(str(crop_file))
        if crop_bgr is None:
            print("Failed to read crop.")
            continue

        gray_crop = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        resized_crop = cv2.resize(gray_crop, (100, 100))
        clahe_crop = clahe.apply(resized_crop)
        canny_crop = cv2.Canny(resized_crop, 50, 150)

        std_matches = []
        for name, t in templates.items():
            res = cv2.matchTemplate(resized_crop, t["raw"], cv2.TM_CCOEFF_NORMED)
            score = res[0][0]
            std_matches.append((name, score))
        std_matches.sort(key=lambda m: m[1], reverse=True)

        center_crop = clahe_crop[10:90, 10:90]
        face_matches = []
        for name, t in templates.items():
            t_face = t["clahe"][20:80, 20:80]
            res = cv2.matchTemplate(center_crop, t_face, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            face_matches.append((name, max_val))
        face_matches.sort(key=lambda m: m[1], reverse=True)

        canny_matches = []
        center_canny_crop = canny_crop[10:90, 10:90]
        for name, t in templates.items():
            t_face_canny = t["canny"][20:80, 20:80]
            res = cv2.matchTemplate(
                center_canny_crop, t_face_canny, cv2.TM_CCOEFF_NORMED
            )
            _, max_val, _, _ = cv2.minMaxLoc(res)
            canny_matches.append((name, max_val))
        canny_matches.sort(key=lambda m: m[1], reverse=True)

        face_matches_v2 = []
        crop_search = clahe_crop[15:70, 20:80]
        for name, t in templates.items():
            t_face = t["clahe"][20:60, 27:72]
            res = cv2.matchTemplate(crop_search, t_face, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            face_matches_v2.append((name, max_val))
        face_matches_v2.sort(key=lambda m: m[1], reverse=True)

        print("Method 1 (Standard 1:1 Raw):")
        for name, score in std_matches[:3]:
            print(f"  - {name}: {score:.3f}")

        print("Method 2 (CLAHE + 60x60 face in 80x80 search):")
        for name, score in face_matches[:3]:
            print(f"  - {name}: {score:.3f}")

        print("Method 3 (Canny Edges + 60x60 face in 80x80 search):")
        for name, score in canny_matches[:3]:
            print(f"  - {name}: {score:.3f}")

        print("Method 4 (Top-Half CLAHE + 40x45 face in 55x60 search):")
        for name, score in face_matches_v2[:3]:
            print(f"  - {name}: {score:.3f}")


if __name__ == "__main__":
    analyze()
