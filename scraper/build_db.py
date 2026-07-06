import json
import sys
from pathlib import Path

# Add backend root to path to allow importing validation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

# Hero skeleton with official roles
HERO_SKELETON = {
    "abathur": {"name": "Abathur", "role": "Support"},
    "alarak": {"name": "Alarak", "role": "Melee Assassin"},
    "alexstrasza": {"name": "Alexstrasza", "role": "Healer"},
    "ana": {"name": "Ana", "role": "Healer"},
    "anduin": {"name": "Anduin", "role": "Healer"},
    "anubarak": {"name": "Anub'arak", "role": "Tank"},
    "artanis": {"name": "Artanis", "role": "Bruiser"},
    "arthas": {"name": "Arthas", "role": "Bruiser"},
    "auriel": {"name": "Auriel", "role": "Healer"},
    "azmodan": {"name": "Azmodan", "role": "Ranged Assassin"},
    "blaze": {"name": "Blaze", "role": "Tank"},
    "brightwing": {"name": "Brightwing", "role": "Healer"},
    "butcher": {"name": "The Butcher", "role": "Melee Assassin"},
    "cassia": {"name": "Cassia", "role": "Ranged Assassin"},
    "chen": {"name": "Chen", "role": "Bruiser"},
    "cho": {"name": "Cho", "role": "Tank"},
    "chromie": {"name": "Chromie", "role": "Ranged Assassin"},
    "deathwing": {"name": "Deathwing", "role": "Bruiser"},
    "deckard": {"name": "Deckard", "role": "Healer"},
    "dehaka": {"name": "Dehaka", "role": "Bruiser"},
    "diablo": {"name": "Diablo", "role": "Tank"},
    "dva": {"name": "D.Va", "role": "Bruiser"},
    "etc": {"name": "E.T.C.", "role": "Tank"},
    "falstad": {"name": "Falstad", "role": "Ranged Assassin"},
    "fenix": {"name": "Fenix", "role": "Ranged Assassin"},
    "gall": {"name": "Gall", "role": "Ranged Assassin"},
    "garrosh": {"name": "Garrosh", "role": "Tank"},
    "gazlowe": {"name": "Gazlowe", "role": "Bruiser"},
    "genji": {"name": "Genji", "role": "Ranged Assassin"},
    "greymane": {"name": "Greymane", "role": "Ranged Assassin"},
    "guldan": {"name": "Gul'dan", "role": "Ranged Assassin"},
    "hanzo": {"name": "Hanzo", "role": "Ranged Assassin"},
    "hogger": {"name": "Hogger", "role": "Bruiser"},
    "illidan": {"name": "Illidan", "role": "Melee Assassin"},
    "imperius": {"name": "Imperius", "role": "Bruiser"},
    "jaina": {"name": "Jaina", "role": "Ranged Assassin"},
    "johanna": {"name": "Johanna", "role": "Tank"},
    "junkrat": {"name": "Junkrat", "role": "Ranged Assassin"},
    "kaelthas": {"name": "Kael'thas", "role": "Ranged Assassin"},
    "kelthuzad": {"name": "Kel'Thuzad", "role": "Ranged Assassin"},
    "kerrigan": {"name": "Kerrigan", "role": "Melee Assassin"},
    "kharazim": {"name": "Kharazim", "role": "Healer"},
    "leoric": {"name": "Leoric", "role": "Bruiser"},
    "lili": {"name": "Li Li", "role": "Healer"},
    "liming": {"name": "Li-Ming", "role": "Ranged Assassin"},
    "lost-vikings": {"name": "The Lost Vikings", "role": "Support"},
    "lt-morales": {"name": "Lt. Morales", "role": "Healer"},
    "lucio": {"name": "Lúcio", "role": "Healer"},
    "lunara": {"name": "Lunara", "role": "Ranged Assassin"},
    "maiev": {"name": "Maiev", "role": "Melee Assassin"},
    "malganis": {"name": "Mal'Ganis", "role": "Tank"},
    "malfurion": {"name": "Malfurion", "role": "Healer"},
    "malthael": {"name": "Malthael", "role": "Bruiser"},
    "medivh": {"name": "Medivh", "role": "Support"},
    "mei": {"name": "Mei", "role": "Tank"},
    "mephisto": {"name": "Mephisto", "role": "Ranged Assassin"},
    "muradin": {"name": "Muradin", "role": "Tank"},
    "murky": {"name": "Murky", "role": "Bruiser"},
    "nazeebo": {"name": "Nazeebo", "role": "Ranged Assassin"},
    "nova": {"name": "Nova", "role": "Ranged Assassin"},
    "orphea": {"name": "Orphea", "role": "Ranged Assassin"},
    "probius": {"name": "Probius", "role": "Ranged Assassin"},
    "qhira": {"name": "Qhira", "role": "Melee Assassin"},
    "ragnaros": {"name": "Ragnaros", "role": "Bruiser"},
    "raynor": {"name": "Raynor", "role": "Ranged Assassin"},
    "rehgar": {"name": "Rehgar", "role": "Healer"},
    "rexxar": {"name": "Rexxar", "role": "Bruiser"},
    "samuro": {"name": "Samuro", "role": "Melee Assassin"},
    "sgt-hammer": {"name": "Sgt. Hammer", "role": "Ranged Assassin"},
    "sonya": {"name": "Sonya", "role": "Bruiser"},
    "stitches": {"name": "Stitches", "role": "Tank"},
    "stukov": {"name": "Stukov", "role": "Healer"},
    "sylvanas": {"name": "Sylvanas", "role": "Ranged Assassin"},
    "tassadar": {"name": "Tassadar", "role": "Ranged Assassin"},
    "thrall": {"name": "Thrall", "role": "Bruiser"},
    "tracer": {"name": "Tracer", "role": "Ranged Assassin"},
    "tychus": {"name": "Tychus", "role": "Ranged Assassin"},
    "tyrael": {"name": "Tyrael", "role": "Tank"},
    "tyrande": {"name": "Tyrande", "role": "Healer"},
    "uther": {"name": "Uther", "role": "Healer"},
    "valeera": {"name": "Valeera", "role": "Melee Assassin"},
    "valla": {"name": "Valla", "role": "Ranged Assassin"},
    "varian": {"name": "Varian", "role": "Bruiser"},
    "whitemane": {"name": "Whitemane", "role": "Healer"},
    "xul": {"name": "Xul", "role": "Bruiser"},
    "yrel": {"name": "Yrel", "role": "Bruiser"},
    "zagara": {"name": "Zagara", "role": "Ranged Assassin"},
    "zarya": {"name": "Zarya", "role": "Support"},
    "zeratul": {"name": "Zeratul", "role": "Melee Assassin"},
    "zuljin": {"name": "Zul'jin", "role": "Ranged Assassin"},
}


def main():
    repo_root = Path(__file__).resolve().parents[1]
    scraped_path = repo_root / "data" / "raw" / "scraped_data.json"
    overrides_path = repo_root / "data" / "overrides.json"
    output_path = repo_root / "data" / "heroes.json"

    print("Building database...")

    # Load scraped data if available
    scraped_data = {}
    if scraped_path.exists():
        with open(scraped_path, "r", encoding="utf-8") as f:
            scraped_data = json.load(f)
        print(f"Loaded scraped data from {scraped_path}")
    else:
        print(f"No scraped data found at {scraped_path}. Using base skeleton.")

    # Load overrides if available
    overrides = {}
    if overrides_path.exists():
        with open(overrides_path, "r", encoding="utf-8") as f:
            overrides = json.load(f)
        print(f"Loaded hand-tuned overrides from {overrides_path}")
    else:
        print(f"No overrides found at {overrides_path}.")

    # Load tiers if available
    tiers_path = repo_root / "data" / "raw" / "tiers.json"
    tiers_data = {}
    if tiers_path.exists():
        with open(tiers_path, "r", encoding="utf-8") as f:
            tiers_data = json.load(f)
        print(f"Loaded tier list data from {tiers_path}")
    else:
        print(f"No tier list data found at {tiers_path}.")

    heroes_db = []

    for hero_id, base_info in HERO_SKELETON.items():
        # Retrieve scraped details (counters, synergies)
        hero_scraped = scraped_data.get(hero_id, {})
        hero_tier = tiers_data.get(hero_id, {})

        # Build initial hero document
        hero_doc = {
            "id": hero_id,
            "name": base_info["name"],
            "role": base_info["role"],
            "tier": hero_tier.get("tier", "B"),
            "recommended_ban": hero_tier.get("recommended_ban", False),
            "tags": [],
            "counters": hero_scraped.get("counters", []),
            "synergies": hero_scraped.get("synergies", []),
            "map_performance": hero_scraped.get("map_performance", {}),
            "talent_builds": hero_scraped.get("talent_builds", []),
        }

        # Apply overrides if they exist
        if hero_id in overrides:
            hero_override = overrides[hero_id]
            for key, val in hero_override.items():
                if key in hero_doc:
                    hero_doc[key] = val

        heroes_db.append(hero_doc)

    # Save to data/heroes.json
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(heroes_db, f, indent=2)

    print(f"Database build complete! Saved to {output_path}")

    # Run validation script to ensure data integrity
    import app.validate_data as validator

    print("\nRunning database validation...")
    try:
        validator.main()
    except SystemExit as e:
        if e.code != 0:
            print("Validation failed after merge!")
            sys.exit(e.code)


if __name__ == "__main__":
    main()
