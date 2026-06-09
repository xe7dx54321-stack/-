
"""Tests for Pre-Tournament Patch main module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.pre_tournament_patch_core import (
    build_manual_input_pack, validate_all_manual_inputs,
    run_pre_tournament_smoke_tests, run_review_rehearsal, build_readiness_delta,
    _d, _load_json, _deep_scan_forbidden, ROOT
)
from worldcup_campaign.pre_tournament_patch import (
    PreTournamentPatch, build_pre_tournament_patch,
    render_pre_tournament_patch_json, render_pre_tournament_patch_markdown,
    write_pre_tournament_patch_outputs,
    validate_no_forbidden_pre_tournament_patch_fields,
    PreTournamentPatchRunner, run_pre_tournament_patch_preview
)

CONFIG_DIR = ROOT / "config"


class TestPreTournamentPatch:
    def test_build_patch(self):
        patch = build_pre_tournament_patch({})
        assert patch.campaign_name == "worldcup_2026_high_odds_campaign"
        assert patch.patch_version == "v1.0"
        assert patch.manual_input_pack is not None
        assert patch.manual_input_validation is not None
        assert patch.smoke_test_result is not None
        assert patch.review_rehearsal_result is not None
        assert patch.readiness_delta is not None
        assert patch.patch_status in ("PASS","WARN","DEGRADED","BLOCKED","FAILED")

    def test_manual_input_pack_present(self):
        patch = build_pre_tournament_patch({})
        assert patch.manual_input_pack.template_count >= 4

    def test_manual_input_validation_present(self):
        patch = build_pre_tournament_patch({})
        val = patch.manual_input_validation
        assert val is not None

    def test_smoke_test_present(self):
        patch = build_pre_tournament_patch({})
        assert patch.smoke_test_result.smoke_test_count >= 0

    def test_review_rehearsal_present(self):
        patch = build_pre_tournament_patch({})
        assert patch.review_rehearsal_result is not None

    def test_readiness_delta_present(self):
        patch = build_pre_tournament_patch({})
        assert patch.readiness_delta is not None
        assert patch.readiness_delta.real_money_execution_ready == False

    def test_patch_status_legal(self):
        patch = build_pre_tournament_patch({})
        assert patch.patch_status in ("PASS","WARN","DEGRADED","BLOCKED","FAILED")

    def test_real_money_execution_blocked(self):
        patch = build_pre_tournament_patch({})
        assert patch.real_money_execution_ready == False
        assert patch.safety["real_money_execution_ready"] == False

    def test_no_forbidden_fields(self):
        patch = build_pre_tournament_patch({})
        payload = render_pre_tournament_patch_json(patch)
        fb = validate_no_forbidden_pre_tournament_patch_fields(payload)
        assert len(fb) == 0, f"Forbidden fields: {fb}"

    def test_json_render(self):
        patch = build_pre_tournament_patch({})
        out = render_pre_tournament_patch_json(patch)
        assert "campaign_name" in out
        assert "patch_status" in out
        assert out["analysis_only"] == True
        assert out["simulation_only"] == True
        assert out["not_betting_advice"] == True
        assert out["real_money_execution_ready"] == False
        assert "safety" in out
        # No forbidden
        fb = _deep_scan_forbidden(out)
        assert len(fb) == 0, f"Forbidden in JSON: {fb}"

    def test_markdown_render(self):
        patch = build_pre_tournament_patch({})
        md = render_pre_tournament_patch_markdown(patch)
        assert "# Pre-Tournament Patch Window" in md
        assert "Patch Summary" in md
        assert "Manual Input Pack" in md
        assert "Smoke Test" in md
        assert "Review Rehearsal" in md
        assert "Readiness Delta" in md
        assert "Remaining Gaps" in md
        assert "Safety Boundary" in md
        assert "Final Recommendation" in md
        # No forbidden language
        forbidden_phrases = ["stake_to_match","bet_instruction","guaranteed_profit","real_bet_execution"]
        for p in forbidden_phrases:
            assert p not in md.lower(), f"Forbidden phrase '{p}' in markdown"

    def test_write_outputs(self):
        patch = build_pre_tournament_patch({})
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            paths = write_pre_tournament_patch_outputs(patch, output_dir=Path(td))
            assert "patch_json" in paths
            assert "patch_md" in paths
            assert Path(paths["patch_json"]).exists()
            assert Path(paths["patch_md"]).exists()


class TestPreTournamentPatchRunner:
    def test_runner(self):
        runner = PreTournamentPatchRunner(config_dir=str(CONFIG_DIR))
        result = runner.run()
        assert result is not None
        assert result.patch_status in ("PASS","WARN","DEGRADED","BLOCKED","FAILED")

    def test_preview_function(self):
        result = run_pre_tournament_patch_preview()
        assert result is not None
        assert result.analysis_only
        assert result.simulation_only
        assert result.not_betting_advice
        assert result.real_money_execution_ready == False


class TestRound24Regression:
    """Ensure Round 1-23b regressions remain available."""
    def test_imports_ok(self):
        import worldcup_campaign.policy
        import worldcup_campaign.bankroll_state
        import worldcup_campaign.calendar_engine
        import worldcup_campaign.match_registry
        import worldcup_campaign.daily_strategy
        import worldcup_campaign.match_probability_runner
        import worldcup_campaign.ev_ranking
        import worldcup_campaign.integrated_daily_strategy
        import worldcup_campaign.parlay_optimizer
        import worldcup_campaign.futures_preview_runner
        import worldcup_campaign.schedule_runner
        import worldcup_campaign.postmatch_settlement_runner
        import worldcup_campaign.dashboard_runner
        import worldcup_campaign.calibration_runner
        import worldcup_campaign.market_odds_runner
        import worldcup_campaign.polymarket_runner
        import worldcup_campaign.market_expectation_runner
        import worldcup_campaign.team_news_runner
        import worldcup_campaign.signal_fusion_runner
        import worldcup_campaign.daily_ops_watchdog
        import worldcup_campaign.daily_ops_runner
        import worldcup_campaign.real_data_runner
        import worldcup_campaign.full_campaign_dry_run
        import worldcup_campaign.human_review_workbench
        import worldcup_campaign.production_readiness_closeout
