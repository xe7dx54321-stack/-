"""Tests for polymarket_gap module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.polymarket_discovery import load_polymarket_fixture, discover_polymarket_markets
from worldcup_campaign.polymarket_signal import extract_polymarket_signals
from worldcup_campaign.polymarket_consensus import build_polymarket_consensus
from worldcup_campaign.polymarket_gap import analyze_polymarket_gaps
ROOT = Path(__file__).resolve().parent.parent
SEED = str(ROOT / "data" / "seed" / "polymarket_seed.json")
CONFIG = {
    "discovery": {"relevant_tags":["world cup","fifa","soccer","wc2026"],"min_volume_for_consideration":1000,"deferred_tags":["golden boot"]},
    "liquidity": {"high_liquidity_threshold":100000,"medium_liquidity_threshold":10000},
    "signal": {"spread_warning_threshold":0.05},
    "consensus": {"strong_consensus_threshold":0.03,"usable_consensus_threshold":0.08},
    "gap_analysis": {"major_disagreement_threshold":0.15,"minor_disagreement_threshold":0.05},
}
class TestGaps:
    def test_gaps_generated(self):
        f = load_polymarket_fixture(SEED)
        d = discover_polymarket_markets(f, CONFIG)
        s = extract_polymarket_signals(d, CONFIG)
        c = build_polymarket_consensus(d, CONFIG)
        g = analyze_polymarket_gaps(d, s, c, {}, {}, CONFIG)
        assert g.gap_record_count > 0
    def test_no_stake_no_order(self):
        f = load_polymarket_fixture(SEED)
        d = discover_polymarket_markets(f, CONFIG)
        s = extract_polymarket_signals(d, CONFIG)
        c = build_polymarket_consensus(d, CONFIG)
        g = analyze_polymarket_gaps(d, s, c, {}, {}, CONFIG)
        import json; js = json.dumps({"count":g.gap_record_count})
        assert "stake" not in js.lower()
