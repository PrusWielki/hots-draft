import json
from pathlib import Path
from typing import Dict, List

from app.models import DraftState, Hero, HotsRole, Recommendation

# Load win rates data
_win_rates_path = Path(__file__).resolve().parents[2] / "data" / "win_rates.json"
WIN_RATES = {}
if _win_rates_path.exists():
    try:
        with open(_win_rates_path, "r", encoding="utf-8") as f:
            WIN_RATES = json.load(f)
    except Exception as e:
        print(f"Error loading win rates: {e}")


def score_heroes(
    draft_state: DraftState, hero_db: Dict[str, Hero]
) -> List[Recommendation]:
    """Pure function to score all available heroes based on the current draft
    state.

    Rules implemented:
    1. Filter out already picked/banned heroes.
    2. Add/subtract synergy bonuses with current allies.
    3. Add/subtract counter-pick adjustments against current enemies.
    4. Apply role/composition balancing factors (ensure tank, healer, bruiser are present).
    5. Apply map-specific performance modifiers.
    """
    recommendations = []

    unavailable = set(
        draft_state.my_team_picks
        + draft_state.my_team_bans
        + draft_state.enemy_picks
        + draft_state.enemy_bans
    )

    ally_roles = [
        hero_db[h_id].role for h_id in draft_state.my_team_picks if h_id in hero_db
    ]
    tanks = ally_roles.count(HotsRole.TANK)
    healers = ally_roles.count(HotsRole.HEALER)
    bruisers = ally_roles.count(HotsRole.BRUISER)
    ranged_assassins = ally_roles.count(HotsRole.RANGED_ASSASSIN)
    melee_assassins = ally_roles.count(HotsRole.MELEE_ASSASSIN)

    for hero_id, hero in hero_db.items():
        if hero_id in unavailable:
            continue

        base_score = 100.0
        reasons = []

        for ally_id in draft_state.my_team_picks:
            if ally_id not in hero_db:
                continue
            ally = hero_db[ally_id]
            synergy_bonus = 0.0
            if ally_id in hero.synergies:
                synergy_bonus += 15.0
            if hero_id in ally.synergies:
                synergy_bonus += 15.0

            if synergy_bonus > 0:
                base_score += synergy_bonus
                reasons.append(
                    f"Synergy with ally {ally.name} (+{synergy_bonus:.0f} pts)"
                )

        for enemy_id in draft_state.enemy_picks:
            if enemy_id not in hero_db:
                continue
            enemy = hero_db[enemy_id]

            if hero_id in enemy.counters:
                base_score += 25.0
                reasons.append(f"Counters enemy {enemy.name} (+25 pts)")

            if enemy_id in hero.counters:
                base_score -= 20.0
                reasons.append(f"Countered by enemy {enemy.name} (-20 pts)")

        # Composition and Role balancing
        if hero.role == HotsRole.TANK:
            if tanks == 0:
                base_score += 30.0
                reasons.append("Missing primary Tank role (+30 pts)")
            else:
                base_score -= 15.0
                reasons.append("Tank role already filled (-15 pts)")

        elif hero.role == HotsRole.HEALER:
            if healers == 0:
                base_score += 35.0
                reasons.append("Missing primary Healer role (+35 pts)")
            else:
                base_score -= 25.0
                reasons.append("Healer role already filled (-25 pts)")

        elif hero.role == HotsRole.BRUISER:
            if bruisers == 0:
                base_score += 15.0
                reasons.append("Missing Bruiser/Offlaner role (+15 pts)")
            else:
                base_score -= 10.0
                reasons.append("Bruiser role already filled (-10 pts)")

        elif hero.role == HotsRole.RANGED_ASSASSIN:
            if ranged_assassins == 0:
                base_score += 20.0
                reasons.append("Missing Ranged damage dealer (+20 pts)")
            elif ranged_assassins >= 2:
                base_score -= 10.0
                reasons.append("Sufficient Ranged damage already present (-10 pts)")

        # Penalize extra squishies if frontline/healing is missing, or if we have too many assassins
        if hero.role in (HotsRole.RANGED_ASSASSIN, HotsRole.MELEE_ASSASSIN):
            assassins_count = ranged_assassins + melee_assassins
            if assassins_count >= 2:
                if tanks == 0 or healers == 0:
                    base_score -= 15.0
                    reasons.append("Need Tank/Healer before more Assassins (-15 pts)")
                elif assassins_count >= 3:
                    base_score -= 20.0
                    reasons.append("Too many squishy damage dealers (-20 pts)")

        # Support role synergy/comp checks
        elif hero.role == HotsRole.SUPPORT:
            has_hypercarry = any(
                h in ("illidan", "valla", "tracer", "zeratul")
                for h in draft_state.my_team_picks
            )
            if has_hypercarry and tanks >= 1 and healers >= 1:
                base_score += 15.0
                reasons.append("Enabler Support for hypercarry (+15 pts)")
            else:
                base_score -= 10.0
                reasons.append("Support role not prioritized (-10 pts)")

        tier_adjustments = {"S": 12.0, "A": 6.0, "B": 0.0, "C": -6.0, "D": -12.0}
        tier_adj = tier_adjustments.get(hero.tier, 0.0)
        if tier_adj != 0.0:
            base_score += tier_adj
            reasons.append(
                f"{hero.tier}-Tier classification ({'+' if tier_adj >= 0 else ''}{tier_adj:.0f} pts)"
            )

        # Global win rate adjustment: (win_rate - 50.0) * 2.0
        if hero_id in WIN_RATES:
            stats = WIN_RATES[hero_id]
            win_rate = stats.get("win_rate", 50.0)
            wr_adj = (win_rate - 50.0) * 2.0
            if wr_adj != 0.0:
                base_score += wr_adj
                reasons.append(
                    f"Global Win Rate of {win_rate:.1f}% ({'+' if wr_adj >= 0 else ''}{wr_adj:.1f} pts)"
                )

        if draft_state.map_name and hero.map_performance:
            map_mod = hero.map_performance.get(draft_state.map_name)
            if map_mod:
                old_score = base_score
                base_score *= map_mod
                diff = base_score - old_score
                reasons.append(
                    f"Map modifier for '{draft_state.map_name}' ({'+' if diff >= 0 else ''}{diff:.1f} pts)"
                )

        recommendations.append(
            Recommendation(hero_id=hero_id, score=round(base_score, 1), reasons=reasons)
        )

    recommendations.sort(key=lambda r: r.score, reverse=True)
    return recommendations


def score_bans(
    draft_state: DraftState, hero_db: Dict[str, Hero]
) -> List[Recommendation]:
    """Score all available heroes for ban recommendations based on current draft

    state.
    """
    ban_recs = []

    unavailable = set(
        draft_state.my_team_picks
        + draft_state.my_team_bans
        + draft_state.enemy_picks
        + draft_state.enemy_bans
    )

    enemy_roles = [
        hero_db[h_id].role for h_id in draft_state.enemy_picks if h_id in hero_db
    ]
    enemy_has_tank = HotsRole.TANK in enemy_roles
    enemy_has_healer = HotsRole.HEALER in enemy_roles
    enemy_has_bruiser = HotsRole.BRUISER in enemy_roles

    # Check if we are in mid-ban phase (where target role choking is highly effective)
    is_mid_ban = len(draft_state.enemy_picks) >= 2

    for hero_id, hero in hero_db.items():
        if hero_id in unavailable:
            continue

        score = 0.0
        reasons = []

        tier_weights = {"S": 15.0, "A": 8.0, "B": 2.0, "C": -5.0, "D": -10.0}
        tier_score = tier_weights.get(hero.tier, 0.0)
        if tier_score != 0.0:
            score += tier_score
            reasons.append(
                f"{hero.tier}-Tier meta power ({'+' if tier_score >= 0 else ''}{tier_score:.0f} pts)"
            )

        if hero.recommended_ban:
            score += 25.0
            reasons.append("High meta ban priority (+25 pts)")

        # Role/composition-based ban adjustments
        if hero.role == HotsRole.TANK:
            if enemy_has_tank:
                score -= 50.0
                reasons.append("Enemy already has a Tank (low ban value) (-50 pts)")
            elif is_mid_ban:
                score += 10.0
                reasons.append(
                    "Enemy is missing a Tank; target ban frontline (+10 pts)"
                )

        elif hero.role == HotsRole.HEALER:
            if enemy_has_healer:
                score -= 50.0
                reasons.append("Enemy already has a Healer (low ban value) (-50 pts)")
            elif is_mid_ban:
                score += 15.0
                reasons.append(
                    "Enemy is missing a Healer; target ban support (+15 pts)"
                )

        elif hero.role == HotsRole.BRUISER:
            if enemy_has_bruiser:
                score -= 20.0
                reasons.append("Enemy already has a Bruiser (low ban value) (-20 pts)")
            elif is_mid_ban:
                score += 5.0
                reasons.append(
                    "Enemy is missing a Bruiser; target ban offlane (+5 pts)"
                )

        # Global stats ban weight: win rate deviation + ban rate weight
        if hero_id in WIN_RATES:
            stats = WIN_RATES[hero_id]
            win_rate = stats.get("win_rate", 50.0)
            ban_rate = stats.get("ban_rate", 0.0)

            # High win rate + high ban rate makes a target S-tier ban
            wr_factor = max(0.0, win_rate - 50.0) * 1.5
            br_factor = ban_rate * 0.3
            ban_adj = wr_factor + br_factor
            if ban_adj > 0.0:
                score += ban_adj
                reasons.append(
                    f"Meta presence (WR {win_rate:.1f}%, Ban {ban_rate:.1f}%) (+{ban_adj:.1f} pts)"
                )

        for ally_id in draft_state.my_team_picks:
            if ally_id not in hero_db:
                continue
            ally = hero_db[ally_id]
            if ally_id in hero.counters:
                score += 25.0
                reasons.append(f"Hard counters our {ally.name} (+25 pts)")

        for enemy_id in draft_state.enemy_picks:
            if enemy_id not in hero_db:
                continue
            enemy = hero_db[enemy_id]
            if enemy_id in hero.synergies or hero_id in enemy.synergies:
                score += 15.0
                reasons.append(f"Synergizes with enemy {enemy.name} (+15 pts)")

        if draft_state.map_name and hero.map_performance:
            map_mod = hero.map_performance.get(draft_state.map_name)
            if map_mod and map_mod > 1.0:
                score += 12.0
                reasons.append(f"Strong on '{draft_state.map_name}' (+12 pts)")
            elif map_mod and map_mod < 1.0:
                score -= 10.0
                reasons.append(f"Weak on '{draft_state.map_name}' (-10 pts)")

        for enemy_id in draft_state.enemy_picks:
            if enemy_id not in hero_db:
                continue
            enemy = hero_db[enemy_id]
            if enemy_id in hero.counters:
                score -= 15.0
                reasons.append(
                    f"Counters enemy {enemy.name} (keep open to pick) (-15 pts)"
                )

        if score > 0:
            ban_recs.append(
                Recommendation(hero_id=hero_id, score=round(score, 1), reasons=reasons)
            )

    ban_recs.sort(key=lambda r: r.score, reverse=True)
    return ban_recs
