"""Tests for Daily Ops Runner."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.daily_ops_core import (
    build_daily_ops_step, validate_step_command, parse_step_stdout,
    create_daily_ops_manifest, summarize_manifest,
    build_final_daily_package, build_operator_checklist,
    DailyOpsStep, DailyOpsManifest, FinalDailyPackage, _d
)
from worldcup_campaign.daily_ops_runner import DailyOpsRunner

ROOT = Path(__file__).resolve().parent.parent


class TestStep:
    def test_build_step(self):
        sc = {"step_id": "test", "runner": "run_calendar_preview.py", "required": True, "phase": "test"}
        s = build_daily_ops_step(sc, "2026-06-11", 100.0)
        assert s.step_id == "test"
        assert "--date" in s.command
        assert "--json" in s.command

    def test_validate_clean(self):
        sc = {"step_id": "t", "runner": "run_calendar_preview.py", "required": True}
        s = build_daily_ops_step(sc, "2026-06-11", 100.0)
        v = validate_step_command(s)
        assert len(v) == 0

    def test_validate_forbidden(self):
        sc = {"step_id": "t", "runner": "run_calendar_preview.py", "required": True}
        s = build_daily_ops_step(sc, "2026-06-11", 100.0)
        s.command.append("--submit_order")
        v = validate_step_command(s)
        assert len(v) >= 1

    def test_parse_json(self):
        d = parse_step_stdout('{"key": "val"}')
        assert d.get("key") == "val"

class TestManifest:
    def test_create(self):
        pc = {"pipeline_name": "test", "steps": [
            {"step_id": "s1", "runner": "t.py", "required": True},
            {"step_id": "s2", "runner": "t.py", "required": False}
        ]}
        m = create_daily_ops_manifest("2026-06-11", 100.0, pc)
        assert m.step_count == 2
        assert m.required_step_count == 1

    def test_summarize(self):
        m = DailyOpsManifest(current_date="2026-06-11")
        m.steps = [
            DailyOpsStep(step_id="s1", status="SUCCESS", required=True),
            DailyOpsStep(step_id="s2", status="WARN", required=False),
        ]
        s = summarize_manifest(m)
        assert s.success_count == 1
        assert s.warn_count == 1


class TestPackage:
    def test_build_review_required(self):
        m = DailyOpsManifest(current_date="2026-06-11")
        fake = type('x', (), {'blocked_from_strategy_upgrade': True, 'pipeline_blocked': False, 'watchdog_post_passed': True})()
        wd = {"circuit_breaker": {"overall_status": "WARN"}, "review_queue": {"review_item_count": 5}}
        p = build_final_daily_package("2026-06-11", 100.0, m, fake, {}, wd)
        assert p.package_type == "review_required_package"

    def test_no_forbidden(self):
        m = DailyOpsManifest(current_date="2026-06-11")
        fake = type('x', (), {'blocked_from_strategy_upgrade': False, 'pipeline_blocked': False, 'watchdog_post_passed': True})()
        wd = {"circuit_breaker": {"overall_status": "PASS"}, "review_queue": {}}
        p = build_final_daily_package("2026-06-11", 100.0, m, fake, {}, wd)
        js = json.dumps(_d(p))
        for fb in ["stake", "bet_instruction", "bookmaker_account", "real_money_balance"]:
            assert fb not in js


class TestChecklist:
    def test_build(self):
        cc = {"checklist_items": ["confirm_watchdog_status"], "forbidden_operator_actions": ["place_bet"]}
        m = DailyOpsManifest(current_date="2026-06-11")
        wd = {"circuit_breaker": {"overall_status": "WARN"}, "review_queue": {}}
        cl = build_operator_checklist(wd, m, cc)
        assert len(cl["items"]) >= 1
        assert "place_bet" in cl["forbidden_actions"]


class TestRunner:
    def test_dry_run_2026_06_11(self):
        r = DailyOpsRunner()
        result = r.run("2026-06-11", 100.0, "dry_run")
        assert result.current_date == "2026-06-11"
        assert result.overall_status == "DRY_RUN"

    def test_dry_run_2026_06_24(self):
        r = DailyOpsRunner()
        result = r.run("2026-06-24", 100.0, "dry_run")
        assert result.current_date == "2026-06-24"

    def test_dry_run_2026_07_19(self):
        r = DailyOpsRunner()
        result = r.run("2026-07-19", 100.0, "dry_run")
        assert result.current_date == "2026-07-19"

    def test_bankroll_5000(self):
        r = DailyOpsRunner()
        result = r.run("2026-06-11", 5000.0, "dry_run")
        assert result.current_bankroll == 5000.0

    def test_watchdog_only(self):
        r = DailyOpsRunner()
        result = r.run("2026-06-11", 100.0, "watchdog_only")
        assert result.mode == "watchdog_only"

    def test_manifest_output(self):
        r = DailyOpsRunner()
        result = r.run("2026-06-11", 100.0, "dry_run")
        assert "steps" in result.manifest
        assert len(result.manifest["steps"]) >= 1

    def test_generates_json(self):
        r = DailyOpsRunner()
        r.run("2026-06-11", 100.0, "dry_run")
        assert (ROOT / "reports" / "generated" / "daily_ops_run.json").exists()

    def test_generates_md(self):
        r = DailyOpsRunner()
        r.run("2026-06-11", 100.0, "dry_run")
        assert (ROOT / "reports" / "generated" / "daily_ops_run.md").exists()

    def test_generates_package(self):
        r = DailyOpsRunner()
        r.run("2026-06-11", 100.0, "dry_run")
        assert (ROOT / "reports" / "generated" / "final_daily_package.json").exists()

    def test_generates_checklist(self):
        r = DailyOpsRunner()
        r.run("2026-06-11", 100.0, "dry_run")
        assert (ROOT / "reports" / "generated" / "operator_checklist.json").exists()

    def test_no_stake(self):
        r = DailyOpsRunner()
        result = r.run("2026-06-11", 100.0, "dry_run")
        js = json.dumps(_d(result))
        for fb in ["stake_to_match", "stake_amount", "bet_instruction",
                    "bookmaker_account", "wallet_address", "private_key",
                    "real_money_balance", "guaranteed_profit"]:
            assert fb not in js

    def test_not_betting(self):
        r = DailyOpsRunner()
        result = r.run("2026-06-11", 100.0, "dry_run")
        assert result.not_betting_advice is True
        assert result.analysis_only is True
        assert result.simulation_only is True

    def test_package_is_review_required(self):
        r = DailyOpsRunner()
        result = r.run("2026-06-11", 100.0, "dry_run")
        pkg = result.final_daily_package
        assert pkg.get("package_type") in ("review_required_package", "clean_final_package", "blocked_package")
