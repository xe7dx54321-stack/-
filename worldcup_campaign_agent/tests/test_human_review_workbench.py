"""Tests for Human Review Workbench."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.human_review_workbench import (
    ReviewItem, ReviewSourceResult, ReviewSourceLoader,
    ReviewItemNormalizer, ReviewItemDeduplicator,
    PriorityClassifier, DecisionValidator, DecisionValidationResult,
    AuditLogger, HumanReviewWorkbench, HumanReviewWorkbenchRunner,
    render_workbench_json, render_workbench_markdown,
    render_workbench_html, write_workbench_outputs,
    validate_workbench_no_forbidden, _d
)

ROOT = Path(__file__).resolve().parent.parent


class TestReviewItem:
    def test_create(self):
        ri = ReviewItem(item_id="test-001", source_type="settlement_review", severity="high")
        assert ri.item_id == "test-001"
        assert ri.source_type == "settlement_review"
        assert ri.severity == "high"
        assert ri.status == "open"

    def test_defaults(self):
        ri = ReviewItem()
        assert ri.status == "open"
        assert ri.severity == "medium"
        assert ri.priority == 50


class TestSourceLoader:
    def test_creates(self):
        loader = ReviewSourceLoader()
        assert loader is not None
        assert loader.gen_dir.exists()

    def test_load_all_returns_list(self):
        loader = ReviewSourceLoader()
        sources = loader.load_all_sources("2026-06-11", 100.0)
        assert len(sources) == 5
        assert all(isinstance(s, ReviewSourceResult) for s in sources)

    def test_source_names(self):
        loader = ReviewSourceLoader()
        sources = loader.load_all_sources("2026-06-11", 100.0)
        names = {s.source_name for s in sources}
        assert "watchdog_review" in names
        assert "signal_fusion_review" in names
        assert "settlement_review" in names
        assert "daily_ops_review" in names
        assert "dry_run_review" in names


class TestNormalizer:
    def test_normalize_adds_id(self):
        norm = ReviewItemNormalizer()
        items = [ReviewItem(source_type="test")]
        result = norm.normalize(items)
        assert len(result) == 1
        assert result[0].item_id != ""

    def test_normalize_preserves_data(self):
        norm = ReviewItemNormalizer()
        items = [ReviewItem(item_id="keep", severity="critical")]
        result = norm.normalize(items)
        assert result[0].item_id == "keep"
        assert result[0].severity == "critical"


class TestDeduplicator:
    def test_deduplicate_removes_dupes(self):
        dedup = ReviewItemDeduplicator()
        items = [
            ReviewItem(item_id="same", source_type="st", match_id="m1", review_reason="r1"),
            ReviewItem(item_id="same", source_type="st", match_id="m1", review_reason="r1"),
        ]
        kept, dups = dedup.deduplicate(items)
        assert len(kept) == 1
        assert dups == 1

    def test_different_not_dupes(self):
        dedup = ReviewItemDeduplicator()
        items = [
            ReviewItem(item_id="a", source_type="st", match_id="m1", review_reason="r1"),
            ReviewItem(item_id="b", source_type="st", match_id="m2", review_reason="r1"),
        ]
        kept, dups = dedup.deduplicate(items)
        assert len(kept) == 2
        assert dups == 0


class TestPriorityClassifier:
    def test_classify_sorts(self):
        pc = PriorityClassifier()
        items = [
            ReviewItem(item_id="a", source_type="settlement_review", severity="low"),
            ReviewItem(item_id="b", source_type="settlement_review", severity="critical"),
        ]
        result = pc.classify(items)
        assert result[0].item_id == "b"
        assert result[0].priority > result[1].priority

    def test_severity_affects_priority(self):
        pc = PriorityClassifier()
        c = ReviewItem(severity="critical")
        l = ReviewItem(severity="low")
        pc.classify([c, l])
        assert c.priority > l.priority


class TestDecisionValidator:
    def test_valid_confirm(self):
        dv = DecisionValidator()
        result = dv.validate({"decision_type": "confirm", "reason": "Looks good, all data matches"})
        assert result.is_valid

    def test_invalid_type(self):
        dv = DecisionValidator()
        result = dv.validate({"decision_type": "invalid_type"})
        assert not result.is_valid

    def test_override_not_settlement_fails(self):
        dv = DecisionValidator()
        result = dv.validate({"decision_type": "override_simulation_preview", "source_type": "watchdog_review", "reason": "Need to override this"})
        assert not result.is_valid

    def test_forbidden_field_in_decision(self):
        dv = DecisionValidator()
        result = dv.validate({"decision_type": "confirm", "stake_amount": 100})
        assert not result.is_valid

    def test_apply_confirm(self):
        dv = DecisionValidator()
        item = ReviewItem(item_id="t1", status="open")
        result = dv.apply_decision(item, {"decision_type": "confirm"})
        assert result.status == "resolved"

    def test_apply_reject(self):
        dv = DecisionValidator()
        item = ReviewItem(item_id="t1", status="open")
        result = dv.apply_decision(item, {"decision_type": "reject"})
        assert result.status == "rejected"


class TestAuditLogger:
    def test_log_and_read(self):
        import tempfile, os
        tmp = Path(tempfile.mkdtemp()) / "audit.jsonl"
        al = AuditLogger(str(tmp))
        item = ReviewItem(item_id="t1")
        dec = {"decision_type": "confirm", "reason": "Approved"}
        vr = DecisionValidationResult(is_valid=True)
        al.log_decision(item, dec, vr)
        entries = al.read_all()
        assert len(entries) >= 1
        assert entries[0]["item_id"] == "t1"
        assert al.append_only
        # cleanup
        tmp.unlink(missing_ok=True)
        tmp.parent.rmdir()


class TestRunner:
    def test_runner_runs(self):
        runner = HumanReviewWorkbenchRunner()
        wb = runner.run("2026-06-11", 100.0)
        assert wb.review_item_count >= 0
        assert wb.current_date == "2026-06-11"

    def test_runner_with_decisions(self):
        runner = HumanReviewWorkbenchRunner()
        decisions = [{"item_id": "nonexistent", "decision_type": "confirm", "reason": "Test decision"}]
        wb = runner.run("2026-06-11", 100.0, decisions)
        assert len(wb.decisions) == 1

    def test_runner_5000_bankroll(self):
        runner = HumanReviewWorkbenchRunner()
        wb = runner.run("2026-06-11", 5000.0)
        assert wb.current_bankroll == 5000.0

    def test_runner_source_statuses(self):
        runner = HumanReviewWorkbenchRunner()
        wb = runner.run("2026-06-11", 100.0)
        assert len(wb.source_statuses) == 5


class TestRenderer:
    def test_json(self):
        wb = HumanReviewWorkbench(current_date="2026-06-11", review_item_count=5)
        d = render_workbench_json(wb)
        assert d["current_date"] == "2026-06-11"

    def test_markdown(self):
        wb = HumanReviewWorkbench(current_date="2026-06-11", review_item_count=5)
        md = render_workbench_markdown(wb)
        assert "# Human Review Workbench" in md
        assert "Safety" in md

    def test_html(self):
        wb = HumanReviewWorkbench(current_date="2026-06-11")
        html = render_workbench_html(wb)
        assert "<!DOCTYPE html>" in html
        assert "Human Review Workbench" in html
        assert "Not Betting Advice" in html

    def test_write_outputs(self):
        wb = HumanReviewWorkbench(current_date="2026-06-11")
        wb.safety = {"analysis_only": True, "simulation_only": True, "not_betting_advice": True}
        paths = write_workbench_outputs(wb)
        assert Path(paths["json"]).exists()
        assert Path(paths["markdown"]).exists()
        assert Path(paths["html"]).exists()


class TestSafety:
    def test_no_forbidden(self):
        wb = HumanReviewWorkbench(current_date="2026-06-11")
        wb.safety = {"analysis_only": True, "simulation_only": True, "not_betting_advice": True}
        forbidden = validate_workbench_no_forbidden(wb)
        assert len(forbidden) == 0

    def test_safety_flags(self):
        runner = HumanReviewWorkbenchRunner()
        wb = runner.run("2026-06-11", 100.0)
        assert wb.analysis_only == True
        assert wb.simulation_only == True
        assert wb.not_betting_advice == True

    def test_no_stake_in_output(self):
        runner = HumanReviewWorkbenchRunner()
        wb = runner.run("2026-06-11", 100.0)
        s = json.dumps(_d(wb)).lower()
        assert "stake_to_match" not in s
        assert "bookmaker_account" not in s
        assert "real_money_balance" not in s

    def test_markdown_no_bet(self):
        wb = HumanReviewWorkbench(current_date="2026-06-11")
        md = render_workbench_markdown(wb)
        assert "bet_instruction" not in md.lower()
        assert "guaranteed_profit" not in md.lower()

    def test_html_static_only(self):
        wb = HumanReviewWorkbench(current_date="2026-06-11")
        html = render_workbench_html(wb)
        assert "<script" not in html.lower() or "src=" not in html.lower()
        assert "bet_instruction" not in html.lower()

    def test_audit_append_only(self):
        import tempfile
        tmp = Path(tempfile.mkdtemp()) / "audit.jsonl"
        al = AuditLogger(str(tmp))
        assert al.append_only
        tmp.unlink(missing_ok=True)
        tmp.parent.rmdir()
