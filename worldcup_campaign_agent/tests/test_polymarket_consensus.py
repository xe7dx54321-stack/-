"""Tests for polymarket_consensus module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.polymarket_discovery import load_polymarket_fixture, discover_polymarket_markets
from worldcup_campaign.polymarket_consensus import build_polymarket_consensus
ROOT = Path(__file__).resolve().parent.parent
SEED = str(ROOT / "data" / "seed" / "polymarket_seed.json")
CONFIG = {
    "discovery": {"relevant_tags": ["world cup","fifa","soccer","wc2026"], "min_volume_for_consideration":1000,"deferred_tags":["golden boot"]},
    "liquidity": {"high_liquidity_threshold":100000,"medium_liquidity_threshold":10000},
    "consensus": {"strong_consensus_threshold":0.03,"usable_consensus_threshold":0.08},
}
class TestConsensus:
    def test_build_consensus(self):
        f = load_polymarket_fixture(SEED)
        d = discover_polymarket_markets(f, CONFIG)
        c = build_polymarket_consensus(d, CONFIG)
        assert c.prediction_consensus_count > 0
    def test_has_consensus_records(self):
        f = load_polymarket_fixture(SEED)
        d = discover_polymarket_markets(f, CONFIG)
        c = build_polymarket_consensus(d, CONFIG)
        assert len(c.consensus_records) > 0
