"""Tests for knockout_path_simulator module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.knockout_path_simulator import KnockoutPathSimulator, TournamentPath
from worldcup_campaign.group_simulator import GroupSimulator

ROOT = Path(__file__).resolve().parent.parent
RATINGS = str(ROOT / "data" / "seed" / "worldcup_2026_team_ratings.json")
TP_CONFIG = str(ROOT / "config" / "tournament_path_config.json")
GROUPS = str(ROOT / "data" / "seed" / "worldcup_2026_groups.json")
MATCHES = str(ROOT / "data" / "seed" / "worldcup_2026_match_registry.json")
GS_CONFIG = str(ROOT / "config" / "group_simulation_config.json")

@pytest.fixture
def paths():
    sim = GroupSimulator(GROUPS, MATCHES, GS_CONFIG)
    results = sim.simulate_all_groups()
    ko = KnockoutPathSimulator(RATINGS, TP_CONFIG)
    return ko.build_paths(results)

def test_48_path_entries(paths):
    assert len(paths) == 48

def test_each_path_has_probabilities(paths):
    for p in paths:
        assert 0 <= p.group_qual_prob <= 1
        assert 0 <= p.winner_prob <= 1
        assert 0 <= p.runner_up_prob <= 1

def test_winner_probability_sum_close_to_1(paths):
    total = sum(p.winner_prob for p in paths)
    assert 0.5 <= total <= 1.3, f"Winner prob sum={total}"

def test_probability_chain_decreases(paths):
    for p in paths:
        assert p.reach_r32 >= p.reach_r16 >= p.reach_qf >= p.reach_sf >= p.reach_final >= p.winner_prob

def test_exact_final_pairs(paths):
    ko = KnockoutPathSimulator(RATINGS, TP_CONFIG)
    pairs = ko.calculate_exact_final_pairs(paths)
    assert len(pairs) > 0
    total = sum(x["probability"] for x in pairs)
    assert total > 0

def test_team_path_lookup(paths):
    ko = KnockoutPathSimulator(RATINGS, TP_CONFIG)
    p = ko.get_team_path("ARG", paths)
    assert p is not None
    assert p.team_code == "ARG"

def test_unknown_team_returns_none(paths):
    ko = KnockoutPathSimulator(RATINGS, TP_CONFIG)
    p = ko.get_team_path("ZZZ", paths)
    assert p is None

def test_advance_prob_in_range():
    ko = KnockoutPathSimulator(RATINGS, TP_CONFIG)
    p = ko._advance_prob(2000, 1500)
    assert 0 < p < 1
