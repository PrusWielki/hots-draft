import json
import sys
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

# Add backend root to path to allow importing app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import Hero


def main():
    repo_root = Path(__file__).resolve().parents[2]
    heroes_json_path = repo_root / "data" / "heroes.json"
    portraits_dir = repo_root / "data" / "portraits"

    print(f"Validating database at: {heroes_json_path}")

    if not heroes_json_path.exists():
        print(f"Error: {heroes_json_path} does not exist.")
        sys.exit(1)

    try:
        with open(heroes_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON in {heroes_json_path}: {e}")
        sys.exit(1)

    # Validate against schema
    try:
        # Use TypeAdapter for List[Hero] validation in Pydantic v2
        adapter = TypeAdapter(list[Hero])
        heroes = adapter.validate_python(data)
    except ValidationError as e:
        print("Schema Validation Error:")
        print(e)
        sys.exit(1)

    # Core validations
    hero_map = {hero.id: hero for hero in heroes}
    errors = []

    # Check for duplicate IDs
    if len(heroes) != len(hero_map):
        ids = [h.id for h in heroes]
        duplicates = {x for x in ids if ids.count(x) > 1}
        errors.append(f"Duplicate hero IDs found in database: {duplicates}")

    # Check referential integrity for counters and synergies
    for hero in heroes:
        # Validate counters
        for counter_id in hero.counters:
            if counter_id not in hero_map:
                errors.append(
                    f"Hero '{hero.id}' references non-existent counter hero: '{counter_id}'"
                )

        # Validate synergies
        for synergy_id in hero.synergies:
            if synergy_id not in hero_map:
                errors.append(
                    f"Hero '{hero.id}' references non-existent synergy hero: '{synergy_id}'"
                )

    # Check portraits if the directory exists
    if portraits_dir.exists():
        # Get list of files, ignoring hidden files and .gitkeep
        portrait_files = {
            p.stem
            for p in portraits_dir.iterdir()
            if p.is_file() and not p.name.startswith(".") and p.name != ".gitkeep"
        }

        # Only validate portraits if there are actually files in the folder
        if portrait_files:
            # Every hero in JSON must have a portrait
            for hero_id in hero_map:
                if hero_id not in portrait_files:
                    errors.append(
                        f"Hero '{hero_id}' is missing a portrait file in data/portraits/"
                    )

            # Every portrait file must correspond to a hero in JSON
            for portrait_name in portrait_files:
                if portrait_name not in hero_map:
                    errors.append(
                        f"Portrait '{portrait_name}.png' does not match any hero in heroes.json"
                    )

    # Report results
    if errors:
        print(f"\nValidation failed with {len(errors)} error(s):")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)

    print("\nSuccess: heroes.json is valid and referentially intact!")
    sys.exit(0)


if __name__ == "__main__":
    main()
