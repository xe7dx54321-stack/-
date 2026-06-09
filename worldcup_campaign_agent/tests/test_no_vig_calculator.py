"""Tests for no_vig_calculator module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.no_vig_calculator import (
    calculate_overround, calculate_no_vig_probabilities, build_no_vig_markets
)
from worldcup_campaign.odds_normalizer import NormalizedOddsEntry


class TestOverround:
    def test_fair_market(self):
        assert calculate_overround([2.0, 2.0]) == 0.0

    def test_typical_overround(self):
        or_ = calculate_overround([1.85, 3.50, 4.20])
        assert or_ > 0.04

    def test_no_vig_probs_sum_to_one(self):
        probs = calculate_no_vig_probabilities([1.85, 3.50, 4.20])
        assert abs(sum(probs) - 1.0) < 0.001

    def test_empty_odds(self):
        assert calculate_overround([]) == 0.0

class TestNoVigMarkets:
    def test_build_markets(self):
        entries = [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=2.0, source_provider="A"),
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="D", decimal_odds=3.5, source_provider="A"),
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="A", decimal_odds=4.0, source_provider="A"),
        ]
        snapshot = type('obj', (), {'entries': entries, 'source_providers': ['A']})()
        summary = build_no_vig_markets(snapshot)
        assert summary.market_count >= 1

    def test_overround_warning(self):
        entries = [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=1.5, source_provider="A"),
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="D", decimal_odds=3.0, source_provider="A"),
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="A", decimal_odds=4.0, source_provider="A"),
        ]
        snapshot = type('obj', (), {'entries': entries, 'source_providers': ['A']})()
        summary = build_no_vig_markets(snapshot, {"overround_policy": {"warn_overround": 0.05}})
        assert summary.average_overround > 0.05
