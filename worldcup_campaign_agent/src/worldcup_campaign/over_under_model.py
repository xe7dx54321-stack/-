"""Over/under probability model."""

from dataclasses import dataclass

from worldcup_campaign.scoreline_model import ScorelineResult


@dataclass
class OverUnderResult:
    line: float
    over_probability: float
    under_probability: float


class OverUnderModel:
    """Calculates over/under probabilities from scoreline distribution."""

    def __init__(self, lines: list[float] = None):
        self.lines = lines or [0.5, 1.5, 2.5, 3.5, 4.5]

    def calculate(self, scorelines: list[ScorelineResult]) -> list[OverUnderResult]:
        """Calculate over/under probabilities for all lines."""
        results = []
        for line in self.lines:
            over = sum(
                s.probability for s in scorelines
                if (s.home_goals + s.away_goals) > line
            )
            under = sum(
                s.probability for s in scorelines
                if (s.home_goals + s.away_goals) <= line
            )
            results.append(OverUnderResult(
                line=line,
                over_probability=round(over, 4),
                under_probability=round(under, 4),
            ))
        return results