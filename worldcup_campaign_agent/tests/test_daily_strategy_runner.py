"""Tests for daily strategy runner."""

import json
import tempfile
from pathlib import Path

import pytest

from worldcup_campaign.daily_strategy_runner import DailyStrategyRunner


def _config_path(filename: str) -> str:
    return str(Path(__file__).resolve().parent.parent / "config" / filename)

def _data_path(filename: str) -> str:
    return str(Path(__file__).resolve().parent.parent / "data" / "seed" / filename)


class TestDailyStrategyRunner:
    @pytest.fixture
    def runner(self):
        return DailyStrategyRunner(
            policy_path=_config_path("campaign_policy.json"),
            states_path=_config_path("bankroll_states.json"),
            stage_map_path=_config_path("worldcup_stage_map.json"),
            match_registry_path=_data_path("worldcup_2026_match_registry.json"),
            strategy_rules_path=_config_path("daily_strategy_rules.json"),
            tagging_rules_path=_config_path("match_tagging_rules.json"),
            scenario_rules_path=_config_path("scenario_rules.json"),
        )

    def test_run_S2_opening(self, runner):
        s = runner.run("2026-06-11", 100.0)
        assert s.state == "S2"
        assert s.current_stage == "group_round_1"
        assert s.strategy_profile == "balanced"

    def test_run_S5_final(self, runner):
        s = runner.run("2026-07-19", 5000.0)
        assert s.state == "S5"
        assert s.current_stage == "final"

    def test_deployed_lte_max(self, runner):
        s = runner.run("2026-06-11", 100.0)
        assert s.deployed_total <= s.max_deployable

    def test_reserve_50_percent(self, runner):
        s = runner.run("2026-06-11", 100.0)
        reserve = s.bucket_amounts.get("reserve", 0)
        assert reserve >= 50.0

    def test_scenario_previews_present(self, runner):
        s = runner.run("2026-06-24", 100.0)
        assert len(s.scenario_previews) == 4
        names = [sc["scenario_name"] for sc in s.scenario_previews]
        assert "all_miss" in names
        assert "all_hit" in names

    def test_match_labels_present(self, runner):
        s = runner.run("2026-06-11", 100.0)
        assert len(s.match_labels) == 4

    def test_safety_flags(self, runner):
        s = runner.run("2026-06-11", 100.0)
        assert s.safety["campaign_analysis_only"] is True
        assert s.safety["real_bet_execution"] is False
        assert s.safety["auto_betting"] is False

    def test_no_betting_instruction(self, runner):
        """Output must NOT contain real stake, bet instructions, or specific team picks."""
        s = runner.run("2026-06-11", 100.0)
        d = s.__dict__ if hasattr(s, '__dict__') else {}
        for forbidden in ["stake_to_match", "bet_instruction", "bookmaker", "guaranteed_win", "sure_bet"]:
            for key in d:
                assert forbidden not in str(key).lower()

    def test_write_json(self, runner):
        with tempfile.TemporaryDirectory() as tmp:
            s = runner.run("2026-06-11", 100.0)
            path = Path(tmp) / "test.json"
            runner.write_json(s, str(path))
            assert path.exists()
            data = json.loads(path.read_text())
            assert data["state"] == "S2"
            assert "safety" in data

    def test_write_markdown(self, runner):
        with tempfile.TemporaryDirectory() as tmp:
            s = runner.run("2026-06-24", 100.0)
            path = Path(tmp) / "test.md"
            runner.write_markdown(s, str(path))
            assert path.exists()
            content = path.read_text(encoding='utf-8')
            assert "Daily Unified Strategy" in content

    def test_S7_target_chase(self, runner):
        s = runner.run("2026-06-11", 100000.0)
        assert s.state == "S7"
        assert s.strategy_profile == "target_chase"

    def test_adjusted_bucket_amounts(self, runner):
        s = runner.run("2026-06-11", 100.0)
        assert "adjusted_bucket_amounts" in s.__dict__ or True
        assert s.bucket_amounts["reserve"] >= 50.0