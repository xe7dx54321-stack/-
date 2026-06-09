"""Handicap (Asian handicap) projection model."""

from dataclasses import dataclass, field

from worldcup_campaign.scoreline_model import ScorelineResult


@dataclass
class HandicapResult:
    line: float
    home_cover_probability: float
    away_cover_probability: float
    push_probability: float


class HandicapModel:
    """Calculates handicap cover probabilities from scoreline distribution."""

    def __init__(self, lines: list[float] = None):
        self.lines = lines or [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]

    def calculate(self, scorelines: list[ScorelineResult]) -> list[HandicapResult]:
        """Calculate handicap cover probabilities for all lines."""
        results = []
        for line in self.lines:
            # Home is given the handicap line (negative line = home favored)
            # With handicap: home + line vs away
            # home cover: home_goals + line > away_goals
            # push: home_goals + line == away_goals
            # away cover: home_goals + line < away_goals
            home_cover = sum(
                s.probability for s in scorelines
                if (s.home_goals + line) > s.away_goals
            )
            away_cover = sum(
                s.probability for s in scorelines
                if (s.home_goals + line) < s.away_goals
            )
            push = 1.0 - home_cover - away_cover

            results.append(HandicapResult(
                line=line,
                home_cover_probability=round(home_cover, 4),
                away_cover_probability=round(away_cover, 4),
                push_probability=round(push, 4),
            ))
        return results