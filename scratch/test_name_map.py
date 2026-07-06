"""
Test the name_map fuzzy matching against known OCR-like inputs from the debug crops.
This tests the name lookup WITHOUT requiring EasyOCR to be installed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.detection.name_map import name_to_hero_id  # noqa: E402

# Simulate what OCR would return from each crop based on what we can see in the images
OCR_SIMULATED = {
    # Ally picks (banner bottom-left, sometimes truncated or Polish)
    "ally_picks_0": "JASNOSKRZY",  # Brightwing = Jasnoskrzydła (truncated)
    "ally_picks_1": "KASJA",  # Cassia = Kasja
    "ally_picks_2": "TYRAEL",  # Tyrael
    "ally_picks_3": "IMPERIUS",  # Imperius (same)
    "ally_picks_4": "WYŻER",  # Hogger = Wyżer
    # Enemy picks (banner bottom-right)
    "enemy_picks_0": "SONYA",  # Sonya (same)
    "enemy_picks_1": "MEDIVH",  # Medivh (same)
    "enemy_picks_2": "HANZO",  # Hanzo (same)
    "enemy_picks_3": "GAZOL",  # Gazlowe = Gazol (truncated GAZO...)
    "enemy_picks_4": "THRALL",  # Thrall (same)
}

GROUND_TRUTH = {
    "ally_picks_0": "brightwing",
    "ally_picks_1": "cassia",
    "ally_picks_2": "tyrael",
    "ally_picks_3": "imperius",
    "ally_picks_4": "hogger",
    "enemy_picks_0": "sonya",
    "enemy_picks_1": "medivh",
    "enemy_picks_2": "hanzo",
    "enemy_picks_3": "gazlowe",
    "enemy_picks_4": "thrall",
}

print("Name map OCR simulation test")
print("=" * 40)
correct = 0
for slot, ocr_text in OCR_SIMULATED.items():
    hero_id = name_to_hero_id(ocr_text)
    gt = GROUND_TRUTH[slot]
    ok = "✅" if hero_id == gt else "❌"
    print(f"{ok} {slot}: OCR='{ocr_text}' → {hero_id} (truth={gt})")
    if hero_id == gt:
        correct += 1

print(
    f"\nAccuracy: {correct}/{len(OCR_SIMULATED)} ({100*correct//len(OCR_SIMULATED)}%)"
)
