
"""Tests for Final Operational Freeze main module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.final_operational_freeze_core import _d, _load_json, _deep_scan_forbidden, ROOT
from worldcup_campaign.final_operational_freeze import (
    FinalOperationalFreeze, build_final_operational_freeze,
    render_freeze_json, render_freeze_markdown, write_freeze_outputs,
    validate_freeze_no_forbidden, FinalOperationalFreezeRunner
)

class TestFinalOperationalFreeze:
    def test_build_freeze(self):
        freeze = build_final_operational_freeze()
        assert freeze.freeze_version == "v1.0"
        assert freeze.feature_freeze == True
        assert freeze.source_manifest is not None
        assert freeze.command_matrix is not None
        assert freeze.launch_checklist is not None
        assert freeze.go_no_go_gate is not None
        assert freeze.artifact_index is not None
        assert freeze.safety_boundary is not None
        assert len(freeze.operator_quickstart) > 100
        assert freeze.release_notes is not None
        assert freeze.real_money_execution_ready == False

    def test_overall_status_legal(self):
        freeze = build_final_operational_freeze()
        assert freeze.overall_freeze_status in (
            "FROZEN_ANALYSIS_SIMULATION_READY","FROZEN_WITH_WARNINGS","BLOCKED")

    def test_feature_freeze(self):
        freeze = build_final_operational_freeze()
        assert freeze.feature_freeze == True

    def test_real_money_execution_false(self):
        freeze = build_final_operational_freeze()
        assert freeze.real_money_execution_ready == False

    def test_json_render(self):
        freeze = build_final_operational_freeze()
        out = render_freeze_json(freeze)
        assert out["analysis_only"] == True
        assert out["simulation_only"] == True
        assert out["not_betting_advice"] == True
        assert out["real_money_execution_ready"] == False
        assert out["feature_freeze"] == True
        assert "go_no_go_gate" in out
        assert "launch_checklist" in out
        assert "command_matrix" in out
        assert "artifact_index" in out
        assert "safety_boundary" in out

    def test_no_forbidden_fields(self):
        freeze = build_final_operational_freeze()
        payload = render_freeze_json(freeze)
        fb = validate_freeze_no_forbidden(payload)
        assert len(fb) == 0, f"Forbidden: {fb}"

    def test_markdown_render(self):
        freeze = build_final_operational_freeze()
        md = render_freeze_markdown(freeze)
        assert "Final Operational Freeze" in md
        assert "Go / No-Go Gate" in md
        assert "Launch Checklist" in md
        assert "Command Matrix" in md
        assert "Safety Boundary" in md
        assert "Known Gaps" in md
        assert "Post-Freeze Rules" in md
        forbidden_phrases = ["stake_to_match","bet_instruction","guaranteed_profit","real_bet_execution"]
        for p in forbidden_phrases:
            assert p not in md.lower(), f"Forbidden phrase '{p}' in markdown"

    def test_write_outputs(self):
        freeze = build_final_operational_freeze()
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            paths = write_freeze_outputs(freeze, output_dir=Path(td))
            assert "freeze_json" in paths
            assert "freeze_md" in paths
            assert "go_no_go_gate" in paths
            assert "launch_checklist_md" in paths
            assert "command_matrix_md" in paths
            assert "artifact_index" in paths
            assert "safety_boundary_md" in paths
            assert "operator_quickstart_md" in paths
            assert "release_notes_md" in paths

    def test_runner(self):
        runner = FinalOperationalFreezeRunner()
        result = runner.run()
        assert result is not None
        assert result.feature_freeze == True

class TestRound25Regression:
    def test_all_key_imports(self):
        import worldcup_campaign.policy
        import worldcup_campaign.bankroll_state
        import worldcup_campaign.calendar_engine
        import worldcup_campaign.match_registry
        import worldcup_campaign.daily_strategy
        import worldcup_campaign.ev_ranking
        import worldcup_campaign.integrated_daily_strategy
        import worldcup_campaign.parlay_optimizer
        import worldcup_campaign.futures_preview_runner
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
        import worldcup_campaign.pre_tournament_patch
        import worldcup_campaign.pre_tournament_patch_core
