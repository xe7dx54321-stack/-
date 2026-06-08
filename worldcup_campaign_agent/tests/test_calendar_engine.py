"""Tests for calendar engine."""

from datetime import date
from pathlib import Path

import pytest

from worldcup_campaign.calendar_engine import CalendarEngine


def _config_path(filename: str) -> str:
    return str(Path(__file__).resolve().parent.parent / "config" / filename)

def _data_path(filename: str) -> str:
    return str(Path(__file__).resolve().parent.parent / "data" / "seed" / filename)


class TestCalendarEngine:
    @pytest.fixture
    def engine(self):
        return CalendarEngine(
            policy_path=_config_path("campaign_policy.json"),
            stage_map_path=_config_path("worldcup_stage_map.json"),
            match_registry_path=_data_path("worldcup_2026_match_registry.json"),
        )

    def test_opening_day(self, engine):
        state = engine.get_state(date(2026, 6, 11))
        assert state.current_stage == "group_round_1"
        assert state.strategy_focus == "initial_positioning"
        assert state.matches_today_count == 4
        assert state.matches_remaining_count == 104

    def test_group_round_3(self, engine):
        state = engine.get_state(date(2026, 6, 24))
        assert state.current_stage == "group_round_3"
        assert state.strategy_focus == "final_group_positioning"
        assert state.matches_today_count == 6

    def test_final(self, engine):
        state = engine.get_state(date(2026, 7, 19))
        assert state.current_stage == "final"
        assert state.strategy_focus == "championship"
        assert state.matches_today_count == 1
        assert state.matches_remaining_count == 1

    def test_stage_summary_total_104(self, engine):
        state = engine.get_state(date(2026, 6, 15))
        assert state.stage_summary["total_matches_expected"] == 104

    def test_strategy_focus_not_empty(self, engine):
        state = engine.get_state(date(2026, 7, 4))
        assert state.strategy_focus != ""
        assert state.strategy_focus is not None

    def test_today_matches_match_registry(self, engine):
        state = engine.get_state(date(2026, 6, 11))
        assert len(state.today_matches) == 4
        for m in state.today_matches:
            assert "match_id" in m
            assert "home_team" in m
            assert "away_team" in m

    def test_safety_flags_present(self, engine):
        state = engine.get_state(date(2026, 6, 11))
        assert state.safety["campaign_analysis_only"] is True
        assert state.safety["real_bet_execution"] is False