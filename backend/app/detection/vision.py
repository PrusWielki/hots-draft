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


class VisionDetector(BaseDetector):
    """OpenCV-based screen detection for HotS draft.

    Runs a background thread to capture screen regions, compare them
    with template portraits in data/portraits/, and emit DraftEvents
    when changes are detected.
    """

    def __init__(self, portraits_dir: Path):
        super().__init__()
        self.portraits_dir = portraits_dir
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.templates: Dict[str, Any] = {}

        if OPENCV_AVAILABLE:
            self._load_templates()
        else:
            print(
                "Warning: opencv-python or numpy is not installed. VisionDetector will run in mock mode."
            )

    def _load_templates(self):
        """Load portrait templates from data/portraits/ for OpenCV matching."""
        if not self.portraits_dir.exists():
            return

        for file in self.portraits_dir.iterdir():
            if file.suffix in (".png", ".jpg", ".jpeg") and file.stem != ".gitkeep":
                # Load template in color or grayscale depending on matching preference
                img = cv2.imread(str(file))
                if img is not None:
                    self.templates[file.stem] = img
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

    def _loop(self):
        """Main detection loop running periodically."""
        while self.running:
            try:
                if OPENCV_AVAILABLE and self.templates:
                    self._perform_detection()
                else:
                    # Mock detection cycle
                    time.sleep(2.0)
            except Exception as e:
                print(f"Error in vision detection loop: {e}")
                time.sleep(5.0)
            time.sleep(1.0)  # Check screen every second

    def _perform_detection(self):
        """Captured screen regions are matched against stored templates.

        Example implementation outline:
        1. Capture HotS game window or main screen.
        2. Crop specific pick/ban portrait slots.
        3. Match cropped slots against loaded templates using cv2.matchTemplate.
        4. If match confidence > threshold (e.g. 0.8), register pick/ban event.
        """
        # This will be fully implemented when screen coordinates and capture methods are calibrated
        pass
