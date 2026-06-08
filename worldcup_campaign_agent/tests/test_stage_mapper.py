"""Tests for stage mapper."""

from datetime import date
from pathlib import Path

import pytest

from worldcup_campaign.stage_mapper import (
    load_stage_map,
    validate_stage_map,
    classify_date,
    get_stages_summary,
    StageDefinition,
)


def _config_path(filename: str) -> str:
    return str(Path(__file__).resolve().parent.parent / "config" / filename)


class TestLoadStageMap:
    def test_load_valid(self):
        stages = load_stage_map(_config_path("worldcup_stage_map.json"))
        assert len(stages) == 11

    def test_stages_unique(self):
        stages = load_stage_map(_config_path("worldcup_stage_map.json"))
        names = [s.stage for s in stages]
        assert len(names) == len(set(names))

    def test_stage_orders_unique(self):
        stages = load_stage_map(_config_path("worldcup_stage_map.json"))
        orders = [s.stage_order for s in stages]
        assert len(orders) == len(set(orders))

    def test_total_matches_104(self):
        stages = load_stage_map(_config_path("worldcup_stage_map.json"))
        total = sum(s.match_count_expected for s in stages)
        assert total == 104


class TestClassifyDate:
    @pytest.fixture
    def stages(self):
        return load_stage_map(_config_path("worldcup_stage_map.json"))

    def test_pre_tournament(self, stages):
        s = classify_date(date(2026, 6, 10), stages)
        assert s.stage == "pre_tournament"

    def test_group_round_1(self, stages):
        s = classify_date(date(2026, 6, 11), stages)
        assert s.stage == "group_round_1"

    def test_group_round_2(self, stages):
        s = classify_date(date(2026, 6, 18), stages)
        assert s.stage == "group_round_2"

    def test_group_round_3(self, stages):
        s = classify_date(date(2026, 6, 24), stages)
        assert s.stage == "group_round_3"

    def test_round_of_32(self, stages):
        s = classify_date(date(2026, 6, 28), stages)
        assert s.stage == "round_of_32"

    def test_round_of_16(self, stages):
        s = classify_date(date(2026, 7, 4), stages)
        assert s.stage == "round_of_16"

    def test_quarter_final(self, stages):
        s = classify_date(date(2026, 7, 9), stages)
        assert s.stage == "quarter_final"

    def test_semi_final(self, stages):
        s = classify_date(date(2026, 7, 14), stages)
        assert s.stage == "semi_final"

    def test_third_place(self, stages):
        s = classify_date(date(2026, 7, 18), stages)
        assert s.stage == "third_place"

    def test_final(self, stages):
        s = classify_date(date(2026, 7, 19), stages)
        assert s.stage == "final"

    def test_post_tournament(self, stages):
        s = classify_date(date(2026, 7, 20), stages)
        assert s.stage == "post_tournament"

    def test_out_of_range_fails(self, stages):
        with pytest.raises(ValueError):
            classify_date(date(2020, 1, 1), stages)


class TestStageSummary:
    def test_summary(self):
        stages = load_stage_map(_config_path("worldcup_stage_map.json"))
        summary = get_stages_summary(stages)
        assert summary["total_stages"] == 11
        assert summary["total_matches_expected"] == 104
        assert len(summary["stages"]) == 11