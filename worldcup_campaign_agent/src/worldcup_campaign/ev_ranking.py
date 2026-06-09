"""EV ranking: ranks market candidates by expected value."""

from dataclasses import dataclass, field

from worldcup_campaign.market_candidate import MarketCandidate


@dataclass
class EVRanking:
    date: str
    candidate_count: int
    value_candidate_count: int
    odds_source_mode: str
    uses_real_bookmaker_odds: bool = False
    candidates: list[MarketCandidate] = field(default_factory=list)
    sanity_summary: dict = field(default_factory=dict)
    not_betting_advice: bool = True


class EVRanker:
    """Ranks market candidates by EV."""

    def __init__(self, max_candidates: int = 50):
        self.max_candidates = max_candidates

    def rank(
        self,
        candidates: list[MarketCandidate],
        date: str,
        odds_source_mode: str,
        sanity_summary: dict = None,
    ) -> EVRanking:
        """Rank candidates by EV descending."""
        # Filter out blocked candidates
        valid = [c for c in candidates if not c.is_blocked]
        # Sort by EV descending
        valid.sort(key=lambda c: c.ev, reverse=True)
        # Limit
        valid = valid[:self.max_candidates]
        # Count value candidates
        value_count = sum(1 for c in valid if c.value_flag in ("strong_value", "value"))

        return EVRanking(
            date=date,
            candidate_count=len(valid),
            value_candidate_count=value_count,
            odds_source_mode=odds_source_mode,
            uses_real_bookmaker_odds=False,
            candidates=valid,
            sanity_summary=sanity_summary or {},
            not_betting_advice=True,
        )