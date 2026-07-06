import json
from pathlib import Path


def parse_data():
    todo_path = Path("todo.md")
    if not todo_path.exists():
        print("todo.md not found")
        return

    content = todo_path.read_text(encoding="utf-8")

    # We want to find the lines after "the copied data is:"
    marker = "the copied data is:"
    if marker not in content:
        print("Marker not found in todo.md")
        return

    data_section = content.split(marker)[1]

    # Standardize names to ID
    # Use mapping from heroes.json if possible, or simple rule
    heroes_path = Path("data/heroes.json")
    with open(heroes_path, "r", encoding="utf-8") as f:
        heroes = json.load(f)
    name_to_id = {h["name"].lower(): h["id"] for h in heroes}
    # Add custom mappings
    name_to_id["mal'ganis"] = "malganis"
    name_to_id["sgt. hammer"] = "sgt-hammer"
    name_to_id["the lost vikings"] = "lost-vikings"
    name_to_id["cho"] = "cho"
    name_to_id["gall"] = "gall"
    name_to_id["lúcio"] = "lucio"
    name_to_id["lucio"] = "lucio"
    name_to_id["kael'thas"] = "kaelthas"
    name_to_id["kel'thuzad"] = "kelthuzad"
    name_to_id["gul'dan"] = "guldan"
    name_to_id["anub'arak"] = "anubarak"
    name_to_id["zul'jin"] = "zuljin"
    name_to_id["li li"] = "lili"
    name_to_id["li-ming"] = "liming"
    name_to_id["lt. morales"] = "lt-morales"

    lines = [line.strip() for line in data_section.split("\n") if line.strip()]

    results = {}

    # Let's iterate lines and look for hero names
    # The format looks like:
    # [Hero Name]
    # [Hero Name]
    # [Stats line: tab or space separated values starting with win rate]
    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if line is a known hero name (or close match)
        clean_line = line.replace("\t", "").strip().lower()
        if clean_line in name_to_id:
            hero_id = name_to_id[clean_line]

            # The next line might be the duplicated hero name
            next_idx = i + 1
            if next_idx < len(lines) and lines[next_idx].strip().lower() == clean_line:
                next_idx += 1

            # Now look for the stats line
            if next_idx < len(lines):
                stats_line = lines[next_idx]
                parts = [p.strip() for p in stats_line.split("\t")]
                if len(parts) >= 8:
                    try:
                        # If first col is empty, check if first elements shifted
                        idx_offset = 0 if parts[0] else 1
                        win_rate = float(parts[idx_offset].replace("%", "").strip())
                        popularity = float(
                            parts[idx_offset + 3].replace("%", "").strip()
                        )
                        pick_rate = float(
                            parts[idx_offset + 4].replace("%", "").strip()
                        )
                        ban_rate = float(parts[idx_offset + 5].replace("%", "").strip())

                        # Find the games played element (it is a number with comma, before 'View Talent Builds')
                        games_played = 0
                        for part in parts:
                            clean_part = part.replace(",", "").strip()
                            if clean_part.isdigit():
                                games_played = int(clean_part)

                        results[hero_id] = {
                            "win_rate": win_rate,
                            "popularity": popularity,
                            "pick_rate": pick_rate,
                            "ban_rate": ban_rate,
                            "games_played": games_played,
                        }
                    except Exception as e:
                        print(
                            f"Failed to parse stats for {hero_id} from line: {stats_line}. Error: {e}"
                        )
            i = next_idx + 1
        else:
            i += 1

    print(f"Parsed stats for {len(results)} heroes.")

    output_path = Path("data/win_rates.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    parse_data()
