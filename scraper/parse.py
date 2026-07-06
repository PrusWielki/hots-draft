import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

# List of hero IDs for reference mapping
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

# Map Icy Veins URL slug back to our hero ID
SLUG_TO_ID = {
    "e-t-c": "etc",
    "li-li": "lili",
    "li-ming": "liming",
    "the-lost-vikings": "lost-vikings",
    "the-butcher": "butcher",
    "kel-thuzad": "kelthuzad",
}


def clean_slug(slug: str) -> str:
    # Convert slug to hero ID
    return SLUG_TO_ID.get(slug, slug)


def parse_hero_guide(html_content: str) -> dict:
    soup = BeautifulSoup(html_content, "html.parser")
    result = {
        "counters": [],
        "synergies": [],
        "map_performance": {},
        "talent_builds": [],
    }

    # 1. Extract Synergies
    syn_div = soup.find("div", class_="heroes_synergies")
    if syn_div:
        for a in syn_div.find_all("a", href=True):
            match = re.search(r"/heroes/([a-z-]+)-build-guide", a["href"])
            if match:
                ref_id = clean_slug(match.group(1))
                if ref_id in HERO_LIST:
                    result["synergies"].append(ref_id)

    # 2. Extract Counters
    cnt_div = soup.find("div", class_="heroes_counters")
    if cnt_div:
        for a in cnt_div.find_all("a", href=True):
            match = re.search(r"/heroes/([a-z-]+)-build-guide", a["href"])
            if match:
                ref_id = clean_slug(match.group(1))
                if ref_id in HERO_LIST:
                    result["counters"].append(ref_id)

    # Deduplicate and sort lists
    result["counters"] = sorted(list(set(result["counters"])))
    result["synergies"] = sorted(list(set(result["synergies"])))

    # 3. Extract Map Performance
    maps_div = soup.find("div", class_="heroes_maps")
    if maps_div:
        rankings = maps_div.find("div", class_="heroes_maps_rankings")
        if rankings:
            map_modifiers = {
                "heroes_maps_stronger": 1.1,
                "heroes_maps_average": 1.0,
                "heroes_maps_weaker": 0.9,
            }
            for section_class, modifier in map_modifiers.items():
                section = rankings.find("div", class_=section_class)
                if section:
                    for a in section.find_all("a", href=True):
                        if "data-heroes-tooltip" in a.attrs:
                            map_slug = a["data-heroes-tooltip"].replace("map-", "")
                            map_name = map_slug.replace("-", "_")
                            result["map_performance"][map_name] = modifier

    # 4. Extract Talent Builds
    builds_div = soup.find("div", class_="heroes_builds")
    if builds_div:
        for build in builds_div.find_all("div", class_="heroes_build"):
            name_el = build.find("h3")
            build_name = name_el.text.strip() if name_el else "Recommended Build"
            is_recommended = bool(
                build.find("span", class_="heroes_build_tag_recommended")
            )

            talents = []
            for tier in build.find_all("div", class_="heroes_build_talent_tier"):
                lvl_el = tier.find("span", class_="heroes_build_talent_tier_subtitle")
                if not lvl_el:
                    continue
                lvl_match = re.search(r"Level\s+(\d+)", lvl_el.text)
                if not lvl_match:
                    continue
                level = int(lvl_match.group(1))

                talent_a = tier.find("a", class_="heroes_build_talent_tier_recommended")
                if talent_a:
                    talent_slug = talent_a.get("data-heroes-tooltip", "")
                    img = talent_a.find("img")
                    talent_name = ""
                    if img:
                        alt_text = img.get("alt", "")
                        talent_name = (
                            alt_text.replace(" Icon", "").replace(" icon", "").strip()
                        )

                    talents.append(
                        {
                            "level": level,
                            "name": talent_name or talent_slug,
                            "slug": talent_slug,
                        }
                    )

            if talents:
                result["talent_builds"].append(
                    {
                        "name": build_name,
                        "is_recommended": is_recommended,
                        "talents": talents,
                    }
                )

    return result


def parse_tier_list(html_content: str) -> dict:
    soup = BeautifulSoup(html_content, "html.parser")
    result = {}

    # We find all h2 tags with id starting with "tier-"
    tier_headers = soup.find_all(
        lambda tag: tag.name == "h2"
        and tag.has_attr("id")
        and tag["id"].startswith("tier-")
    )

    for header in tier_headers:
        tier_id = header["id"]
        tier_letter = tier_id.split("-")[1].upper()  # S, A, B, C, D

        # Find next sibling with htl class, accounting for heading_container div wrapper
        container = (
            header.parent
            if header.parent and "heading_container" in header.parent.get("class", [])
            else header
        )
        htl_div = container.find_next_sibling("div", class_="htl")
        if not htl_div:
            # Fallback check
            htl_div = container.find_next_sibling()
            while (
                htl_div
                and htl_div.name != "h2"
                and "htl" not in htl_div.get("class", [])
            ):
                htl_div = htl_div.find_next_sibling()

        if not htl_div or "htl" not in htl_div.get("class", []):
            continue

        for a_tag in htl_div.find_all("a", href=True):
            href = a_tag["href"]
            match = re.search(r"/heroes/([a-z-]+)-build-guide", href)
            if not match:
                continue
            slug = match.group(1)
            hero_id = clean_slug(slug)

            if hero_id in HERO_LIST:
                # Check for ban class
                ban_span = a_tag.find("span", class_=re.compile(r"htl_ban_"))
                recommended_ban = False
                if ban_span:
                    classes = ban_span.get("class", [])
                    if any("htl_ban_true" in c for c in classes):
                        recommended_ban = True

                TIER_ORDER = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1, "E": 0, "F": 0}
                if hero_id in result:
                    old_tier = result[hero_id]["tier"]
                    if TIER_ORDER.get(tier_letter, 0) > TIER_ORDER.get(old_tier, 0):
                        result[hero_id]["tier"] = tier_letter
                    if recommended_ban:
                        result[hero_id]["recommended_ban"] = True
                else:
                    result[hero_id] = {
                        "tier": tier_letter,
                        "recommended_ban": recommended_ban,
                    }
    return result


def main():
    repo_root = Path(__file__).resolve().parents[1]
    cache_dir = repo_root / "data" / "raw" / "icyveins"
    output_path = repo_root / "data" / "raw" / "scraped_data.json"
    tiers_output_path = repo_root / "data" / "raw" / "tiers.json"

    if not cache_dir.exists():
        print(
            f"Error: Cache directory {cache_dir} does not exist. Run fetch_icyveins.py first."
        )
        return

    scraped_db = {}
    html_files = [p for p in cache_dir.glob("*.html") if p.stem != "general-tier-list"]

    print(f"Parsing {len(html_files)} cached HTML files...")

    for i, file_path in enumerate(html_files):
        hero_id = file_path.stem
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        data = parse_hero_guide(content)
        scraped_db[hero_id] = data

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scraped_db, f, indent=2)

    print(f"Saved hero details to: {output_path}")

    # Parse tier list if available
    tier_list_path = cache_dir / "general-tier-list.html"
    if tier_list_path.exists():
        print("Parsing general tier list...")
        with open(tier_list_path, "r", encoding="utf-8") as f:
            content = f.read()
        tiers = parse_tier_list(content)
        with open(tiers_output_path, "w", encoding="utf-8") as f:
            json.dump(tiers, f, indent=2)
        print(f"Saved parsed tiers to: {tiers_output_path}")
    else:
        print("No tier list HTML cached. Skipping.")

    print("Parsing complete!")


if __name__ == "__main__":
    main()
