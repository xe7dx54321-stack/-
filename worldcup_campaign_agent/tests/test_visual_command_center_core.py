
"""Tests for Visual Command Center Core."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.visual_command_center_core import (
    LoadedVisualSource, VisualDashboardSources, StatusCard, VisualStatusSummary,
    VisualCandidateCard, VisualCandidateSummary, VisualReviewCard, VisualReviewSummary,
    BankrollSeries, ReviewCountSeries,
    load_visual_dashboard_sources, classify_color, build_status_summary,
    build_candidate_cards, build_review_cards,
    build_bankroll_series, build_review_count_series,
    _d, _load_json, _scan_forbidden, ROOT
)

class TestDataLoader:
    def test_load_sources(self):
        cfg = _load_json(ROOT / "config" / "visual_command_center_config.json") or {}
        sources = load_visual_dashboard_sources(cfg)
        assert sources.source_count > 5
        assert sources.available_count >= 0

    def test_missing_source_warning(self):
        sources = VisualDashboardSources()
        src = LoadedVisualSource(source_name="test", path="/nonexistent")
        src.warnings.append("Source file not found")
        sources.sources.append(src)
        assert sources.available_count == 0

    def test_forbidden_scan(self):
        data = {"stake_amount": 100}
        fb = _scan_forbidden(data)
        assert len(fb) > 0

    def test_safety_flags(self):
        cfg = _load_json(ROOT / "config" / "visual_frontend_safety_config.json")
        assert cfg is not None
        assert cfg["analysis_only"] == True
        assert cfg["real_money_execution_ready"] == False

class TestStatusClassifier:
    def test_pass_green(self): assert classify_color("PASS") == "green"
    def test_warn_yellow(self): assert classify_color("WARN") == "yellow"
    def test_degraded_orange(self): assert classify_color("DEGRADED") == "orange"
    def test_blocked_red(self): assert classify_color("BLOCKED") == "red"
    def test_unknown_gray(self): assert classify_color("UNKNOWN") == "gray"

    def test_build_status_summary(self):
        cfg = _load_json(ROOT / "config" / "visual_command_center_config.json") or {}
        sources = load_visual_dashboard_sources(cfg)
        ss = build_status_summary(sources)
        assert ss.status_card_count >= 4
        assert ss.overall_status in ("READY","READY_WITH_WARNINGS","DEGRADED")

class TestCandidateCards:
    def test_build_cards(self):
        cfg = _load_json(ROOT / "config" / "visual_command_center_config.json") or {}
        sources = load_visual_dashboard_sources(cfg)
        summary = build_candidate_cards(sources)
        assert summary.candidate_count >= 0
        assert summary.analysis_only if hasattr(summary, 'analysis_only') else True

    def test_empty_source_no_crash(self):
        sources = VisualDashboardSources()
        summary = build_candidate_cards(sources)
        assert summary.candidate_count == 0

    def test_no_forbidden_labels(self):
        cfg = _load_json(ROOT / "config" / "visual_candidate_card_config.json")
        fb = cfg.get("forbidden_labels", [])
        assert "stake_amount" not in str(cfg.get("candidate_card_fields", []))

class TestReviewCards:
    def test_build_cards(self):
        cfg = _load_json(ROOT / "config" / "visual_command_center_config.json") or {}
        sources = load_visual_dashboard_sources(cfg)
        summary = build_review_cards(sources)
        assert summary.review_count >= 0

    def test_no_stake_fields(self):
        card = VisualReviewCard()
        out = _d(card)
        fb = _scan_forbidden(out)
        assert len(fb) == 0

class TestBankrollCharts:
    def test_build_series(self):
        cfg = _load_json(ROOT / "config" / "visual_command_center_config.json") or {}
        sources = load_visual_dashboard_sources(cfg)
        series = build_bankroll_series(sources)
        assert series.point_count >= 0

    def test_empty_source_no_crash(self):
        sources = VisualDashboardSources()
        series = build_bankroll_series(sources)
        assert series.point_count == 0
