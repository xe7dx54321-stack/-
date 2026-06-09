"""Mock odds generator: creates synthetic odds from model probabilities."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MockOdds:
    match_id: str
    market_type: str
    selection: str
    odds: float
    is_mock: bool = True
    is_synthetic: bool = True
    source: str = "synthetic_from_model_probability"


class MockOddsGenerator:
    """Generates mock/synthetic odds from model probabilities."""

    def __init__(self, policy_path: str):
        self.policy = json.loads(Path(policy_path).read_text(encoding="utf-8-sig"))
        self.vig = self.policy.get("synthetic_vig", 0.06)
        self.min_odds = self.policy.get("min_odds", 1.05)
        self.max_odds = self.policy.get("max_odds", 100.0)

    def _prob_to_odds(self, prob: float) -> float:
        """Convert probability to decimal odds with vig applied.

        Fair odds = 1/prob, then add vig to make it worse than fair.
        Synthetic odds = fair_odds * (1 - vig_share)
        """
        if prob <= 0:
            return self.max_odds
        fair_odds = 1.0 / prob
        # Apply vig: bookmaker's odds are worse than fair
        synthetic = fair_odds * (1.0 - self.vig)
        return round(max(self.min_odds, min(self.max_odds, synthetic)), 2)

    def generate_1x2(
        self, match_id: str, home_prob: float, draw_prob: float, away_prob: float
    ) -> list[MockOdds]:
        """Generate mock 1x2 odds."""
        return [
            MockOdds(match_id=match_id, market_type="1x2", selection="home",
                     odds=self._prob_to_odds(home_prob)),
            MockOdds(match_id=match_id, market_type="1x2", selection="draw",
                     odds=self._prob_to_odds(draw_prob)),
            MockOdds(match_id=match_id, market_type="1x2", selection="away",
                     odds=self._prob_to_odds(away_prob)),
        ]

    def generate_over_under(
        self, match_id: str, line: float, over_prob: float, under_prob: float
    ) -> list[MockOdds]:
        """Generate mock over/under odds."""
        return [
            MockOdds(match_id=match_id, market_type=f"over_under_{line}",
                     selection="over", odds=self._prob_to_odds(over_prob)),
            MockOdds(match_id=match_id, market_type=f"over_under_{line}",
                     selection="under", odds=self._prob_to_odds(under_prob)),
        ]

    def generate_correct_score_snapshot(
        self, match_id: str, scorelines: list[dict]
    ) -> list[MockOdds]:
        """Generate mock correct score odds for top scorelines."""
        results = []
        for sl in scorelines[:8]:
            results.append(MockOdds(
                match_id=match_id, market_type="correct_score",
                selection=f"{sl['scoreline']}",
                odds=self._prob_to_odds(sl["probability"]),
            ))
        return results