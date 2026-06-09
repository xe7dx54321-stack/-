"""Tests for odds_freshness module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.odds_freshness import check_odds_freshness
from worldcup_campaign.odds_normalizer import NormalizedOddsEntry


class TestFreshness:
    def test_no_timestamps(self):
        entries = [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=2.0, source_provider="A"),
        ]
        snapshot = type('obj', (), {'entries': entries})()
        result = check_odds_freshness(snapshot)
        assert "No timestamped" in result.warnings[0]

    def test_fresh_entries(self):
        entries = [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=2.0, source_provider="A", snapshot_timestamp="2026-06-11T10:00:00Z"),
        ]
        snapshot = type('obj', (), {'entries': entries})()
        result = check_odds_freshness(snapshot, reference_time="2026-06-11T12:00:00Z")
        assert result.fresh_count == 1

    def test_stale_entries(self):
        entries = [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=2.0, source_provider="A", snapshot_timestamp="2026-06-09T10:00:00Z"),
        ]
        snapshot = type('obj', (), {'entries': entries})()
        result = check_odds_freshness(snapshot, reference_time="2026-06-11T12:00:00Z", config={"freshness": {"stale_age_hours": 24}})
        assert result.stale_count == 1

    def test_warning_count(self):
        entries = [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=2.0, source_provider="A", snapshot_timestamp="2026-06-11T02:00:00Z"),
        ]
        snapshot = type('obj', (), {'entries': entries})()
        result = check_odds_freshness(snapshot, reference_time="2026-06-11T12:00:00Z", config={"freshness": {"warn_age_hours": 8, "max_age_hours": 24, "stale_age_hours": 48}})
        assert result.freshness_warning_count == 1
