"""Tests for Production Readiness Closeout."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.production_readiness_closeout import (
    ProductionReadinessCloseoutRunner, ProductionReadinessCloseout,
    CapabilityMap, Scorecard, SourceEnablementPlan, GapRegister,
    PreTournamentChecklist, render_closeout_json, render_closeout_markdown,
    write_closeout_outputs, validate_closeout_no_forbidden, _d
)

ROOT = Path(__file__).resolve().parent.parent


class TestRunner:
    def test_runner_creates_result(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        assert result.overall_status != ""
        assert result.readiness_score >= 0
        assert result.real_money_execution_ready == False

    def test_capability_map_exists(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        assert result.capability_map is not None
        assert result.capability_map.capability_count == 23
        assert result.capability_map.ready_count >= 20

    def test_scorecard_exists(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        assert result.scorecard is not None
        assert result.scorecard.domain_count == 20
        assert result.scorecard.ready_domain_count >= 15

    def test_source_plan_exists(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        assert result.source_enablement_plan is not None
        assert result.source_enablement_plan.source_category_count == 9
        assert result.source_enablement_plan.not_allowed_count >= 2

    def test_gap_register_exists(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        assert result.gap_register is not None
        assert result.gap_register.gap_count >= 5
        assert result.gap_register.high_gap_count >= 1

    def test_checklist_exists(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        assert result.pre_tournament_checklist is not None
        assert result.pre_tournament_checklist.checklist_count == 10
        assert result.pre_tournament_checklist.pending_count == 10

    def test_runbook_generated(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        assert len(result.operator_runbook) > 500
        assert "Daily Setup" in result.operator_runbook
        assert "Safety Boundary" in result.operator_runbook

    def test_dry_run_summary_loaded(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        assert isinstance(result.dry_run_summary, dict)

    def test_workbench_summary_loaded(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        assert isinstance(result.workbench_summary, dict)


class TestRenderer:
    def test_json(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        d = render_closeout_json(result)
        assert d["overall_status"] != ""
        assert d["real_money_execution_ready"] == False

    def test_markdown(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        md = render_closeout_markdown(result)
        assert "# Production Readiness Closeout Report" in md
        assert "Safety Boundary" in md

    def test_write_outputs(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        paths = write_closeout_outputs(result)
        assert Path(paths["json"]).exists()
        assert Path(paths["markdown"]).exists()
        assert Path(paths["runbook"]).exists()


class TestSafety:
    def test_no_forbidden(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        forbidden = validate_closeout_no_forbidden(result)
        assert len(forbidden) == 0, f"Forbidden: {forbidden}"

    def test_safety_flags(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        assert result.analysis_only == True
        assert result.simulation_only == True
        assert result.not_betting_advice == True
        assert result.safety["real_bet_execution"] == False
        assert result.safety["auto_betting"] == False
        assert result.real_money_execution_ready == False

    def test_no_stake_in_output(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        # Only check core data, not config metadata that references these terms as categories
        check_keys = ["scorecard","capability_map","gap_register","pre_tournament_checklist","dry_run_summary","workbench_summary","safety"]
        d = _d(result)
        s = json.dumps({k:d.get(k) for k in check_keys if k in d}).lower()
        assert "stake_to_match" not in s
        assert "real_money_balance" not in s

    def test_markdown_no_bet(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        md = render_closeout_markdown(result)
        assert "bet_instruction" not in md.lower()
        assert "guaranteed_profit" not in md.lower()

    def test_readiness_levels(self):
        runner = ProductionReadinessCloseoutRunner()
        result = runner.run()
        assert result.readiness_level in ("HIGH_READINESS","MODERATE_READINESS","LOW_READINESS","NOT_READY")
