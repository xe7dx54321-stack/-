"""Tests for market_model_gap module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.market_model_gap import compute_model_vs_market_gap
from worldcup_campaign.odds_normalizer import NormalizedOddsEntry


class TestModelGap:
    def test_gap_computation(self):
        entries = [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=2.0, source_provider="A"),
        ]
        snapshot = type('obj', (), {'entries': entries})()
        mp_data = {"matches": [{"match_id": "M1", "home_probability": 0.55}]}
        result = compute_model_vs_market_gap(snapshot, mp_data)
        assert result.record_count == 1
        assert result.records[0].gap != 0.0

    def test_direction_classification(self):
        entries = [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=2.0, source_provider="A"),
        ]
        snapshot = type('obj', (), {'entries': entries})()
        mp_data = {"matches": [{"match_id": "M1", "home_probability": 0.55}]}
        result = compute_model_vs_market_gap(snapshot, mp_data)
        assert result.records[0].direction in ("model_above", "model_below", "aligned")

    def test_no_match_data(self):
        entries = [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=2.0, source_provider="A"),
        ]
        snapshot = type('obj', (), {'entries': entries})()
        result = compute_model_vs_market_gap(snapshot, {})
        assert result.record_count == 0

    def test_average_gap(self):
        entries = [
            NormalizedOddsEntry(match_id="M1", market_type="1X2", selection_id="H", decimal_odds=2.0, source_provider="A"),
            NormalizedOddsEntry(match_id="M2", market_type="1X2", selection_id="A", decimal_odds=3.0, source_provider="A"),
        ]
        snapshot = type('obj', (), {'entries': entries})()
        mp_data = {"matches": [
            {"match_id": "M1", "home_probability": 0.55},
            {"match_id": "M2", "away_probability": 0.30},
        ]}
        result = compute_model_vs_market_gap(snapshot, mp_data)
        assert result.average_gap > 0
