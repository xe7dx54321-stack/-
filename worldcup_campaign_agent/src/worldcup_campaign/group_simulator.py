"""Group stage simulator: expected points, qualification probabilities."""
import json, sys
from dataclasses import dataclass, field
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from worldcup_campaign.match_registry import load_match_registry


@dataclass
class GroupStanding:
    team_code: str
    team_name: str = ""
    expected_points: float = 0.0
    qualification_probability: float = 0.0
    group_winner_probability: float = 0.0
    rank: int = 0
    matches_played: int = 3


@dataclass
class GroupResult:
    group_id: str
    group_letter: str
    standings: list = field(default_factory=list)
    qualifiers: list = field(default_factory=list)
    group_winner: str = ""


class GroupSimulator:
    def __init__(self, groups_path: str, match_registry_path: str, config_path: str):
        self.groups = json.loads(Path(groups_path).read_text(encoding="utf-8-sig"))
        self.matches = load_match_registry(match_registry_path)
        self.config = json.loads(Path(config_path).read_text(encoding="utf-8-sig"))
        self.points = self.config.get("points", {"win": 3, "draw": 1, "loss": 0})

    def simulate_all_groups(self) -> list[GroupResult]:
        results = []
        for g in self.groups:
            result = self._simulate_group(g)
            results.append(result)
        return results

    def _simulate_group(self, group: dict) -> GroupResult:
        group_id = group["group_id"]
        group_letter = group["group_letter"]
        team_codes = group["teams"]

        # Find group matches
        group_matches = []
        for m in self.matches:
            home = m.home_team if hasattr(m, 'home_team') else m.get("home_team", "")
            away = m.away_team if hasattr(m, 'away_team') else m.get("away_team", "")
            if home in team_codes and away in team_codes:
                group_matches.append(m)

        # Calculate expected points using rating-based fallback
        # (no probability model needed for group stage v1)
        team_points = {t: 0.0 for t in team_codes}
        for match in group_matches:
            home = match.home_team if hasattr(match, 'home_team') else match.get("home_team")
            away = match.away_team if hasattr(match, 'away_team') else match.get("away_team")
            # Simple: home advantage 40%, draw 28%, away 32%
            p_home, p_draw, p_away = 0.40, 0.28, 0.32
            team_points[home] += p_home * self.points["win"] + p_draw * self.points["draw"]
            team_points[away] += p_away * self.points["win"] + p_draw * self.points["draw"]

        # Sort by expected points
        sorted_teams = sorted(team_points.items(), key=lambda x: x[1], reverse=True)

        standings = []
        for rank, (team, pts) in enumerate(sorted_teams, 1):
            qual_prob = self._estimate_qual_prob(rank, pts, sorted_teams)
            winner_prob = self._estimate_winner_prob(rank, pts, sorted_teams)
            standings.append(GroupStanding(
                team_code=team, expected_points=round(pts, 2),
                qualification_probability=round(qual_prob, 4),
                group_winner_probability=round(winner_prob, 4),
                rank=rank
            ))

        qualifiers = [s.team_code for s in standings if s.rank <= 2]
        winner = qualifiers[0] if qualifiers else ""

        return GroupResult(
            group_id=group_id, group_letter=group_letter,
            standings=standings, qualifiers=qualifiers, group_winner=winner
        )

    def _estimate_qual_prob(self, rank, pts, all_teams):
        if rank <= 2:
            gap_to_3rd = pts - all_teams[2][1] if len(all_teams) > 2 else 1.0
            return min(1.0, 0.6 + 0.4 * min(1.0, max(0, gap_to_3rd / 3.0)))
        elif rank == 3:
            gap_to_2nd = all_teams[1][1] - pts if len(all_teams) > 1 else 1.0
            return max(0.0, 0.4 - 0.3 * min(1.0, max(0, gap_to_2nd / 3.0)))
        else:
            return 0.05

    def _estimate_winner_prob(self, rank, pts, all_teams):
        if rank == 1:
            gap = pts - all_teams[1][1] if len(all_teams) > 1 else 1.0
            return min(0.95, 0.4 + 0.3 * min(1.0, max(0, gap / 3.0)))
        elif rank == 2:
            gap = all_teams[0][1] - pts if len(all_teams) > 0 else 1.0
            return max(0.05, 0.3 - 0.2 * min(1.0, max(0, gap / 3.0)))
        return 0.05 if rank == 3 else 0.01

    def get_all_qualifiers(self, group_results: list[GroupResult]) -> list[str]:
        return [s.team_code for r in group_results for s in r.standings if s.rank <= 2]

    def get_third_place_teams(self, group_results: list[GroupResult]) -> list[GroupStanding]:
        thirds = []
        for r in group_results:
            for s in r.standings:
                if s.rank == 3:
                    thirds.append(s)
        thirds.sort(key=lambda x: x.expected_points, reverse=True)
        return thirds

    def get_best_third_place_qualifiers(self, group_results: list[GroupResult], n: int = 8) -> list[str]:
        thirds = self.get_third_place_teams(group_results)
        return [t.team_code for t in thirds[:n]]
