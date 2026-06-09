"""Tests for schedule_runner module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.schedule_runner import ScheduleRunner

ROOT = Path(__file__).resolve().parent.parent

def get_paths():
    return {
        "schedule_config": str(ROOT / "config" / "campaign_schedule_config.json"),
        "stage_map": str(ROOT / "config" / "worldcup_stage_map.json"),
        "execution_rules": str(ROOT / "config" / "daily_execution_rules.json"),
        "match_registry": str(ROOT / "data" / "seed" / "worldcup_2026_match_registry.json"),
    }

class TestSingleDay:
    def test_2026_06_11(self):
        runner = ScheduleRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert preview.day_count == 50
        assert preview.matchday_count > 0

    def test_2026_06_24(self):
        runner = ScheduleRunner(get_paths())
        preview = runner.run("2026-06-24", 100.0)
        assert preview.today_schedule["date"] == "2026-06-24"

    def test_2026_07_19(self):
        runner = ScheduleRunner(get_paths())
        preview = runner.run("2026-07-19", 100.0)
        assert preview.today_schedule["date"] == "2026-07-19"

    def test_bankroll_5000(self):
        runner = ScheduleRunner(get_paths())
        preview = runner.run("2026-06-11", 5000.0)
        assert preview.day_count == 50

    def test_path_sanity_warning(self):
        runner = ScheduleRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0, winner_prob_sum=0.63)
        assert len(preview.path_sanity_warnings) > 0

class TestFullTimeline:
    def test_50_days(self):
        runner = ScheduleRunner(get_paths())
        timeline = runner.run_full_timeline(100.0)
        assert len(timeline) == 50

    def test_has_matchdays(self):
        runner = ScheduleRunner(get_paths())
        timeline = runner.run_full_timeline(100.0)
        matchdays = [d for d in timeline if d["is_matchday"]]
        assert len(matchdays) >= 25

    def test_stages_present(self):
        runner = ScheduleRunner(get_paths())
        timeline = runner.run_full_timeline(100.0)
        stages = set(d["stage"] for d in timeline)
        assert len(stages) > 3

class TestSafety:
    def test_safety_flags(self):
        runner = ScheduleRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        s = preview.safety
        assert s["campaign_analysis_only"] is True
        assert s["real_bet_execution"] is False
        assert s["not_betting_advice"] is True

    def test_no_stake_fields(self):
        runner = ScheduleRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        from dataclasses import asdict
        d = asdict(preview)
        jstr = json.dumps(d, default=str)
        assert "stake_to_match" not in jstr
        assert "stake_amount" not in jstr
        assert "bet_instruction" not in jstr
        assert "bookmaker" not in jstr.lower()

    def test_operator_checklist_present(self):
        runner = ScheduleRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert len(preview.operator_checklist) > 0

class TestReports:
    def test_write_json(self):
        runner = ScheduleRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        out = str(ROOT / "reports" / "generated" / "schedule_test.json")
        runner.write_json(preview, out)
        assert Path(out).exists()
        data = json.loads(Path(out).read_text(encoding="utf-8"))
        assert "day_count" in data

    def test_write_markdown(self):
        runner = ScheduleRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        out = str(ROOT / "reports" / "generated" / "schedule_test.md")
        runner.write_markdown(preview, out)
        assert Path(out).exists()
        content = Path(out).read_text(encoding="utf-8")
        assert "Campaign Schedule" in content
