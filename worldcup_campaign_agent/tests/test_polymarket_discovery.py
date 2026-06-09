"""Tests for polymarket_discovery module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.polymarket_discovery import (
    load_polymarket_fixture, discover_polymarket_markets
)
ROOT = Path(__file__).resolve().parent.parent
SEED = str(ROOT / "data" / "seed" / "polymarket_seed.json")
CONFIG = {
    "discovery": {"relevant_tags": ["world cup","fifa","soccer","wc2026","2026"], "min_volume_for_consideration": 1000, "deferred_tags": ["golden boot","golden ball"]},
    "liquidity": {"high_liquidity_threshold": 100000, "medium_liquidity_threshold": 10000},
}
class TestDiscovery:
    def test_load_fixture(self):
        f = load_polymarket_fixture(SEED)
        assert len(f["events"]) >= 3
    def test_discover_events(self):
        f = load_polymarket_fixture(SEED)
        d = discover_polymarket_markets(f, CONFIG)
        assert d.event_count >= 3
        assert d.relevant_event_count >= 3
    def test_market_count(self):
        f = load_polymarket_fixture(SEED)
        d = discover_polymarket_markets(f, CONFIG)
        assert d.market_count >= 10
    def test_relevant_market_count(self):
        f = load_polymarket_fixture(SEED)
        d = discover_polymarket_markets(f, CONFIG)
        assert d.relevant_market_count >= 10
    def test_mapped_market_count(self):
        f = load_polymarket_fixture(SEED)
        d = discover_polymarket_markets(f, CONFIG)
        assert d.mapped_market_count >= 10
    def test_non_wc_event_excluded(self):
        f = load_polymarket_fixture(SEED)
        d = discover_polymarket_markets(f, CONFIG)
        nba_events = [e for e in d.events if "nba" in e.event_id.lower()]
        assert len(nba_events) >= 1
        assert not nba_events[0].is_relevant
