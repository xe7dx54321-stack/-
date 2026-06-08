"""Tests for opportunity window calculator."""

from datetime import date
from pathlib import Path

import pytest

from worldcup_campaign.match_registry import load_match_registry
from worldcup_campaign.opportunity_window import (
    count_effective_windows,
    count_remaining_matches,
    get_remaining_matches_by_stage,
)


def _data_path(filename: str) -> str:
    return str(
        Path(__file__).resolve().parent.parent / "data" / "seed" / filename
    )


class TestCountEffectiveWindows:
    @pytest.fixture
    def matches(self):
        return load_match_registry(_data_path("worldcup_2026_match_registry.json"))

    def test_opening_day_windows_gt_1(self, matches):
        w = count_effective_windows(date(2026, 6, 11), matches)
        assert w > 1

    def test_final_day_windows_1(self, matches):
        w = count_effective_windows(date(2026, 7, 19), matches)
        assert w == 1

    def test_post_tournament_windows_0(self, matches):
        w = count_effective_windows(date(2026, 7, 20), matches)
        assert w == 0

    def test_windows_not_negative(self, matches):
        for d in [date(2026, 6, 11), date(2026, 7, 1), date(2026, 7, 19), date(2026, 7, 20)]:
            w = count_effective_windows(d, matches)
            assert w >= 0, f"Windows at {d} was {w}"

    def test_windows_consistent_with_remaining(self, matches):
        """If matches remaining > 0, windows should be >= 1."""
        for d in [date(2026, 6, 11), date(2026, 6, 24), date(2026, 7, 4), date(2026, 7, 14)]:
            remaining = count_remaining_matches(d, matches)
            windows = count_effective_windows(d, matches)
            if remaining > 0:
                assert windows >= 1, (
                    f"Date {d}: remaining={remaining} but windows={windows}"
                )


class TestCountRemainingMatches:
    @pytest.fixture
    def matches(self):
        return load_match_registry(_data_path("worldcup_2026_match_registry.json"))

    def test_opening_day_104(self, matches):
        assert count_remaining_matches(date(2026, 6, 11), matches) == 104

    def test_mid_group_stage(self, matches):
        remaining = count_remaining_matches(date(2026, 6, 20), matches)
        assert 60 < remaining < 104

    def test_final_day_1(self, matches):
        assert count_remaining_matches(date(2026, 7, 19), matches) == 1

    def test_post_tournament_0(self, matches):
        assert count_remaining_matches(date(2026, 7, 20), matches) == 0


class TestRemainingByStage:
    @pytest.fixture
    def matches(self):
        return load_match_registry(_data_path("worldcup_2026_match_registry.json"))

    def test_opening_day_all_stages_present(self, matches):
        by_stage = get_remaining_matches_by_stage(date(2026, 6, 11), matches)
        total = sum(by_stage.values())
        assert total == 104