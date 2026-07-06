import time
from pathlib import Path

import httpx

HERO_LIST = [
    "abathur",
    "alarak",
    "alexstrasza",
    "ana",
    "anduin",
    "anubarak",
    "artanis",
    "arthas",
    "auriel",
    "azmodan",
    "blaze",
    "brightwing",
    "butcher",
    "cassia",
    "chen",
    "cho",
    "chromie",
    "deathwing",
    "deckard",
    "dehaka",
    "diablo",
    "dva",
    "etc",
    "falstad",
    "fenix",
    "gall",
    "garrosh",
    "gazlowe",
    "genji",
    "greymane",
    "guldan",
    "hanzo",
    "hogger",
    "illidan",
    "imperius",
    "jaina",
    "johanna",
    "junkrat",
    "kaelthas",
    "kelthuzad",
    "kerrigan",
    "kharazim",
    "leoric",
    "lili",
    "liming",
    "lost-vikings",
    "lt-morales",
    "lucio",
    "lunara",
    "maiev",
    "malganis",
    "malfurion",
    "malthael",
    "medivh",
    "mei",
    "mephisto",
    "muradin",
    "murky",
    "nazeebo",
    "nova",
    "orphea",
    "probius",
    "qhira",
    "ragnaros",
    "raynor",
    "rehgar",
    "rexxar",
    "samuro",
    "sgt-hammer",
    "sonya",
    "stitches",
    "stukov",
    "sylvanas",
    "tassadar",
    "thrall",
    "tracer",
    "tychus",
    "tyrael",
    "tyrande",
    "uther",
    "valeera",
    "valla",
    "varian",
    "whitemane",
    "xul",
    "yrel",
    "zagara",
    "zarya",
    "zeratul",
    "zuljin",
]

# Custom URL slug overrides for Icy Veins
SLUG_OVERRIDES = {
    "etc": "e-t-c",
    "lili": "li-li",
    "liming": "li-ming",
    "lost-vikings": "the-lost-vikings",
    "butcher": "the-butcher",
    "kelthuzad": "kel-thuzad",
}


def get_slug(hero_id: str) -> str:
    return SLUG_OVERRIDES.get(hero_id, hero_id)


def main():
    repo_root = Path(__file__).resolve().parents[1]
    cache_dir = repo_root / "data" / "raw" / "icyveins"
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading Icy Veins guides to cache directory: {cache_dir}")

    client = httpx.Client(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
    )

    for i, hero in enumerate(HERO_LIST):
        slug = get_slug(hero)
        url = f"https://www.icy-veins.com/heroes/{slug}-build-guide"
        dest_file = cache_dir / f"{hero}.html"

        if dest_file.exists():
            print(f"[{i+1}/{len(HERO_LIST)}] Already cached: {hero}")
            continue

        print(f"[{i+1}/{len(HERO_LIST)}] Fetching: {url} -> {dest_file.name}")
        try:
            response = client.get(url, follow_redirects=True)
            if response.status_code == 200:
                with open(dest_file, "w", encoding="utf-8") as f:
                    f.write(response.text)
                # Polite rate limiting
                time.sleep(1.0)
            else:
                print(
                    f"  Warning: Received status code {response.status_code} for {hero}"
                )
        except Exception as e:
            print(f"  Error fetching {hero}: {e}")
            time.sleep(2.0)

    # Fetch the general tier list
    tier_list_url = (
        "https://www.icy-veins.com/heroes/heroes-of-the-storm-general-tier-list"
    )
    tier_list_dest = cache_dir / "general-tier-list.html"
    if not tier_list_dest.exists():
        print(f"\nFetching general tier list: {tier_list_url} -> {tier_list_dest.name}")
        try:
            response = client.get(tier_list_url, follow_redirects=True)
            if response.status_code == 200:
                with open(tier_list_dest, "w", encoding="utf-8") as f:
                    f.write(response.text)
                print("Tier list fetched successfully!")
            else:
                print(
                    f"  Warning: Received status code {response.status_code} for tier list"
                )
        except Exception as e:
            print(f"  Error fetching tier list: {e}")

    print("Fetching complete!")


if __name__ == "__main__":
    main()
