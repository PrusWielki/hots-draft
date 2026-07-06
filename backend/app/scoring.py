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

    # Track which heroes are unavailable
    unavailable = set(
        draft_state.my_team_picks
        + draft_state.my_team_bans
        + draft_state.enemy_picks
        + draft_state.enemy_bans
    )

    # Analyze current ally team composition
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

        # 1. Ally Synergies
        for ally_id in draft_state.my_team_picks:
            if ally_id not in hero_db:
                continue
            ally = hero_db[ally_id]

            # Synergy is bi-directional
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

        # 2. Enemy Counters
        for enemy_id in draft_state.enemy_picks:
            if enemy_id not in hero_db:
                continue
            enemy = hero_db[enemy_id]

            # If the recommended hero counters the enemy
            if hero_id in enemy.counters:
                base_score += 25.0
                reasons.append(f"Counters enemy {enemy.name} (+25 pts)")

            # If the enemy counters the recommended hero
            if enemy_id in hero.counters:
                base_score -= 20.0
                reasons.append(f"Countered by enemy {enemy.name} (-20 pts)")

        # 3. Composition adjustments
        # Ensure we have at least one Tank
        if hero.role == HotsRole.TANK:
            if not has_tank:
                base_score += 30.0
                reasons.append("Missing primary Tank role (+30 pts)")
            else:
                base_score -= 15.0
                reasons.append("Tank role already filled (-15 pts)")

        # Ensure we have at least one Healer
        elif hero.role == HotsRole.HEALER:
            if not has_healer:
                base_score += 35.0
                reasons.append("Missing primary Healer role (+35 pts)")
            else:
                base_score -= 25.0
                reasons.append("Healer role already filled (-25 pts)")

        # Ensure we have at least one Bruiser
        elif hero.role == HotsRole.BRUISER:
            if not has_bruiser:
                base_score += 15.0
                reasons.append("Missing Bruiser/Offlaner role (+15 pts)")

        # 3.5. Tier adjustments
        tier_adjustments = {"S": 12.0, "A": 6.0, "B": 0.0, "C": -6.0, "D": -12.0}
        tier_adj = tier_adjustments.get(hero.tier, 0.0)
        if tier_adj != 0.0:
            base_score += tier_adj
            reasons.append(
                f"{hero.tier}-Tier classification ({'+' if tier_adj >= 0 else ''}{tier_adj:.0f} pts)"
            )

        # 4. Map Modifiers
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

    # Sort recommendations by score descending
    recommendations.sort(key=lambda r: r.score, reverse=True)
    return recommendations
