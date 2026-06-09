"""Tests for bucket_performance_review module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.bucket_performance_review import (
    review_bucket_performance, BucketPerformanceReview
)


class TestBucketPerformance:
    def test_generates_review(self):
        settlement = {"simulation_ledger": []}
        review = review_bucket_performance(settlement, [], {})
        assert review is not None
        assert "core" in review.bucket_breakdowns
        assert "edge" in review.bucket_breakdowns
        assert "attack" in review.bucket_breakdowns
        assert "futures" in review.bucket_breakdowns
        assert "parlay" in review.bucket_breakdowns

    def test_core_edge_attack_futures_parlay_present(self):
        settlement = {"simulation_ledger": []}
        review = review_bucket_performance(settlement)
        names = review.bucket_breakdowns.keys()
        for b in ["core", "edge", "attack", "futures", "parlay"]:
            assert b in names

    def test_pending_futures_not_realized_loss(self):
        settlement = {
            "simulation_ledger": [
                {"record_id": "f1", "bucket": "futures", "is_pending": True, "actual_outcome": None, "decimal_odds": 10.0},
                {"record_id": "f2", "bucket": "futures", "is_pending": True, "actual_outcome": None, "decimal_odds": 20.0},
            ]
        }
        review = review_bucket_performance(settlement)
        bd = review.bucket_breakdowns.get("futures", {})
        assert bd.get("realized_count", 0) == 0
        assert bd.get("pending_count", 0) == 2

    def test_attack_high_variance_warning(self):
        settlement = {"simulation_ledger": []}
        review = review_bucket_performance(settlement)
        bd = review.bucket_breakdowns.get("attack", {})
        assert len(bd.get("warnings", [])) > 0

    def test_simulated_pl_output(self):
        settlement = {
            "simulation_ledger": [
                {"record_id": "r1", "bucket": "core", "is_pending": False, "actual_outcome": 1, "decimal_odds": 2.0},
                {"record_id": "r2", "bucket": "core", "is_pending": False, "actual_outcome": 0, "decimal_odds": 2.0},
            ]
        }
        review = review_bucket_performance(settlement)
        bd = review.bucket_breakdowns.get("core", {})
        assert bd.get("simulated_pl") is not None

    def test_candidate_count_by_bucket(self):
        settlement = {
            "simulation_ledger": [
                {"record_id": "r1", "bucket": "core"},
                {"record_id": "r2", "bucket": "core"},
                {"record_id": "r3", "bucket": "edge"},
            ]
        }
        review = review_bucket_performance(settlement)
        assert review.candidate_count_by_bucket.get("core") == 2
        assert review.candidate_count_by_bucket.get("edge") == 1

    def test_no_real_money_balance(self):
        settlement = {"simulation_ledger": []}
        review = review_bucket_performance(settlement)
        d = {
            "overall_summary": review.overall_summary,
            "warnings": review.warnings,
        }
        js = json.dumps(d)
        assert "real_money_balance" not in js.lower()

    def test_no_bet_instruction(self):
        settlement = {"simulation_ledger": []}
        review = review_bucket_performance(settlement)
        d = {
            "overall_summary": review.overall_summary,
            "warnings": review.warnings,
        }
        js = json.dumps(d)
        assert "bet_instruction" not in js.lower()
