"""Tests for calendar runner."""

import json
import tempfile
from pathlib import Path

import pytest

from worldcup_campaign.calendar_runner import CalendarRunner


def _config_path(filename: str) -> str:
    return str(Path(__file__).resolve().parent.parent / "config" / filename)

def _data_path(filename: str) -> str:
    return str(Path(__file__).resolve().parent.parent / "data" / "seed" / filename)


class TestCalendarRunner:
    @pytest.fixture
    def runner(self):
        return CalendarRunner(
            policy_path=_config_path("campaign_policy.json"),
            stage_map_path=_config_path("worldcup_stage_map.json"),
            match_registry_path=_data_path("worldcup_2026_match_registry.json"),
        )

    def test_runner_executes(self, runner):
        state = runner.run("2026-06-11")
        assert state.current_date == "2026-06-11"
        assert state.current_stage == "group_round_1"

    def test_runner_three_dates(self, runner):
        for dt in ["2026-06-11", "2026-06-24", "2026-07-19"]:
            state = runner.run(dt)
            assert state.current_date == dt

    def test_write_json_report(self, runner):
        with tempfile.TemporaryDirectory() as tmp:
            state = runner.run("2026-06-11")
            path = Path(tmp) / "report.json"
            runner.write_json_report(state, str(path))
            assert path.exists()
            data = json.loads(path.read_text())
            assert data["current_stage"] == "group_round_1"
            assert "matches_today_count" in data
            assert "safety" in data

    def test_write_markdown_report(self, runner):
        with tempfile.TemporaryDirectory() as tmp:
            state = runner.run("2026-07-19")
            path = Path(tmp) / "report.md"
            runner.write_markdown_report(state, str(path))
            assert path.exists()
            content = path.read_text()
            assert "Calendar Preview" in content
            assert "final" in content

    def test_safety_flags_in_report(self, runner):
        state = runner.run("2026-06-24")
        assert state.safety["campaign_analysis_only"] is True
        assert state.safety["real_bet_execution"] is False
        assert state.safety["auto_betting"] is False

    def test_no_odds_or_stake_in_state(self, runner):
        """Calendar runner should NOT contain odds/stake/bet execution fields."""
        state = runner.run("2026-06-11")
        d = state.__dict__ if hasattr(state, '__dict__') else {}
        # These fields should not exist at calendar level
        for forbidden in ["odds", "stake", "bet", "wager", "execution"]:
            for key in d:
                assert forbidden not in str(key).lower(), (
                    f"Forbidden field '{forbidden}' found in {key}"
                )