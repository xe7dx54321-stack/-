"""Tests for market_consensus module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.market_consensus import build_market_consensus, _classify_consensus_strength
from worldcup_campaign.odds_normalizer import NormalizedOddsEntry
from worldcup_campaign.no_vig_calculator import build_no_vig_markets, NoVigSummary


class TestClassifyConsensusStrength:
    def test_two_sources_not_strong(self):
        level = _classify_consensus_strength(2, 0.02, 3, 2, 0.03, 0.08, 0.12)
        assert level in ("usable", "weak")

    def test_three_sources_low_dispersion_strong(self):
        level = _classify_consensus_strength(3, 0.02, 3, 2, 0.03, 0.08, 0.12)
        assert level == "strong"

    def test_one_source_weak(self):
        level = _classify_consensus_strength(1, 0.01, 3, 2, 0.03, 0.08, 0.12)
        assert level == "weak"

    def test_high_dispersion_downgrades(self):
        level = _classify_consensus_strength(3, 0.20, 3, 2, 0.03, 0.08, 0.12)
        assert level == "weak"


class TestConsensus:
    def _make_entries_2source(self):
        return [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=1.85, source_provider="A"),
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="D", decimal_odds=3.50, source_provider="A"),
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="A", decimal_odds=4.20, source_provider="A"),
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=1.90, source_provider="B"),
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="D", decimal_odds=3.40, source_provider="B"),
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="A", decimal_odds=4.23, source_provider='B'),
        ]

    def _make_entries_3source(self):
        return self._make_entries_2source() + [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=1.87, source_provider='C'),
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="D", decimal_odds=3.48, source_provider='C'),
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="A", decimal_odds=4.28, source_provider='C'),
        ]

    def test_two_sources_strong_count_zero(self):
        entries = self._make_entries_2source()
        snapshot = type('obj', (), {'entries': entries})()
        no_vig = build_no_vig_markets(snapshot)
        result = build_market_consensus(snapshot, no_vig)
        assert result.strong_consensus_count == 0
        assert result.usable_consensus_count + result.weak_consensus_count >= 1

    def test_three_sources_can_be_strong(self):
        entries = self._make_entries_3source()
        snapshot = type('obj', (), {'entries': entries})()
        no_vig = build_no_vig_markets(snapshot)
        result = build_market_consensus(snapshot, no_vig)
        # 3 sources with low dispersion should be strong
        assert result.strong_consensus_count >= 1

    def test_insufficient_sources(self):
        entries = [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=2.0, source_provider="A"),
        ]
        snapshot = type('obj', (), {'entries': entries})()
        no_vig = NoVigSummary()
        result = build_market_consensus(snapshot, no_vig)
        assert result.markets[0].consensus_level == "insufficient_data"

    def test_dispersion_warning(self):
        entries = [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=1.50, source_provider="A"),
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=3.00, source_provider="B"),
        ]
        snapshot = type('obj', (), {'entries': entries})()
        no_vig = NoVigSummary()
        result = build_market_consensus(snapshot, no_vig, {
            "consensus": {
                "min_sources_for_consensus": 2,
                "min_sources_for_strong_consensus": 3,
                "min_sources_for_usable_consensus": 2,
                "dispersion_warning_threshold": 0.1,
                "strong_consensus_threshold": 0.03,
                "usable_consensus_threshold": 0.08,
            }
        })
        assert result.dispersion_warning_count >= 1
        assert result.strong_consensus_count == 0
