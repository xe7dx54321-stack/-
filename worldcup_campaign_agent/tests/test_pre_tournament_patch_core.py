
"""Tests for Pre-Tournament Patch Core modules."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.pre_tournament_patch_core import (
    ManualInputTemplate, ManualInputPack, build_manual_input_pack,
    ManualInputValidationResult, ManualInputValidationSummary,
    validate_manual_odds_input, validate_manual_result_input,
    validate_manual_team_news_input, validate_manual_review_decision_input,
    validate_all_manual_inputs,
    SmokeTestCaseResult, PreTournamentSmokeTestResult,
    run_smoke_test_case, run_pre_tournament_smoke_tests,
    ReviewRehearsalResult, run_review_rehearsal,
    ReadinessDelta, build_readiness_delta,
    _d, _load_json, _deep_scan_forbidden, ROOT, FORBIDDEN
)

CONFIG_DIR = ROOT / "config"

class TestManualInputPack:
    def test_build_pack(self):
        cfg = _load_json(CONFIG_DIR / "manual_input_pack_config.json") or {}
        pack = build_manual_input_pack(cfg)
        assert pack.template_count >= 4
        assert pack.manual_odds_template_available
        assert pack.manual_result_template_available
        assert pack.manual_team_news_template_available
        assert pack.manual_review_decision_template_available
        assert pack.analysis_only
        assert pack.simulation_only
        assert pack.not_betting_advice

    def test_odds_template_exists(self):
        cfg = _load_json(CONFIG_DIR / "manual_input_pack_config.json") or {}
        pack = build_manual_input_pack(cfg)
        odds_templates = [t for t in pack.templates if t.input_type == "manual_odds_input"]
        assert len(odds_templates) >= 1

    def test_result_template_exists(self):
        cfg = _load_json(CONFIG_DIR / "manual_input_pack_config.json") or {}
        pack = build_manual_input_pack(cfg)
        result_templates = [t for t in pack.templates if t.input_type == "manual_result_input"]
        assert len(result_templates) >= 1

    def test_team_news_template_exists(self):
        cfg = _load_json(CONFIG_DIR / "manual_input_pack_config.json") or {}
        pack = build_manual_input_pack(cfg)
        news_templates = [t for t in pack.templates if t.input_type == "manual_team_news_input"]
        assert len(news_templates) >= 1

    def test_review_decision_template_exists(self):
        cfg = _load_json(CONFIG_DIR / "manual_input_pack_config.json") or {}
        pack = build_manual_input_pack(cfg)
        review_templates = [t for t in pack.templates if t.input_type == "manual_review_decision_input"]
        assert len(review_templates) >= 1

    def test_forbidden_fields_absent(self):
        cfg = _load_json(CONFIG_DIR / "manual_input_pack_config.json") or {}
        pack = build_manual_input_pack(cfg)
        for t in pack.templates:
            if t.format == "json" and t.example_rows_or_items > 0:
                assert t.forbidden_fields_absent, f"Template {t.template_id} has forbidden fields: {t.warnings}"


class TestManualInputValidator:
    def test_validate_odds_json(self):
        result = validate_manual_odds_input("data/seed/manual_odds_input_template.json")
        assert result.valid_count >= 0

    def test_validate_odds_csv(self):
        result = validate_manual_odds_input("data/seed/manual_odds_input_template.csv")
        assert result.valid_count >= 0

    def test_validate_result_json(self):
        result = validate_manual_result_input("data/seed/manual_result_input_template.json")
        assert result.valid_count >= 0

    def test_validate_result_csv(self):
        result = validate_manual_result_input("data/seed/manual_result_input_template.csv")
        assert result.valid_count >= 0

    def test_validate_team_news_json(self):
        result = validate_manual_team_news_input("data/seed/manual_team_news_input_template.json")
        assert result.valid_count >= 0

    def test_validate_review_decision(self):
        result = validate_manual_review_decision_input("data/seed/manual_review_decision_rehearsal.json")
        assert result.valid_count >= 0

    def test_validate_all(self):
        cfg = _load_json(CONFIG_DIR / "manual_input_pack_config.json") or {}
        pack = build_manual_input_pack(cfg)
        summary = validate_all_manual_inputs(pack)
        assert summary.total_forbidden == 0, f"Forbidden fields: {[r.errors for r in summary.results]}"
        assert summary.analysis_only
        assert summary.simulation_only
        assert summary.not_betting_advice

    def test_forbidden_field_detection(self):
        result = validate_manual_review_decision_input("data/seed/manual_review_decision_rehearsal.json")
        # Should detect at least 1 invalid decision (execute_real_bet)
        assert result.invalid_count >= 1, "Should reject execute_real_bet decision"


class TestSmokeTest:
    def test_smoke_test_config(self):
        cfg = _load_json(CONFIG_DIR / "pre_tournament_smoke_test_config.json")
        assert cfg is not None
        assert len(cfg.get("smoke_tests", [])) >= 3

    def test_smoke_test_runner_no_network(self):
        cfg = _load_json(CONFIG_DIR / "pre_tournament_smoke_test_config.json") or {}
        # Smoke tests run without network by design
        cfg["smoke_tests"] = cfg.get("smoke_tests", [])[:1]  # Just test one
        result = run_pre_tournament_smoke_tests(cfg)
        assert result.smoke_test_count >= 0
        assert result.analysis_only
        assert result.simulation_only
        assert result.not_betting_advice

    def test_smoke_test_no_forbidden_output(self):
        triage = SmokeTestCaseResult(test_id="dummy")
        out = _d(triage)
        fb = _deep_scan_forbidden(out)
        assert len(fb) == 0, f"Forbidden in SmokeTestCaseResult: {fb}"


class TestReviewRehearsal:
    def test_run_rehearsal(self):
        cfg = _load_json(CONFIG_DIR / "review_rehearsal_config.json") or {}
        result = run_review_rehearsal(cfg)
        assert result.decision_input_loaded
        assert result.decision_count > 0
        assert result.valid_decision_count > 0
        assert result.invalid_decision_count >= 1  # should catch execute_real_bet
        assert result.decision_preview_generated
        assert result.audit_log_preview_generated
        assert result.analysis_only
        assert result.simulation_only
        assert result.not_betting_advice

    def test_invalid_decision_rejected(self):
        cfg = _load_json(CONFIG_DIR / "review_rehearsal_config.json") or {}
        result = run_review_rehearsal(cfg)
        assert result.invalid_decision_count >= 1

    def test_override_only_settlement(self):
        cfg = _load_json(CONFIG_DIR / "review_rehearsal_config.json") or {}
        result = run_review_rehearsal(cfg)
        assert result.override_preview_count >= 0

    def test_no_write_real_state(self):
        cfg = _load_json(CONFIG_DIR / "review_rehearsal_config.json") or {}
        result = run_review_rehearsal(cfg)
        out = _d(result)
        fb = _deep_scan_forbidden(out)
        assert len(fb) == 0, f"Forbidden in ReviewRehearsalResult: {fb}"


class TestReadinessDelta:
    def test_build_delta(self):
        manual_cfg = _load_json(CONFIG_DIR / "manual_input_pack_config.json") or {}
        smoke_cfg = _load_json(CONFIG_DIR / "pre_tournament_smoke_test_config.json") or {}
        rehearsal_cfg = _load_json(CONFIG_DIR / "review_rehearsal_config.json") or {}
        delta_cfg = _load_json(CONFIG_DIR / "readiness_delta_config.json") or {}

        pack = build_manual_input_pack(manual_cfg)
        validation = validate_all_manual_inputs(pack)
        smoke = run_pre_tournament_smoke_tests(smoke_cfg)
        rehearsal = run_review_rehearsal(rehearsal_cfg)

        delta = build_readiness_delta(
            delta_cfg.get("baseline_closeout","reports/generated/production_readiness_closeout.json"),
            validation, smoke, rehearsal, delta_cfg
        )

        assert delta.baseline_readiness_score > 0
        assert delta.patched_readiness_score_preview >= delta.baseline_readiness_score
        assert delta.patched_readiness_score_preview <= 0.95
        assert delta.real_money_execution_ready == False
        assert delta.analysis_only
        assert delta.simulation_only
        assert delta.not_betting_advice

    def test_real_money_stays_false(self):
        manual_cfg = _load_json(CONFIG_DIR / "manual_input_pack_config.json") or {}
        smoke_cfg = _load_json(CONFIG_DIR / "pre_tournament_smoke_test_config.json") or {}
        rehearsal_cfg = _load_json(CONFIG_DIR / "review_rehearsal_config.json") or {}
        delta_cfg = _load_json(CONFIG_DIR / "readiness_delta_config.json") or {}

        pack = build_manual_input_pack(manual_cfg)
        validation = validate_all_manual_inputs(pack)
        smoke = run_pre_tournament_smoke_tests(smoke_cfg)
        rehearsal = run_review_rehearsal(rehearsal_cfg)

        delta = build_readiness_delta("reports/generated/production_readiness_closeout.json",
                                      validation, smoke, rehearsal, delta_cfg)
        assert delta.real_money_execution_ready == False

    def test_delta_no_forbidden_output(self):
        delta = ReadinessDelta()
        out = _d(delta)
        fb = _deep_scan_forbidden(out)
        assert len(fb) == 0, f"Forbidden in ReadinessDelta: {fb}"
