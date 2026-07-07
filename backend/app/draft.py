from typing import List, Optional

from pydantic import BaseModel


class DraftStep(BaseModel):
    action: str  # "pick" or "ban"
    team: str  # "my_team" or "enemy"


class DraftManager:
    def __init__(self, my_team_first: bool = True, map_name: Optional[str] = None):
        self.my_team_first = my_team_first
        self.map_name = map_name
        self.steps = self._generate_steps()
        self.current_step_idx = 0

        # Lists of hero IDs
        self.my_team_picks: List[str] = []
        self.my_team_bans: List[str] = []
        self.enemy_picks: List[str] = []
        self.enemy_bans: List[str] = []

        # History for undo support (stores tuple of (step_idx, hero_id))
        self.history: List[tuple[int, str]] = []

    def _generate_steps(self) -> List[DraftStep]:
        # T1 is first pick team, T2 is second pick team
        t1 = "my_team" if self.my_team_first else "enemy"
        t2 = "enemy" if self.my_team_first else "my_team"

        return [
            # Phase 1 Bans
            DraftStep(action="ban", team=t1),
            DraftStep(action="ban", team=t2),
            DraftStep(action="ban", team=t1),
            DraftStep(action="ban", team=t2),
            # Phase 1 Picks
            DraftStep(action="pick", team=t1),
            DraftStep(action="pick", team=t2),
            DraftStep(action="pick", team=t2),
            DraftStep(action="pick", team=t1),
            DraftStep(action="pick", team=t1),
            # Phase 2 Bans (Mid-Ban) - Second team bans first in mid-ban
            DraftStep(action="ban", team=t2),
            DraftStep(action="ban", team=t1),
            # Phase 2 Picks: B picks 3&4, A picks 4&5, B picks 5
            DraftStep(action="pick", team=t2),
            DraftStep(action="pick", team=t2),
            DraftStep(action="pick", team=t1),
            DraftStep(action="pick", team=t1),
            DraftStep(action="pick", team=t2),
        ]

    def get_current_step(self) -> Optional[DraftStep]:
        if self.current_step_idx < len(self.steps):
            return self.steps[self.current_step_idx]
        return None

    def apply_action(self, hero_id: str) -> bool:
        """Record a pick or ban for the current draft step.

        Returns True if successful, False if draft is already complete.
        """
        step = self.get_current_step()
        if not step:
            return False

        # Prevent duplicate picks or bans
        if (
            hero_id in self.my_team_picks
            or hero_id in self.enemy_picks
            or hero_id in self.my_team_bans
            or hero_id in self.enemy_bans
        ):
            return False

        # Append to the correct list
        if step.action == "pick":
            if step.team == "my_team":
                self.my_team_picks.append(hero_id)
            else:
                self.enemy_picks.append(hero_id)
        elif step.action == "ban":
            if step.team == "my_team":
                self.my_team_bans.append(hero_id)
            else:
                self.enemy_bans.append(hero_id)

        self.history.append((self.current_step_idx, hero_id))
        self.current_step_idx += 1

        # Cho'Gall special rule: if Cho is picked, automatically pick Gall in the next slot (and vice versa)
        if step.action == "pick" and hero_id in ("cho", "gall"):
            companion_id = "gall" if hero_id == "cho" else "cho"
            next_step = self.get_current_step()
            if next_step and next_step.action == "pick" and next_step.team == step.team:
                if (
                    companion_id not in self.my_team_picks
                    and companion_id not in self.enemy_picks
                ):
                    if step.team == "my_team":
                        self.my_team_picks.append(companion_id)
                    else:
                        self.enemy_picks.append(companion_id)
                    self.history.append((self.current_step_idx, companion_id))
                    self.current_step_idx += 1

        return True

    def undo_last_action(self) -> bool:
        """Undo the last recorded pick or ban.

        Returns True if successful, False if history is empty.
        """
        if not self.history:
            return False

        step_idx, hero_id = self.history.pop()
        step = self.steps[step_idx]

        if step.action == "pick":
            if step.team == "my_team":
                self.my_team_picks.remove(hero_id)
            else:
                self.enemy_picks.remove(hero_id)
        elif step.action == "ban":
            if step.team == "my_team":
                self.my_team_bans.remove(hero_id)
            else:
                self.enemy_bans.remove(hero_id)

        self.current_step_idx = step_idx

        # Cho'Gall special rule: if we undo Cho/Gall, automatically undo its companion pick
        if step.action == "pick" and hero_id in ("cho", "gall"):
            companion_id = "gall" if hero_id == "cho" else "cho"
            if self.history:
                prev_step_idx, prev_hero_id = self.history[-1]
                if prev_hero_id == companion_id:
                    self.history.pop()
                    if step.team == "my_team":
                        self.my_team_picks.remove(companion_id)
                    else:
                        self.enemy_picks.remove(companion_id)
                    self.current_step_idx = prev_step_idx

        return True

    def reset(self):
        self.current_step_idx = 0
        self.my_team_picks.clear()
        self.my_team_bans.clear()
        self.enemy_picks.clear()
        self.enemy_bans.clear()
        self.history.clear()

    def is_complete(self) -> bool:
        return self.current_step_idx >= len(self.steps)
