import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import cv2  # noqa: E402
import time  # noqa: E402
from app.detection.ocr import _get_reader, extract_name_region  # noqa: E402

repo_root = backend_dir.parent
screenshot_path = repo_root / "data" / "debug_crops" / "full_screenshot.png"
if not screenshot_path.exists():
    print(f"Error: {screenshot_path} not found!")
    sys.exit(1)

img = cv2.imread(str(screenshot_path))
h_orig, w_orig = img.shape[:2]

# Let's crop ally_picks[1] (Cassia)
scale_x = w_orig / 2560.0
scale_y = h_orig / 1440.0
# Coordinates for ally_picks[1]: {"x": 37, "y": 420, "w": 302, "h": 140}
x = int(37 * scale_x)
y = int(420 * scale_y)
w = int(302 * scale_x)
h = int(140 * scale_y)

BANNER_PAD = 150
x_ocr = max(0, x - BANNER_PAD)
w_ocr = (x + w) - x_ocr
ocr_crop = img[y : y + h, x_ocr : x_ocr + w_ocr]

name_region = extract_name_region(ocr_crop, is_ally=True)
print(f"Name region shape for OCR: {name_region.shape}")

reader = _get_reader()
if reader is None:
    print("OCR not available!")
    sys.exit(1)

print("\n--- Warmup run ---")
reader.readtext(name_region)

print("\n--- Benchmark: Default readtext ---")
start = time.time()
for _ in range(5):
    res = reader.readtext(name_region)
print(
    f"Default: {(time.time() - start) / 5:.4f} seconds per run. Results: {[r[1] for r in res]}"
)

print("\n--- Benchmark: Optimized canvas_size=600, mag_ratio=1.0 ---")
start = time.time()
for _ in range(5):
    res = reader.readtext(name_region, canvas_size=600, mag_ratio=1.0)
print(
    f"Optimized (mag=1.0): {(time.time() - start) / 5:.4f} seconds per run. Results: {[r[1] for r in res]}"
)

print("\n--- Benchmark: Optimized canvas_size=400, mag_ratio=1.0 ---")
start = time.time()
for _ in range(5):
    res = reader.readtext(name_region, canvas_size=400, mag_ratio=1.0)
print(
    f"Optimized (mag=1.0, canvas=400): {(time.time() - start) / 5:.4f} seconds per run. Results: {[r[1] for r in res]}"
)
