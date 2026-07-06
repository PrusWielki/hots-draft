import sys
from pathlib import Path

# Add backend directory to path so we can import modules
repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root / "backend"))

try:
    import cv2
    import mss
    import numpy as np

    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

from app.detection.vision import DEFAULT_COORDINATES  # noqa: E402


def debug_capture():
    if not OPENCV_AVAILABLE:
        print(
            "Error: opencv-python or mss is not installed. Please run: pip install opencv-python mss numpy"
        )
        return

    print("Starting Vision Debugger...")

    # Create debug directory
    debug_dir = repo_root / "data" / "debug_crops"
    debug_dir.mkdir(parents=True, exist_ok=True)

    # Load templates with multiple scales (matching production vision.py)
    portraits_dir = repo_root / "data" / "portraits"
    templates = {}
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    scales = [0.5, 0.6, 0.7, 0.8, 0.9]
    if portraits_dir.exists():
        for file in portraits_dir.iterdir():
            if file.suffix in (".png", ".jpg", ".jpeg") and file.stem != ".gitkeep":
                img = cv2.imread(str(file))
                if img is not None:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    base = cv2.resize(gray, (100, 100))
                    variants = []
                    for s in scales:
                        w = int(100 * s)
                        h = int(100 * s)
                        scaled = cv2.resize(base, (w, h))
                        variants.append(clahe.apply(scaled))
                    templates[file.stem] = variants
        print(
            f"Loaded {len(templates)} templates ({len(scales)} scales each) for comparison."
        )
    else:
        print(f"Warning: Portraits directory not found at {portraits_dir}")

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        print(f"Primary monitor dimensions: {monitor['width']}x{monitor['height']}")
        screenshot = sct.grab(monitor)

        img_bgr = np.array(screenshot)
        if img_bgr.shape[2] == 4:
            img_bgr = cv2.cvtColor(img_bgr, cv2.COLOR_BGRA2BGR)

        # Save the full screenshot for coordinate calibration
        full_screenshot_path = debug_dir / "full_screenshot.png"
        cv2.imwrite(str(full_screenshot_path), img_bgr)
        print(
            f"Saved full screenshot to {full_screenshot_path} for coordinate calibration reference!"
        )

        height, width = img_bgr.shape[:2]
        scale_x = width / 2560.0
        scale_y = height / 1440.0

        print(
            f"Capture dimensions: {width}x{height} (Scale factors: X={scale_x:.2f}, Y={scale_y:.2f})"
        )

        for category, slots in DEFAULT_COORDINATES.items():
            print(f"\nScanning category: {category}...")
            for idx, slot in enumerate(slots):
                x = int(slot["x"] * scale_x)
                y = int(slot["y"] * scale_y)
                w = int(slot["w"] * scale_x)
                h = int(slot["h"] * scale_y)

                # Boundary check
                if x < 0 or y < 0 or x + w > width or y + h > height:
                    print(f"  Slot {idx} coordinates out of bounds: x={x}, y={y}")
                    continue

                crop = img_bgr[y : y + h, x : x + w]
                if crop.size == 0:
                    continue

                # Save cropped slot to folder
                crop_path = debug_dir / f"{category}_{idx}.png"
                cv2.imwrite(str(crop_path), crop)
                print(f"  Saved crop for {category}[{idx}] to data/debug_crops/")

                if templates:
                    gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    resized_crop = cv2.resize(gray_crop, (100, 100))
                    cl_crop = clahe.apply(resized_crop)

                    matches = []
                    for hero_id, variants in templates.items():
                        best = 0.0
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
                            if max_val > best:
                                best = max_val
                        matches.append((hero_id, best))

                    matches.sort(key=lambda m: m[1], reverse=True)
                    print(f"    Top matches for {category}[{idx}]:")
                    for hero_id, score in matches[:3]:
                        print(f"      - {hero_id}: {score:.2f}")

    print(
        f"\nDone! Open the folder '{debug_dir.resolve()}' and check if the images contain the draft slots of the game."
    )
    print(
        "If they are misaligned (showing the wrong area), adjust the x, y values in backend/app/detection/vision.py."
    )


if __name__ == "__main__":
    debug_capture()
