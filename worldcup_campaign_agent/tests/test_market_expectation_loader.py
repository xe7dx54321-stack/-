"""Tests for market_expectation_loader module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.market_expectation_loader import (
    load_market_expectation_sources, extract_model_probabilities,
    extract_sportsbook_probabilities, extract_polymarket_probabilities
)
ROOT = Path(__file__).resolve().parent.parent
RDIR = str(ROOT / "reports" / "generated")
class TestLoader:
    def test_load_sources(self):
        s = load_market_expectation_sources(RDIR)
        assert s.model_available or s.sportsbook_available or s.polymarket_available
    def test_extract_model(self):
        s = load_market_expectation_sources(RDIR)
        p = extract_model_probabilities(s.model_data)
        assert len(p) > 0
    def test_extract_sportsbook(self):
        s = load_market_expectation_sources(RDIR)
        p = extract_sportsbook_probabilities(s.sportsbook_data)
        assert len(p) >= 0
    def test_extract_polymarket(self):
        s = load_market_expectation_sources(RDIR)
        p = extract_polymarket_probabilities(s.polymarket_data)
        assert len(p) > 0
    def test_no_stake(self):
        s = load_market_expectation_sources(RDIR)
        js = json.dumps({"model_avail": s.model_available, "warnings": s.source_warnings})
        assert "stake" not in js.lower()
