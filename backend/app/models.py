from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class HotsRole(str, Enum):
    TANK = "Tank"
    BRUISER = "Bruiser"
    HEALER = "Healer"
    MELEE_ASSASSIN = "Melee Assassin"
    RANGED_ASSASSIN = "Ranged Assassin"
    SUPPORT = "Support"


class TalentChoice(BaseModel):
    level: int = Field(
        ..., description="Level of the talent tier (1, 4, 7, 10, 13, 16, 20)"
    )
    name: str = Field(..., description="Display name of the talent")
    slug: str = Field(..., description="Unique talent identifier slug")


class TalentBuild(BaseModel):
    name: str = Field(..., description="Name of the build, e.g. Offensive Taunt Build")
    is_recommended: bool = Field(
        False, description="Whether this is the recommended build"
    )
    talents: List[TalentChoice] = Field(
        default_factory=list, description="List of talent choices per tier"
    )


class Hero(BaseModel):
    id: str = Field(
        ..., description="Unique lower-case identifier, e.g., kaelthas or johanna"
    )
    name: str = Field(..., description="Display name, e.g., Kael'thas or Johanna")
    role: HotsRole = Field(..., description="Official HotS role")
    tier: str = Field("B", description="Icy Veins tier list ranking (S, A, B, C, D)")
    recommended_ban: bool = Field(
        False, description="Whether this hero is recommended for bans"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Descriptive tags like waveclear, blind, global, burst",
    )
    counters: List[str] = Field(
        default_factory=list, description="IDs of heroes that counter this hero"
    )
    synergies: List[str] = Field(
        default_factory=list, description="IDs of heroes that synergy with this hero"
    )
    map_performance: Dict[str, float] = Field(
        default_factory=dict,
        description="Map name to performance modifier, e.g. {'tomb_of_the_spider_queen': 1.2}",
    )
    talent_builds: List[TalentBuild] = Field(
        default_factory=list, description="Scraped recommended talent builds"
    )


class DraftState(BaseModel):
    map_name: Optional[str] = Field(
        None, description="The name of the map for the match"
    )
    my_team_picks: List[str] = Field(
        default_factory=list, description="Hero IDs picked by my team"
    )
    my_team_bans: List[str] = Field(
        default_factory=list, description="Hero IDs banned by my team"
    )
    enemy_picks: List[str] = Field(
        default_factory=list, description="Hero IDs picked by the enemy team"
    )
    enemy_bans: List[str] = Field(
        default_factory=list, description="Hero IDs banned by the enemy team"
    )


class Recommendation(BaseModel):
    hero_id: str = Field(..., description="Recommended hero ID")
    score: float = Field(..., description="Calculated recommendation score")
    reasons: List[str] = Field(
        default_factory=list, description="List of reasons for recommendation"
    )
