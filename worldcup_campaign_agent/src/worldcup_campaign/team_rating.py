"""Team rating loader and lookup."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TeamRating:
    team_code: str
    team_name: str
    group: str
    overall: float
    attack: float
    defense: float
    experience: int
    home_strength: float
    is_placeholder: bool
    confidence_penalty: float


class TeamRatingRegistry:
    """Loads and queries team ratings."""

    def __init__(self, ratings_path: str):
        raw = json.loads(Path(ratings_path).read_text(encoding="utf-8-sig"))
        self._ratings: dict[str, TeamRating] = {}
        for entry in raw:
            tr = TeamRating(
                team_code=entry["team_code"],
                team_name=entry["team_name"],
                group=entry.get("group", ""),
                overall=float(entry["overall"]),
                attack=float(entry["attack"]),
                defense=float(entry["defense"]),
                experience=int(entry.get("experience", 50)),
                home_strength=float(entry.get("home_strength", 1.0)),
                is_placeholder=bool(entry.get("is_placeholder", False)),
                confidence_penalty=float(entry.get("confidence_penalty", 0.0)),
            )
            self._ratings[tr.team_code] = tr

    def get(self, team_code: str) -> Optional[TeamRating]:
        """Get rating for a team by code."""
        return self._ratings.get(team_code)

    def get_or_default(self, team_code: str) -> TeamRating:
        """Get rating or return a default placeholder."""
        if team_code in self._ratings:
            return self._ratings[team_code]
        return TeamRating(
            team_code=team_code, team_name=team_code, group="",
            overall=1600.0, attack=1550.0, defense=1550.0,
            experience=50, home_strength=1.0,
            is_placeholder=True, confidence_penalty=0.3,
        )

    @property
    def team_count(self) -> int:
        return len(self._ratings)

    def get_by_group(self, group: str) -> list[TeamRating]:
        return [r for r in self._ratings.values() if r.group == group]