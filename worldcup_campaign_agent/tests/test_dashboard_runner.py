"""Tests for dashboard_runner module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.dashboard_runner import DashboardRunner

ROOT = Path(__file__).resolve().parent.parent

def get_paths():
    return {
        "dashboard_config": str(ROOT / "config" / "dashboard_config.json"),
        "daily_brief_config": str(ROOT / "config" / "daily_brief_config.json"),
        "section_policy": str(ROOT / "config" / "dashboard_section_policy.json"),
    }

class TestRunner:
    def test_2026_06_11(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert preview.current_date == "2026-06-11"

    def test_2026_06_24(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-24", 100.0)
        assert preview.current_date == "2026-06-24"

    def test_2026_07_19(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-07-19", 100.0)
        assert preview.current_date == "2026-07-19"

    def test_bankroll_5000(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-11", 5000.0)
        assert preview.current_bankroll == 5000.0

    def test_mode_postmatch(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0, "postmatch")
        assert preview.dashboard_mode == "postmatch"

    def test_mode_full(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0, "full")
        assert preview.dashboard_mode == "full"

    def test_dashboard_present(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert "bankroll_summary" in preview.dashboard

    def test_daily_brief_present(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert "boss_summary" in preview.daily_brief

    def test_source_status(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert len(preview.source_status) > 0

    def test_generated_files(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        od = ROOT / "reports" / "generated"
        assert (od / "campaign_dashboard.json").exists()
        assert (od / "daily_brief.md").exists()
        assert (od / "campaign_dashboard.html").exists()

class TestSafety:
    def test_no_stake_to_match(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        from dataclasses import asdict
        jstr = json.dumps(asdict(preview), default=str)
        assert "stake_to_match" not in jstr

    def test_no_stake_amount(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        from dataclasses import asdict
        jstr = json.dumps(asdict(preview), default=str)
        assert "stake_amount" not in jstr

    def test_no_bet_instruction(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        from dataclasses import asdict
        jstr = json.dumps(asdict(preview), default=str)
        assert "bet_instruction" not in jstr

    def test_no_bookmaker_account(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        from dataclasses import asdict
        jstr = json.dumps(asdict(preview), default=str)
        assert "bookmaker_account" not in jstr

    def test_no_real_money_balance(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        from dataclasses import asdict
        jstr = json.dumps(asdict(preview), default=str)
        assert "real_money_balance" not in jstr

    def test_not_betting_advice(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert preview.not_betting_advice is True
        assert preview.simulation_only is True

    def test_safety_flags(self):
        runner = DashboardRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        s = preview.safety
        assert s["campaign_analysis_only"] is True
        assert s["no_real_money"] is True
