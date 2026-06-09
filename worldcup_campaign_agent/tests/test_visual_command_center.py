
"""Tests for Visual Command Center main module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.visual_command_center_core import _d, _load_json, _scan_forbidden, ROOT
from worldcup_campaign.visual_command_center import (
    VisualCommandCenterSnapshot, build_visual_snapshot,
    render_visual_json, render_visual_markdown, render_static_html,
    write_visual_outputs, validate_visual_no_forbidden,
    VisualCommandCenterRunner
)

class TestVisualSnapshot:
    def test_build_snapshot(self):
        snap = build_visual_snapshot()
        assert snap.campaign_name == "worldcup_2026_high_odds_campaign"
        assert snap.local_url == "http://localhost:8501"
        assert snap.frontend_mode == "local_only"
        assert snap.status_summary is not None
        assert snap.candidate_summary is not None
        assert snap.review_summary is not None
        assert snap.bankroll_series is not None
        assert snap.analysis_only == True
        assert snap.simulation_only == True
        assert snap.not_betting_advice == True
        assert snap.real_money_execution_ready == False

    def test_local_url(self):
        snap = build_visual_snapshot()
        assert "localhost" in snap.local_url

    def test_json_render(self):
        snap = build_visual_snapshot()
        out = render_visual_json(snap)
        assert out["analysis_only"] == True
        assert out["real_money_execution_ready"] == False
        assert "status_summary" in out
        assert "candidate_summary" in out
        fb = validate_visual_no_forbidden(out)
        assert len(fb) == 0, f"Forbidden: {fb}"

    def test_markdown_render(self):
        snap = build_visual_snapshot()
        md = render_visual_markdown(snap)
        assert "Visual Command Center" in md
        assert "Status Summary" in md
        assert "Safety Boundary" in md
        forbidden_phrases = ["stake_to_match","bet_instruction","guaranteed_profit","real_bet_execution"]
        for p in forbidden_phrases:
            assert p not in md.lower()

    def test_html_render(self):
        snap = build_visual_snapshot()
        html = render_static_html(snap)
        assert "<!DOCTYPE html>" in html
        assert "ANALYSIS ONLY" in html
        assert "SIMULATION ONLY" in html
        assert "NOT BETTING ADVICE" in html
        assert "REAL MONEY: FALSE" in html
        # No forbidden UI actions
        forbidden_ui = ["Place Bet","Submit Order","Connect Wallet"]
        for fui in forbidden_ui:
            assert fui not in html
        # No real-money language
        assert "real money balance" not in html.lower()

    def test_write_outputs(self):
        snap = build_visual_snapshot()
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_visual_outputs(snap, output_dir=Path(tmp))
            assert "json" in paths
            assert "md" in paths
            assert "html" in paths
            assert Path(paths["html"]).exists()

    def test_runner(self):
        runner = VisualCommandCenterRunner()
        snap = runner.run()
        assert snap is not None
        assert snap.analysis_only == True

class TestRound26Regression:
    def test_imports_ok(self):
        import worldcup_campaign.policy
        import worldcup_campaign.daily_ops_runner
        import worldcup_campaign.human_review_workbench
        import worldcup_campaign.production_readiness_closeout
        import worldcup_campaign.pre_tournament_patch
        import worldcup_campaign.final_operational_freeze
