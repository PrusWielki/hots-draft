import sys
from pathlib import Path

import httpx

# Order of heroes in the Icy Veins master sprite sheet (each is 100px wide, total 9000px wide)
SPRITE_ORDER = [
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
    "lt-morales",
    "lucio",
    "lunara",
    "maiev",
    "malfurion",
    "malganis",
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
    "butcher",
    "lost-vikings",
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
    "hogger",
]


def main():
    repo_root = Path(__file__).resolve().parents[1]
    portraits_dir = repo_root / "data" / "portraits"
    portraits_dir.mkdir(parents=True, exist_ok=True)

    # Sprite sheet url on Icy Veins
    sprite_url = "https://static.icy-veins.com/sprites/heroes-portraits-100x100-ceacae4a807149808d9d604961089bba.jpg"
    temp_sprite_path = repo_root / "data" / "raw" / "heroes-portraits-100x100.jpg"
    temp_sprite_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading master sprite sheet from: {sprite_url}")

    # Download the sheet
    client = httpx.Client(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
    )
    try:
        response = client.get(sprite_url)
        if response.status_code == 200:
            with open(temp_sprite_path, "wb") as f:
                f.write(response.content)
            print("Sprite sheet downloaded successfully!")
        else:
            print(
                f"Error: Received status code {response.status_code} for sprite sheet."
            )
            sys.exit(1)
    except Exception as e:
        print(f"Error downloading sprite sheet: {e}")
        sys.exit(1)

    # Crop the sprite sheet into individual portraits (try OpenCV, fallback to PIL)
    try:
        import cv2

        print("Using OpenCV for cropping...")
        img = cv2.imread(str(temp_sprite_path))
        if img is None:
            raise ValueError("Failed to load image with OpenCV")

        h, w, _ = img.shape
        portrait_size = 100
        print(f"Loaded image size: {w}x{h}")

        for idx, hero_id in enumerate(SPRITE_ORDER):
            x = idx * portrait_size
            if x + portrait_size <= w:
                crop = img[0:portrait_size, x : x + portrait_size]
                dest = portraits_dir / f"{hero_id}.png"
                cv2.imwrite(str(dest), crop)
        print("Successfully cropped all 90 portraits using OpenCV!")

    except Exception as e:
        print(f"OpenCV cropping failed ({e}). Falling back to PIL (Pillow)...")
        try:
            from PIL import Image

            img = Image.open(temp_sprite_path)
            w, h = img.size
            portrait_size = 100
            print(f"Loaded image size: {w}x{h}")

            for idx, hero_id in enumerate(SPRITE_ORDER):
                x = idx * portrait_size
                if x + portrait_size <= w:
                    crop = img.crop((x, 0, x + portrait_size, portrait_size))
                    dest = portraits_dir / f"{hero_id}.png"
                    crop.save(dest, "PNG")
            print("Successfully cropped all 90 portraits using PIL!")
        except Exception as pil_err:
            print(f"Error: PIL cropping failed as well: {pil_err}")
            sys.exit(1)


if __name__ == "__main__":
    main()
