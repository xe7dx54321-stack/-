"""Tests for odds_movement module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.odds_movement import analyze_odds_movement
from worldcup_campaign.odds_normalizer import NormalizedOddsEntry


class TestMovement:
    def test_no_opening_odds(self):
        entries = [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=2.0, source_provider="A", snapshot_type="current"),
        ]
        snapshot = type('obj', (), {'entries': entries})()
        result = analyze_odds_movement(snapshot)
        assert result.insufficient_history_count > 0

    def test_movement_between_snapshots(self):
        entries = [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=1.80, source_provider="A", snapshot_type="opening"),
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=1.90, source_provider="A", snapshot_type="current"),
        ]
        snapshot = type('obj', (), {'entries': entries})()
        result = analyze_odds_movement(snapshot)
        assert result.record_count == 1
        assert result.records[0].direction in ("drift", "steam", "stable")

    def test_significant_move(self):
        entries = [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=1.50, source_provider="A", snapshot_type="opening"),
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=2.10, source_provider="A", snapshot_type="current"),
        ]
        snapshot = type('obj', (), {'entries': entries})()
        result = analyze_odds_movement(snapshot, {"movement": {"significant_move_threshold": 0.05}})
        assert result.significant_move_count == 1
