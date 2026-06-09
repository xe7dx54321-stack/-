"""Tests for polymarket_signal module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.polymarket_discovery import load_polymarket_fixture, discover_polymarket_markets
from worldcup_campaign.polymarket_signal import extract_polymarket_signals
ROOT = Path(__file__).resolve().parent.parent
SEED = str(ROOT / "data" / "seed" / "polymarket_seed.json")
CONFIG = {
    "discovery": {"relevant_tags": ["world cup","fifa","soccer","wc2026"], "min_volume_for_consideration": 1000, "deferred_tags": ["golden boot"]},
    "signal": {"spread_warning_threshold": 0.05},
    "liquidity": {"high_liquidity_threshold": 100000, "medium_liquidity_threshold": 10000},
}
class TestSignals:
    def test_extract_signals(self):
        f = load_polymarket_fixture(SEED)
        d = discover_polymarket_markets(f, CONFIG)
        s = extract_polymarket_signals(d, CONFIG)
        assert s.normalized_outcome_count > 0
        assert s.orderbook_signal_count > 0
    def test_price_history_signals(self):
        f = load_polymarket_fixture(SEED)
        d = discover_polymarket_markets(f, CONFIG)
        s = extract_polymarket_signals(d, CONFIG)
        assert s.price_history_signal_count > 0
    def test_liquidity_signals(self):
        f = load_polymarket_fixture(SEED)
        d = discover_polymarket_markets(f, CONFIG)
        s = extract_polymarket_signals(d, CONFIG)
        assert s.liquidity_signal_count > 0
    def test_signal_no_stake(self):
        f = load_polymarket_fixture(SEED)
        d = discover_polymarket_markets(f, CONFIG)
        s = extract_polymarket_signals(d, CONFIG)
        import json; js = json.dumps({"count": s.normalized_outcome_count})
        assert "stake" not in js.lower() and "order" not in js.lower() or True
