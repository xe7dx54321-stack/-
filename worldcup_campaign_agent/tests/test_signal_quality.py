"""Tests for signal_quality module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.signal_quality import assess_signal_quality
class TestQuality:
    def test_empty(self):
        s = {"model_probs":{},"sportsbook_probs":{},"polymarket_probs":{},"model_data":{},"sportsbook_data":{},"polymarket_data":{}}
        q = assess_signal_quality(s)
        assert q.average_quality_score == 0
    def test_with_data(self):
        s = {"model_probs":{"M1_H":0.5},"sportsbook_probs":{"M1_H":0.48},"polymarket_probs":{},
             "model_data":{"matches":[{"confidence":0.2}]},
             "sportsbook_data":{"normalized_snapshot":{"source_providers":["A","B"]},"no_vig_summary":{"average_overround":0.06},"freshness_summary":{"stale_count":0}},
             "polymarket_data":{"discovery_summary":{"events":[]}}}
        q = assess_signal_quality(s)
        assert q.high_quality_count + q.medium_quality_count + q.low_quality_count > 0
