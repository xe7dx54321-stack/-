"""Tests for odds_normalizer module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.odds_normalizer import normalize_odds_entries, NormalizedOddsEntry


class FakeEntry:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestNormalizer:
    def test_normalize_basic(self):
        entries = [
            FakeEntry(match_id="M1", market_type="1X2", selection_id="H", selection_label="Home", decimal_odds=2.0, source_provider="A", snapshot_type="current", snapshot_timestamp="2026-06-11T10:00:00Z"),
        ]
        result = normalize_odds_entries(entries)
        assert result.normalized_count == 1
        assert result.entries[0].implied_probability == 0.5

    def test_invalid_odds_clamped(self):
        entries = [
            FakeEntry(match_id="M1", market_type="1X2", selection_id="H", selection_label="Home", decimal_odds=0.5, source_provider="A", snapshot_type="current", snapshot_timestamp=""),
        ]
        result = normalize_odds_entries(entries)
        assert result.invalid_count == 1

    def test_multiple_sources(self):
        entries = [
            FakeEntry(match_id="M1", market_type="1X2", selection_id="H", selection_label="H", decimal_odds=2.0, source_provider="A", snapshot_type="current", snapshot_timestamp=""),
            FakeEntry(match_id="M1", market_type="1X2", selection_id="H", selection_label="H", decimal_odds=2.1, source_provider="B", snapshot_type="current", snapshot_timestamp=""),
        ]
        result = normalize_odds_entries(entries)
        assert len(result.source_providers) == 2
        assert result.normalized_count == 2

    def test_snapshot_date_extracted(self):
        entries = [
            FakeEntry(match_id="M1", market_type="1X2", selection_id="H", selection_label="H", decimal_odds=2.0, source_provider="A", snapshot_type="current", snapshot_timestamp="2026-06-11T10:00:00Z"),
        ]
        result = normalize_odds_entries(entries)
        assert result.snapshot_date == "2026-06-11"

    def test_unknown_market_warning(self):
        entries = [
            FakeEntry(match_id="M1", market_type="unknown_market", selection_id="X", selection_label="X", decimal_odds=2.0, source_provider="A", snapshot_type="current", snapshot_timestamp=""),
        ]
        result = normalize_odds_entries(entries)
        assert result.entries[0].validation_warning != ""
