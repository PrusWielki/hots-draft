from typing import Dict, List

from app.models import DraftState, Hero, HotsRole, Recommendation


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
    has_tank = HotsRole.TANK in ally_roles
    has_healer = HotsRole.HEALER in ally_roles
    has_bruiser = HotsRole.BRUISER in ally_roles

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

        if hero.role == HotsRole.TANK:
            if not has_tank:
                base_score += 30.0
                reasons.append("Missing primary Tank role (+30 pts)")
            else:
                base_score -= 15.0
                reasons.append("Tank role already filled (-15 pts)")

        elif hero.role == HotsRole.HEALER:
            if not has_healer:
                base_score += 35.0
                reasons.append("Missing primary Healer role (+35 pts)")
            else:
                base_score -= 25.0
                reasons.append("Healer role already filled (-25 pts)")

        elif hero.role == HotsRole.BRUISER:
            if not has_bruiser:
                base_score += 15.0
                reasons.append("Missing Bruiser/Offlaner role (+15 pts)")

        tier_adjustments = {"S": 12.0, "A": 6.0, "B": 0.0, "C": -6.0, "D": -12.0}
        tier_adj = tier_adjustments.get(hero.tier, 0.0)
        if tier_adj != 0.0:
            base_score += tier_adj
            reasons.append(
                f"{hero.tier}-Tier classification ({'+' if tier_adj >= 0 else ''}{tier_adj:.0f} pts)"
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
