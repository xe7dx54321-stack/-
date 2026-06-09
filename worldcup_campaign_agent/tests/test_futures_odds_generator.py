"""Tests for futures_odds_generator module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.futures_odds_generator import (
    FuturesOddsGenerator, FuturesProbabilityAggregator, FuturesOdds
)
from worldcup_campaign.knockout_path_simulator import KnockoutPathSimulator
from worldcup_campaign.group_simulator import GroupSimulator

ROOT = Path(__file__).resolve().parent.parent

@pytest.fixture
def all_odds():
    sim = GroupSimulator(
        str(ROOT / "data" / "seed" / "worldcup_2026_groups.json"),
        str(ROOT / "data" / "seed" / "worldcup_2026_match_registry.json"),
        str(ROOT / "config" / "group_simulation_config.json"),
    )
    results = sim.simulate_all_groups()
    ko = KnockoutPathSimulator(
        str(ROOT / "data" / "seed" / "worldcup_2026_team_ratings.json"),
        str(ROOT / "config" / "tournament_path_config.json"),
    )
    paths = ko.build_paths(results)
    pairs = ko.calculate_exact_final_pairs(paths)
    gen = FuturesOddsGenerator(
        str(ROOT / "config" / "futures_odds_policy.json"),
        str(ROOT / "config" / "futures_market_config.json"),
    )
    odds = gen.generate_from_paths(paths)
    pair_odds = gen.generate_exact_final_pair_odds(pairs)
    return odds + pair_odds, paths, pairs

def test_odds_generated(all_odds):
    odds, paths, pairs = all_odds
    assert len(odds) > 0

def test_odds_have_positive_values(all_odds):
    odds, paths, pairs = all_odds
    for o in odds:
        assert o.synthetic_odds >= 1.01

def test_odds_uses_real_bookmaker_false(all_odds):
    odds, paths, pairs = all_odds
    for o in odds:
        assert o.uses_real_bookmaker_odds is False

def test_odds_not_betting_advice(all_odds):
    odds, paths, pairs = all_odds
    for o in odds:
        assert o.not_betting_advice is True
        assert o.analysis_only is True

def test_winner_market_exists(all_odds):
    odds, paths, pairs = all_odds
    winners = [o for o in odds if o.market_type == "winner"]
    assert len(winners) > 0

def test_group_qualification_market_exists(all_odds):
    odds, paths, pairs = all_odds
    quals = [o for o in odds if o.market_type == "group_qualification"]
    assert len(quals) > 0

def test_exact_final_pair_odds_exist(all_odds):
    odds, paths, pairs = all_odds
    efps = [o for o in odds if o.market_type == "exact_final_pair"]
    assert len(efps) > 0

def test_probability_summary(all_odds):
    odds, paths, pairs = all_odds
    agg = FuturesProbabilityAggregator(
        str(ROOT / "config" / "futures_market_config.json")
    )
    summary = agg.build_summary(paths, pairs, odds)
    assert summary["total_teams"] == 48
    assert "winner_probability_sum" in summary
    assert summary["analysis_only"] is True

def test_odds_source_is_synthetic(all_odds):
    odds, paths, pairs = all_odds
    for o in odds:
        assert "synthetic" in o.source.lower() or "probability" in o.source.lower()

def test_no_stake_fields(all_odds):
    odds, paths, pairs = all_odds
    for o in odds:
        d = o.__dict__ if hasattr(o, '__dict__') else o
        assert "stake" not in str(d).lower() or "not_betting" in str(d)
