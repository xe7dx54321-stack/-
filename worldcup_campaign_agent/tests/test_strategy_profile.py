"""Tests for strategy profile selector."""

from pathlib import Path

import pytest

from worldcup_campaign.strategy_profile import StrategyProfileSelector, StrategyProfile


def _config_path(filename: str) -> str:
    return str(Path(__file__).resolve().parent.parent / "config" / filename)


class TestStrategyProfileSelector:
    @pytest.fixture
    def selector(self):
        return StrategyProfileSelector(_config_path("daily_strategy_rules.json"))

    def test_group_r1_S2_is_balanced(self, selector):
        profile = selector.select_profile("group_round_1", "S2")
        assert profile.name == "balanced"

    def test_group_r1_S0_is_very_aggressive(self, selector):
        profile = selector.select_profile("group_round_1", "S0")
        assert profile.name == "very_aggressive"

    def test_group_r1_S1_is_aggressive(self, selector):
        profile = selector.select_profile("group_round_1", "S1")
        assert profile.name == "aggressive"

    def test_S6_override(self, selector):
        profile = selector.select_profile("group_round_1", "S6")
        assert profile.name == "conservative"

    def test_S7_override(self, selector):
        profile = selector.select_profile("group_round_1", "S7")
        assert profile.name == "target_chase"

    def test_final_S2_is_conservative(self, selector):
        profile = selector.select_profile("final", "S2")
        assert profile.name == "conservative"

    def test_balanced_allows_all_buckets(self, selector):
        profile = selector.select_profile("group_round_1", "S2")
        assert profile.allow_core is True
        assert profile.allow_edge is True
        assert profile.allow_attack is True

    def test_conservative_disallows_attack(self, selector):
        profile = selector.select_profile("final", "S2")
        assert profile.allow_attack is False

    def test_profile_details(self, selector):
        profile = selector.select_profile("group_round_1", "S2")
        details = selector.get_profile_details(profile)
        assert details["name"] == "balanced"
        assert "description" in details