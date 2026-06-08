"""Tests for strategy allocator."""

from pathlib import Path

import pytest

from worldcup_campaign.strategy_profile import StrategyProfileSelector
from worldcup_campaign.strategy_allocator import StrategyAllocator
from worldcup_campaign.match_strategy_labeler import MatchStrategyLabeler
from worldcup_campaign.match_registry import load_match_registry, get_matches_by_date
from datetime import date


def _config_path(filename: str) -> str:
    return str(Path(__file__).resolve().parent.parent / "config" / filename)

def _data_path(filename: str) -> str:
    return str(Path(__file__).resolve().parent.parent / "data" / "seed" / filename)


class TestStrategyAllocator:
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

    def test_allocate_S2_opening(self, allocator, selector, labeler, matches):
        profile = selector.select_profile("group_round_1", "S2")
        today = date(2026, 6, 11)
        today_ms = get_matches_by_date(today, matches)
        labeled = labeler.label_matches(today_ms, today)
        
        buckets = {"reserve": 50.0, "core": 10.0, "edge": 15.0, "attack": 20.0, "futures": 5.0}
        plan = allocator.allocate(buckets, profile, labeled)
        
        assert plan.total_reserve == 50.0
        assert plan.total_deployed <= 50.0

    def test_allocate_S5_conservative(self, allocator, selector, labeler, matches):
        profile = selector.select_profile("group_round_1", "S5")
        assert profile.name in ("conservative", "balanced")
        today = date(2026, 6, 11)
        today_ms = get_matches_by_date(today, matches)
        labeled = labeler.label_matches(today_ms, today)
        
        buckets = {"reserve": 2500.0, "core": 1250.0, "edge": 750.0, "attack": 250.0, "futures": 250.0}
        plan = allocator.allocate(buckets, profile, labeled)
        
        # Conservative should not deploy attack
        attack_buckets = [b for b in plan.buckets if b.bucket == "attack"]
        if attack_buckets and not profile.allow_attack:
            assert attack_buckets[0].is_active is False

    def test_eligible_match_count(self, allocator, selector, labeler, matches):
        profile = selector.select_profile("group_round_1", "S2")
        today = date(2026, 6, 11)
        today_ms = get_matches_by_date(today, matches)
        labeled = labeler.label_matches(today_ms, today)
        
        buckets = {"reserve": 50.0, "core": 10.0, "edge": 15.0, "attack": 20.0, "futures": 5.0}
        plan = allocator.allocate(buckets, profile, labeled)
        
        for b in plan.buckets:
            assert b.eligible_match_count >= 0