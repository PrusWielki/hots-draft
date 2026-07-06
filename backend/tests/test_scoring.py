import sys
from pathlib import Path

# Add backend root to path to allow importing app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import DraftState, Hero, HotsRole
import app.scoring
from app.scoring import score_heroes

# Mock global win rates to avoid affecting unit tests with real data
app.scoring.WIN_RATES = {}

# Mock database for unit testing
MOCK_HERO_DB = {
    "johanna": Hero(
        id="johanna",
        name="Johanna",
        role=HotsRole.TANK,
        tags=["blind", "waveclear"],
        counters=["malganis"],
        synergies=["kaelthas"],
        map_performance={},
    ),
    "illidan": Hero(
        id="illidan",
        name="Illidan",
        role=HotsRole.MELEE_ASSASSIN,
        tags=["dive", "sustain"],
        counters=["johanna"],  # Johanna counters Illidan
        synergies=["abathur"],
        map_performance={},
    ),
    "abathur": Hero(
        id="abathur",
        name="Abathur",
        role=HotsRole.SUPPORT,
        tags=["global"],
        counters=[],
        synergies=["illidan"],
        map_performance={},
    ),
    "rehgar": Hero(
        id="rehgar",
        name="Rehgar",
        role=HotsRole.HEALER,
        tags=["cleanse"],
        counters=[],
        synergies=[],
        map_performance={},
    ),
    "lili": Hero(
        id="lili",
        name="Li Li",
        role=HotsRole.HEALER,
        tags=["blind"],
        counters=[],
        synergies=[],
        map_performance={},
    ),
}


def test_empty_draft_recommends_roles():
    """If draft is empty, tank and healer should receive composition bonuses."""
    state = DraftState()
    recs = score_heroes(state, MOCK_HERO_DB)
    rec_map = {r.hero_id: r for r in recs}

    # Rehgar should get composition bonus for missing healer (+35 pts)
    # Johanna should get composition bonus for missing tank (+30 pts)
    assert rec_map["rehgar"].score == 135.0  # 100 base + 35 healer
    assert rec_map["johanna"].score == 130.0  # 100 base + 30 tank


def test_healer_bonus_disappears_when_healer_picked():
    """If our team already has a healer, healer recommendation scores should drop."""
    # Our team picks Rehgar (Healer)
    state = DraftState(my_team_picks=["rehgar"])
    recs = score_heroes(state, MOCK_HERO_DB)
    rec_map = {r.hero_id: r for r in recs}

    # Rehgar is picked, so he is not recommended
    assert "rehgar" not in rec_map

    # Li Li is a healer. Since we already have Rehgar, she should be penalized (-25 pts)
    assert rec_map["lili"].score == 75.0  # 100 base - 25 penalty


def test_counter_pick_bonus():
    """If the enemy team picks Illidan, Johanna (who counters Illidan) should get a +25 pts bonus."""
    state = DraftState(enemy_picks=["illidan"])
    recs = score_heroes(state, MOCK_HERO_DB)
    rec_map = {r.hero_id: r for r in recs}

    # Johanna counters Illidan -> 100 base + 30 (missing tank) + 25 (counter) = 155 pts
    assert rec_map["johanna"].score == 155.0


def test_synergy_bonus():
    """If our team picks Illidan, Abathur (who has synergy with Illidan) should get a synergy bonus."""
    state = DraftState(my_team_picks=["illidan"])
    recs = score_heroes(state, MOCK_HERO_DB)
    rec_map = {r.hero_id: r for r in recs}

    # Abathur synergies with Illidan -> 100 base + 30 synergy - 10 Support penalty = 120 pts
    assert rec_map["abathur"].score == 120.0
