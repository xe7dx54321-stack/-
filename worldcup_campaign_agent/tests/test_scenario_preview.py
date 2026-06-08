"""Tests for scenario preview."""

from pathlib import Path

import pytest

from worldcup_campaign.scenario_preview import ScenarioPreview
from worldcup_campaign.strategy_profile import StrategyProfileSelector
from worldcup_campaign.strategy_allocator import StrategyAllocator
from worldcup_campaign.match_strategy_labeler import MatchStrategyLabeler
from worldcup_campaign.match_registry import load_match_registry, get_matches_by_date
from datetime import date


def _config_path(filename: str) -> str:
    return str(Path(__file__).resolve().parent.parent / "config" / filename)

def _data_path(filename: str) -> str:
    return str(Path(__file__).resolve().parent.parent / "data" / "seed" / filename)


class TestScenarioPreview:
    @pytest.fixture
    def preview(self):
        return ScenarioPreview(
            _config_path("scenario_rules.json"),
            _config_path("bankroll_states.json"),
        )

    @pytest.fixture
    def allocator(self):
        return StrategyAllocator()

    @pytest.fixture
    def selector(self):
        return StrategyProfileSelector(_config_path("daily_strategy_rules.json"))

    @pytest.fixture
    def labeler(self):
        return MatchStrategyLabeler(_config_path("match_tagging_rules.json"))

    @pytest.fixture
    def matches(self):
        return load_match_registry(_data_path("worldcup_2026_match_registry.json"))

    def test_four_scenarios(self, preview, allocator, selector, labeler, matches):
        profile = selector.select_profile("group_round_1", "S2")
        today = date(2026, 6, 11)
        today_ms = get_matches_by_date(today, matches)
        labeled = labeler.label_matches(today_ms, today)
        buckets = {"reserve": 50.0, "core": 10.0, "edge": 15.0, "attack": 20.0, "futures": 5.0}
        plan = allocator.allocate(buckets, profile, labeled)
        
        scenarios = preview.generate_previews(100.0, plan, 1000000.0)
        assert len(scenarios) == 4

    def test_all_miss_preserves_reserve(self, preview, allocator, selector, labeler, matches):
        profile = selector.select_profile("group_round_1", "S2")
        today = date(2026, 6, 11)
        today_ms = get_matches_by_date(today, matches)
        labeled = labeler.label_matches(today_ms, today)
        buckets = {"reserve": 50.0, "core": 10.0, "edge": 15.0, "attack": 20.0, "futures": 5.0}
        plan = allocator.allocate(buckets, profile, labeled)
        
        scenarios = preview.generate_previews(100.0, plan, 1000000.0)
        all_miss = [s for s in scenarios if s.scenario_name == "all_miss"][0]
        assert all_miss.projected_bankroll == 50.0

    def test_all_hit_greater_than_current(self, preview, allocator, selector, labeler, matches):
        profile = selector.select_profile("group_round_1", "S2")
        today = date(2026, 6, 11)
        today_ms = get_matches_by_date(today, matches)
        labeled = labeler.label_matches(today_ms, today)
        buckets = {"reserve": 50.0, "core": 10.0, "edge": 15.0, "attack": 20.0, "futures": 5.0}
        plan = allocator.allocate(buckets, profile, labeled)
        
        scenarios = preview.generate_previews(100.0, plan, 1000000.0)
        all_hit = [s for s in scenarios if s.scenario_name == "all_hit"][0]
        assert all_hit.projected_bankroll > 100.0

    def test_projected_state_valid(self, preview, allocator, selector, labeler, matches):
        profile = selector.select_profile("group_round_1", "S2")
        today = date(2026, 6, 11)
        today_ms = get_matches_by_date(today, matches)
        labeled = labeler.label_matches(today_ms, today)
        buckets = {"reserve": 50.0, "core": 10.0, "edge": 15.0, "attack": 20.0, "futures": 5.0}
        plan = allocator.allocate(buckets, profile, labeled)
        
        scenarios = preview.generate_previews(100.0, plan, 1000000.0)
        for s in scenarios:
            assert s.projected_state in [
                "S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "TARGET_REACHED"
            ]