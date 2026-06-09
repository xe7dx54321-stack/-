"""Tests for market_alignment module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.market_alignment import assess_market_alignment
class TestAlignment:
    def test_aligned(self):
        s = {"model_probs":{"M1_H":0.50},"sportsbook_probs":{"M1_H":0.51},"polymarket_probs":{"M1_H":0.505}}
        a = assess_market_alignment(s)
        assert a.record_count > 0
        assert a.market_aligned_count >= 1
    def test_disagreement(self):
        s = {"model_probs":{"M1_H":0.80},"sportsbook_probs":{"M1_H":0.50},"polymarket_probs":{}}
        a = assess_market_alignment(s)
        assert a.major_disagreement_count >= 1
    def test_insufficient(self):
        s = {"model_probs":{"M1_H":0.5},"sportsbook_probs":{},"polymarket_probs":{}}
        a = assess_market_alignment(s)
        assert a.insufficient_data_count >= 1
