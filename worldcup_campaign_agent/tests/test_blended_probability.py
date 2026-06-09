"""Tests for blended_probability module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.blended_probability import compute_blended_probability
from worldcup_campaign.signal_quality import assess_signal_quality
class TestBlended:
    def test_blend(self):
        s = {"model_probs":{"M1_H":0.50},"sportsbook_probs":{"M1_H":0.48},"polymarket_probs":{},
             "model_data":{"matches":[]},"sportsbook_data":{"normalized_snapshot":{"source_providers":["A","B"]},"freshness_summary":{"stale_count":0}},"polymarket_data":{"discovery_summary":{"events":[]}}}
        q = assess_signal_quality(s)
        b = compute_blended_probability(s, q)
        assert b.blended_record_count > 0
    def test_weights_sum(self):
        s = {"model_probs":{"M1_H":0.5},"sportsbook_probs":{"M1_H":0.5},"polymarket_probs":{},
             "model_data":{"matches":[]},"sportsbook_data":{"normalized_snapshot":{"source_providers":["A"]},"freshness_summary":{"stale_count":0}},"polymarket_data":{"discovery_summary":{"events":[]}}}
        q = assess_signal_quality(s)
        b = compute_blended_probability(s, q)
        r = b.records[0]
        total = r.model_weight + r.sportsbook_weight + r.polymarket_weight
        assert abs(total - 1.0) < 0.01
