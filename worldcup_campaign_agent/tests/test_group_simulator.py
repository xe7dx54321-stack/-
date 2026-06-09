"""Tests for group_simulator module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.group_simulator import GroupSimulator, GroupResult, GroupStanding

ROOT = Path(__file__).resolve().parent.parent
GROUPS = str(ROOT / "data" / "seed" / "worldcup_2026_groups.json")
MATCHES = str(ROOT / "data" / "seed" / "worldcup_2026_match_registry.json")
CONFIG = str(ROOT / "config" / "group_simulation_config.json")


def test_simulate_all_12_groups():
    sim = GroupSimulator(GROUPS, MATCHES, CONFIG)
    results = sim.simulate_all_groups()
    assert len(results) == 12


def test_each_group_has_4_standings():
    sim = GroupSimulator(GROUPS, MATCHES, CONFIG)
    results = sim.simulate_all_groups()
    for r in results:
        assert len(r.standings) == 4


def test_expected_points_in_range():
    sim = GroupSimulator(GROUPS, MATCHES, CONFIG)
    results = sim.simulate_all_groups()
    for r in results:
        for s in r.standings:
            assert 0 <= s.expected_points <= 9


def test_qualification_prob_in_range():
    sim = GroupSimulator(GROUPS, MATCHES, CONFIG)
    results = sim.simulate_all_groups()
    for r in results:
        for s in r.standings:
            assert 0 <= s.qualification_probability <= 1


def test_24_qualifiers():
    sim = GroupSimulator(GROUPS, MATCHES, CONFIG)
    results = sim.simulate_all_groups()
    qualifiers = sim.get_all_qualifiers(results)
    assert len(qualifiers) == 24


def test_12_third_place_teams():
    sim = GroupSimulator(GROUPS, MATCHES, CONFIG)
    results = sim.simulate_all_groups()
    thirds = sim.get_third_place_teams(results)
    assert len(thirds) == 12


def test_8_best_third_place_qualifiers():
    sim = GroupSimulator(GROUPS, MATCHES, CONFIG)
    results = sim.simulate_all_groups()
    best_thirds = sim.get_best_third_place_qualifiers(results, 8)
    assert len(best_thirds) == 8


def test_rankings_are_1_to_4():
    sim = GroupSimulator(GROUPS, MATCHES, CONFIG)
    results = sim.simulate_all_groups()
    for r in results:
        ranks = [s.rank for s in r.standings]
        assert sorted(ranks) == [1, 2, 3, 4]


def test_group_winner_is_rank_1():
    sim = GroupSimulator(GROUPS, MATCHES, CONFIG)
    results = sim.simulate_all_groups()
    for r in results:
        winner = r.group_winner
        rank1 = [s for s in r.standings if s.rank == 1][0]
        assert winner == rank1.team_code
