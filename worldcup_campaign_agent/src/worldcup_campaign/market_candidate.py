"""Market candidate: combines probability, odds, and EV into a candidate entry."""

from dataclasses import dataclass, field
from typing import Optional

from worldcup_campaign.odds_math import (
    decimal_odds_to_implied_probability,
    calculate_edge,
    calculate_ev,
)


@dataclass
class MarketCandidate:
    match_id: str
    match_number: int
    market_type: str
    selection: str
    home_team: str
    away_team: str
    stage: str
    mock_odds: float
    model_probability: float
    market_probability: float
    no_vig_probability: float
    edge: float
    ev: float
    odds_band: str
    value_flag: str
    bucket_eligibility: list[str] = field(default_factory=list)
    target_contribution_preview: float = 0.0
    warnings: list[str] = field(default_factory=list)
    is_blocked: bool = False


class MarketCandidateBuilder:
    """Builds market candidates from model probabilities and mock odds."""

    def __init__(self, ev_config_path: str):
        import json
        from pathlib import Path
        self.config = json.loads(Path(ev_config_path).read_text(encoding="utf-8-sig"))
        self.odds_bands = self.config.get("odds_bands", [])
        self.value_flags = self.config.get("value_flags", {})

    def build_1x2_candidates(
        self,
        match_id: str, match_number: int,
        home_team: str, away_team: str, stage: str,
        home_prob: float, draw_prob: float, away_prob: float,
        home_odds: float, draw_odds: float, away_odds: float,
        warnings: list[str] = None,
    ) -> list[MarketCandidate]:
        """Build 1x2 market candidates."""
        candidates = []
        specs = [
            ("home", home_team, home_prob, home_odds),
            ("draw", "Draw", draw_prob, draw_odds),
            ("away", away_team, away_prob, away_odds),
        ]
        for sel, label, prob, odds in specs:
            candidates.append(self._make_candidate(
                match_id, match_number, "1x2", sel, label,
                home_team, away_team, stage, prob, odds, warnings or [],
            ))
        return candidates

    def build_ou_candidates(
        self,
        match_id: str, match_number: int,
        home_team: str, away_team: str, stage: str,
        line: float, over_prob: float, under_prob: float,
        over_odds: float, under_odds: float,
        warnings: list[str] = None,
    ) -> list[MarketCandidate]:
        """Build over/under market candidates."""
        candidates = []
        specs = [
            ("over", over_prob, over_odds),
            ("under", under_prob, under_odds),
        ]
        for sel, prob, odds in specs:
            candidates.append(self._make_candidate(
                match_id, match_number, f"over_under_{line}",
                sel, f"O/U {line} {sel}",
                home_team, away_team, stage, prob, odds, warnings or [],
            ))
        return candidates

    def _make_candidate(
        self, match_id, match_number, market_type, selection, selection_label,
        home_team, away_team, stage, model_prob, odds, warnings,
    ) -> MarketCandidate:
        """Create a single market candidate with all computed fields."""
        # Implied market probability
        market_prob = decimal_odds_to_implied_probability(odds)
        # No-vig probability (for single selection, same as market_prob in simple case)
        no_vig_prob = market_prob  # Simplified; proper no-vig needs all selections
        # Edge
        edge = calculate_edge(model_prob, market_prob)
        # EV
        ev = calculate_ev(model_prob, odds)
        # Odds band
        band = self._get_odds_band(odds)
        # Value flag
        flag = self._get_value_flag(edge, ev)
        # Bucket eligibility
        bucket_elig = self._get_bucket_eligibility(market_type, selection, flag, odds)

        return MarketCandidate(
            match_id=match_id,
            match_number=match_number,
            market_type=market_type,
            selection=selection_label,
            home_team=home_team,
            away_team=away_team,
            stage=stage,
            mock_odds=round(odds, 2),
            model_probability=round(model_prob, 4),
            market_probability=round(market_prob, 4),
            no_vig_probability=round(no_vig_prob, 4),
            edge=round(edge, 4),
            ev=round(ev, 4),
            odds_band=band,
            value_flag=flag,
            bucket_eligibility=bucket_elig,
        )

    def _get_odds_band(self, odds: float) -> str:
        for band in self.odds_bands:
            parts = band.split("-")
            if len(parts) == 2:
                low = float(parts[0])
                high = float(parts[1])
                if odds < high:
                    return band
        return self.odds_bands[-1] if self.odds_bands else "unknown"

    def _get_value_flag(self, edge: float, ev: float) -> str:
        for flag, criteria in self.value_flags.items():
            if edge >= criteria["min_edge"] and ev >= criteria["min_ev"]:
                return flag
        return "no_value"

    def _get_bucket_eligibility(
        self, market_type: str, selection: str, value_flag: str, odds: float
    ) -> list[str]:
        """Determine which buckets a candidate is eligible for."""
        buckets = []
        if value_flag in ("strong_value", "value"):
            if "1x2" in market_type and odds < 2.0:
                buckets.append("core")
            elif "over_under" in market_type:
                buckets.append("edge")
            if odds >= 5.0:
                buckets.append("attack")
        if value_flag == "strong_value" and odds >= 2.5:
            buckets.append("edge")
        return buckets