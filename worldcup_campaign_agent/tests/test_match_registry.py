"""Tests for match registry."""

from datetime import date
from pathlib import Path

import pytest

from worldcup_campaign.match_registry import (
    load_match_registry,
    validate_match_registry,
    get_matches_by_date,
    get_matches_by_stage,
    get_matches_by_group,
    get_upcoming_matches,
    get_remaining_matches,
    get_match_count_by_stage,
    MatchEntry,
)


def _data_path(filename: str) -> str:
    return str(
        Path(__file__).resolve().parent.parent / "data" / "seed" / filename
    )


class TestLoadMatchRegistry:
    @pytest.fixture
    def matches(self):
        return load_match_registry(_data_path("worldcup_2026_match_registry.json"))

    def test_total_104(self, matches):
        assert len(matches) == 104

    def test_match_numbers_contiguous(self, matches):
        nums = sorted([m.match_number for m in matches])
        assert nums == list(range(1, 105))

    def test_match_ids_unique(self, matches):
        ids = [m.match_id for m in matches]
        assert len(ids) == len(set(ids))

    def test_group_stage_72(self, matches):
        group = [m for m in matches if not m.is_knockout]
        assert len(group) == 72

    def test_knockout_32(self, matches):
        ko = [m for m in matches if m.is_knockout]
        assert len(ko) == 32

    def test_per_stage_counts(self, matches):
        counts = get_match_count_by_stage(matches)
        assert counts["group_round_1"] == 24
        assert counts["group_round_2"] == 24
        assert counts["group_round_3"] == 24
        assert counts["round_of_32"] == 16
        assert counts["round_of_16"] == 8
        assert counts["quarter_final"] == 4
        assert counts["semi_final"] == 2
        assert counts["third_place"] == 1
        assert counts["final"] == 1

    def test_group_matches_have_group(self, matches):
        for m in matches:
            if not m.is_knockout:
                assert m.group is not None, f"Match {m.match_id} has no group"

    def test_knockout_matches_no_group(self, matches):
        for m in matches:
            if m.is_knockout:
                assert m.group is None, f"Match {m.match_id} should not have group"

    def test_dates_in_stage_range(self, matches):
        # Check a few key dates
        for m in matches:
            if m.stage == "group_round_1":
                assert date(2026, 6, 11) <= m.date <= date(2026, 6, 17)
            elif m.stage == "final":
                assert m.date == date(2026, 7, 19)


class TestQueryMatches:
    @pytest.fixture
    def matches(self):
        return load_match_registry(_data_path("worldcup_2026_match_registry.json"))

    def test_get_by_date_group_stage(self, matches):
        result = get_matches_by_date(date(2026, 6, 11), matches)
        assert len(result) == 4

    def test_get_by_date_final(self, matches):
        result = get_matches_by_date(date(2026, 7, 19), matches)
        assert len(result) == 1
        assert result[0].is_knockout is True

    def test_get_by_stage(self, matches):
        result = get_matches_by_stage("quarter_final", matches)
        assert len(result) == 4

    def test_get_by_group(self, matches):
        result = get_matches_by_group("GROUP_A", matches)
        assert len(result) == 6  # 2 per round × 3 rounds = 6

    def test_upcoming_matches(self, matches):
        result = get_upcoming_matches(date(2026, 6, 11), matches, limit=10)
        assert len(result) == 10
        assert all(m.date >= date(2026, 6, 11) for m in result)

    def test_remaining_matches_opening(self, matches):
        result = get_remaining_matches(date(2026, 6, 11), matches)
        assert len(result) == 104

    def test_remaining_matches_final(self, matches):
        result = get_remaining_matches(date(2026, 7, 19), matches)
        assert len(result) == 1

    def test_remaining_matches_post(self, matches):
        result = get_remaining_matches(date(2026, 7, 20), matches)
        assert len(result) == 0