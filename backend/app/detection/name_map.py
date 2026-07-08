"""
OCR-based hero name detection for Heroes of the Storm draft picks.

Uses EasyOCR to read the name banner on each pick slot, then maps the
detected text (including Polish localised names) back to the hero ID.

Bans have no name tag, so template matching is still used for those.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import get_close_matches
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Polish → hero_id name mapping
# Most names are identical across languages; only localised ones are listed.
# Keys are upper-cased and accent-stripped for fuzzy comparison.
# ---------------------------------------------------------------------------

# fmt: off
_POLISH_NAMES: dict[str, str] = {
    # Hero ID           English name           Polish name(s)
    "abathur":          "Abathur",
    "alarak":           "Alarak",
    "alexstrasza":      "Alekstrasza",
    "ana":              "Ana",
    "anduin":           "Anduin",
    "anubarak":         "Anub'arak",
    "artanis":          "Artanis",
    "arthas":           "Arthas",
    "auriel":           "Auriel",
    "azmodan":          "Azmodan",
    "blaze":            "Pożarsky",
    "brightwing":       "Jasnoskrzydła",
    "butcher":          "Rzeźnik",
    "cassia":           "Kasja",
    "chen":             "Czen",
    "cho":              "Czo",
    "chromie":          "Chronia",
    "deathwing":        "Skrzydłośmierć",
    "deckard":          "Deckard",
    "dehaka":           "Dehaka",
    "diablo":           "Diablo",
    "dva":              "D.Va",
    "etc":              "E.T.C.",
    "falstad":          "Falstad",
    "fenix":            "Fenix",
    "gall":             "Gal",
    "garrosh":          "Garrosh",
    "gazlowe":          "Gazol",
    "genji":            "Genji",
    "greymane":         "Szarogrzywy",
    "guldan":           "Gul'dan",
    "hanzo":            "Hanzo",
    "hogger":           "Wyżer",
    "illidan":          "Illidan",
    "imperius":         "Imperius",
    "jaina":            "Jaina",
    "johanna":          "Johanna",
    "junkrat":          "Złomiarz",
    "kaelthas":         "Kael'thas",
    "kelthuzad":        "Kel'Thuzad",
    "kerrigan":         "Kerrigan",
    "kharazim":         "Kharazim",
    "leoric":           "Leoric",
    "lili":             "Li Li",
    "liming":           "Li-Ming",
    "lost-vikings":     "Zaginieni Wikingowie",
    "lt-morales":       "Porucznik Morales",
    "lucio":            "Lúcio",
    "lunara":           "Lunara",
    "maiev":            "Maiev",
    "malganis":         "Mal'Ganis",
    "malfurion":        "Malfurion",
    "malthael":         "Maltael",
    "medivh":           "Medivh",
    "mei":              "Mei",
    "mephisto":         "Mefisto",
    "muradin":          "Muradin",
    "murky":            "Męcik",
    "nazeebo":          "Nazeebo",
    "nova":             "Nova",
    "orphea":           "Orphea",
    "probius":          "Probiusz",
    "qhira":            "Qhira",
    "ragnaros":         "Ragnaros",
    "raynor":           "Raynor",
    "rehgar":           "Rehgar",
    "rexxar":           "Rexxar",
    "samuro":           "Samuro",
    "sgt-hammer":       "Sierżant Petarda",
    "sonya":            "Sonya",
    "stitches":         "Zszywaniec",
    "stukov":           "Stukov",
    "sylvanas":         "Sylwana",
    "tassadar":         "Tassadar",
    "thrall":           "Thrall",
    "tracer":           "Tracer",
    "tychus":           "Tychus",
    "tyrael":           "Tyrael",
    "tyrande":          "Tyrande",
    "uther":            "Uther",
    "valeera":          "Valeera",
    "valla":            "Valla",
    "varian":           "Varian",
    "whitemane":        "Białowłosa",
    "xul":              "Xul",
    "yrel":             "Yrel",
    "zagara":           "Zagara",
    "zarya":            "Zarya",
    "zeratul":          "Zeratul",
    "zuljin":           "Zul'jin",
}
# fmt: on

# Also include original English names as fallback
_ENGLISH_NAMES: dict[str, str] = {
    "abathur": "Abathur",
    "alarak": "Alarak",
    "alexstrasza": "Alexstrasza",
    "ana": "Ana",
    "anduin": "Anduin",
    "anubarak": "Anub'Arak",
    "artanis": "Artanis",
    "arthas": "Arthas",
    "auriel": "Auriel",
    "azmodan": "Azmodan",
    "blaze": "Blaze",
    "brightwing": "Brightwing",
    "butcher": "The Butcher",
    "cassia": "Cassia",
    "chen": "Chen",
    "cho": "Cho",
    "chromie": "Chromie",
    "deathwing": "Deathwing",
    "deckard": "Deckard",
    "dehaka": "Dehaka",
    "diablo": "Diablo",
    "dva": "D.Va",
    "etc": "E.T.C.",
    "falstad": "Falstad",
    "fenix": "Fenix",
    "gall": "Gall",
    "garrosh": "Garrosh",
    "gazlowe": "Gazlowe",
    "genji": "Genji",
    "greymane": "Greymane",
    "guldan": "Gul'dan",
    "hanzo": "Hanzo",
    "hogger": "Hogger",
    "illidan": "Illidan",
    "imperius": "Imperius",
    "jaina": "Jaina",
    "johanna": "Johanna",
    "junkrat": "Junkrat",
    "kaelthas": "Kael'thas",
    "kelthuzad": "Kel'Thuzad",
    "kerrigan": "Kerrigan",
    "kharazim": "Kharazim",
    "leoric": "Leoric",
    "lili": "Li Li",
    "liming": "Li-Ming",
    "lost-vikings": "The Lost Vikings",
    "lt-morales": "Lt. Morales",
    "lucio": "Lucio",
    "lunara": "Lunara",
    "maiev": "Maiev",
    "malganis": "Mal'Ganis",
    "malfurion": "Malfurion",
    "malthael": "Malthael",
    "medivh": "Medivh",
    "mei": "Mei",
    "mephisto": "Mephisto",
    "muradin": "Muradin",
    "murky": "Murky",
    "nazeebo": "Nazeebo",
    "nova": "Nova",
    "orphea": "Orphea",
    "probius": "Probius",
    "qhira": "Qhira",
    "ragnaros": "Ragnaros",
    "raynor": "Raynor",
    "rehgar": "Rehgar",
    "rexxar": "Rexxar",
    "samuro": "Samuro",
    "sgt-hammer": "Sgt. Hammer",
    "sonya": "Sonya",
    "stitches": "Stitches",
    "stukov": "Stukov",
    "sylvanas": "Sylvanas",
    "tassadar": "Tassadar",
    "thrall": "Thrall",
    "tracer": "Tracer",
    "tychus": "Tychus",
    "tyrael": "Tyrael",
    "tyrande": "Tyrande",
    "uther": "Uther",
    "valeera": "Valeera",
    "valla": "Valla",
    "varian": "Varian",
    "whitemane": "Whitemane",
    "xul": "Xul",
    "yrel": "Yrel",
    "zagara": "Zagara",
    "zarya": "Zarya",
    "zeratul": "Zeratul",
    "zuljin": "Zul'jin",
}


def _normalize(text: str) -> str:
    """Strip accents, punctuation, extra spaces; uppercase."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^A-Za-z0-9\s]", "", text)
    return text.upper().strip()


# Build reverse lookup: normalized_name → hero_id
_LOOKUP: dict[str, str] = {}
for _hero_id, _pl_name in _POLISH_NAMES.items():
    _LOOKUP[_normalize(_pl_name)] = _hero_id
for _hero_id, _en_name in _ENGLISH_NAMES.items():
    _LOOKUP[_normalize(_en_name)] = _hero_id

# Add custom aliases/fallback names directly to _LOOKUP
_CUSTOM_ALIASES = {
    "ZAGIN": "lost-vikings",
    "ZAGUB": "lost-vikings",
    "ZAGINIENI": "lost-vikings",
    "ZAGUBIENI": "lost-vikings",
    "WIKINGOWIE": "lost-vikings",
    "ZAGINIENI WIKINGOWIE": "lost-vikings",
    "ZAGUBIENI WIKINGOWIE": "lost-vikings",
    "KELTHAS": "kaelthas",
    "ALTHAS": "kaelthas",
    "AELTHAS": "kaelthas",
    "ELTHAS": "kaelthas",
}
for alias, h_id in _CUSTOM_ALIASES.items():
    _LOOKUP[alias] = h_id

_ALL_NORMALIZED = list(_LOOKUP.keys())


def name_to_hero_id(raw_text: str, cutoff: float = 0.65) -> str | None:
    """
    Map OCR-detected text to a hero ID.

    Resolution order:
    1. Exact match on normalized text
    2. Exact first-word match (handles multi-word Polish names where only first word appears)
    3. Prefix match — the query is a prefix of a known normalized name (≥3 chars).
       This handles truncated names like "MEDI"→medivh, "THR"→thrall, "HAN"→hanzo.
    4. Fuzzy full-string match (difflib SequenceMatcher)
    5. Fuzzy first-word match (handles truncation like "JASNOSKRZY"→brightwing)
    Returns None if no confident match found.
    """
    normalized = _normalize(raw_text)
    if not normalized:
        return None

    # Ignore draft lobby state text (Polish and English) to prevent false fuzzy matching
    _LOBBY_WORDS = {
        "WYBIERA",
        "BLOKUJE",
        "BANUJE",
        "CHOOSING",
        "PICKING",
        "BANNING",
        "WYBIERZ",
        "CHOOSE",
        "LOCK",
        "ZABLOKUJ",
        "LOCKING",
        "ZATWIERDZ",
    }
    if normalized in _LOBBY_WORDS or (
        normalized.split() and normalized.split()[0] in _LOBBY_WORDS
    ):
        return None

    # Also compute a letters-only version (strips digits and stray punctuation like commas/semicolons)
    # This handles OCR artifacts like "SO," → "SO" and "THR;" → "THR"
    letters_only = re.sub(r"[^A-Z]", "", normalized)

    # Helper to run the full resolution chain for a given query string
    def _resolve(query: str) -> str | None:
        if not query:
            return None
        # 1. Exact
        if query in _LOOKUP:
            return _LOOKUP[query]
        first = query.split()[0] if " " in query else query
        # 2. First-word exact
        if first in _LOOKUP:
            return _LOOKUP[first]
        # 3. Prefix (≥2 chars to catch very short OCR outputs like "SO" → sonya)
        if len(first) >= 2:
            hits = [
                (k, v)
                for k, v in _LOOKUP.items()
                if k.startswith(first) or (len(k) >= 3 and first.startswith(k))
            ]
            if len(hits) == 1:
                return hits[0][1]
            if len(hits) > 1:
                best = max(
                    hits,
                    key=lambda kv: len(
                        get_close_matches(first, [kv[0]], n=1, cutoff=0.0)
                    ),
                )
                return best[1]
        # 4. Fuzzy full
        m = get_close_matches(query, _ALL_NORMALIZED, n=1, cutoff=cutoff)
        if m:
            return _LOOKUP[m[0]]
        # 5. Fuzzy first-word
        if len(first) >= 4:
            m = get_close_matches(first, _ALL_NORMALIZED, n=1, cutoff=cutoff)
            if m:
                return _LOOKUP[m[0]]
        return None

    # Try normalized text first, then letters-only (strips OCR artifacts like commas/semicolons)
    return _resolve(normalized) or _resolve(letters_only)
