"""Poisson scoreline probability model."""

import math
from dataclasses import dataclass, field


@dataclass
class ScorelineResult:
    home_goals: int
    away_goals: int
    scoreline: str
    probability: float


class ScorelineModel:
    """Independent Poisson model for scoreline distribution."""

    def __init__(self, max_goals: int = 8):
        self.max_goals = max_goals

    def _poisson(self, k: int, lam: float) -> float:
        if lam <= 0:
            return 1.0 if k == 0 else 0.0
        return (lam ** k) * math.exp(-lam) / math.factorial(k)

    def calculate(self, eg_home: float, eg_away: float) -> list[ScorelineResult]:
        """Calculate scoreline probabilities for all combinations up to max_goals."""
        results = []
        for h in range(self.max_goals + 1):
            ph = self._poisson(h, eg_home)
            for a in range(self.max_goals + 1):
                pa = self._poisson(a, eg_away)
                prob = ph * pa
                results.append(ScorelineResult(
                    home_goals=h, away_goals=a,
                    scoreline=f"{h}-{a}",
                    probability=round(prob, 6),
                ))
        # Sort by probability descending
        results.sort(key=lambda x: x.probability, reverse=True)
        return results

    def get_top_scorelines(self, results: list[ScorelineResult], n: int = 10) -> list[ScorelineResult]:
        """Get top N most probable scorelines."""
        return results[:n]