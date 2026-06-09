"""Tests for futures_performance_review module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.futures_performance_review import (
    review_futures_performance, FuturesPerformanceReview
)


class TestFuturesPerformance:
    def test_generates_review(self):
        preview = {"futures_candidate_count": 30, "futures_bucket_count": 12, "attack_longshot_count": 8}
        review = review_futures_performance(preview)
        assert review.futures_candidate_count == 30
        assert review.futures_bucket_count == 12

    def test_pending_futures_not_miss(self):
        preview = {"futures_candidate_count": 5}
        settlement = {
            "simulation_ledger": [
                {"record_id": "f1", "source_type": "futures", "is_pending": True, "actual_outcome": None},
                {"record_id": "f2", "source_type": "futures", "is_pending": True, "actual_outcome": None},
            ]
        }
        review = review_futures_performance(preview, settlement)
        assert review.pending_futures_count == 2
        assert review.settled_futures_count == 0

    def test_winner_probability_sum_warning(self):
        preview = {"futures_candidate_count": 10, "winner_probability_sum_warning": "Sum exceeds 1.0; synthetic proxy model bias"}
        review = review_futures_performance(preview)
        assert len(review.winner_probability_sum_warning) > 0

    def test_golden_boot_deferred_warning(self):
        preview = {"futures_candidate_count": 10}
        review = review_futures_performance(preview)
        assert any("golden" in w.lower() for w in review.warnings)

    def test_performance_by_market_type(self):
        preview = {"futures_candidate_count": 5}
        settlement = {
            "simulation_ledger": [
                {"record_id": "f1", "source_type": "futures", "market_type": "winner", "is_pending": True},
                {"record_id": "f2", "source_type": "futures", "market_type": "winner", "is_pending": False, "actual_outcome": 1},
            ]
        }
        review = review_futures_performance(preview, settlement)
        assert "winner" in review.performance_by_market_type

    def test_no_stake_output(self):
        preview = {"futures_candidate_count": 10}
        review = review_futures_performance(preview)
        d = {
            "futures_candidate_count": review.futures_candidate_count,
            "warnings": review.warnings,
        }
        js = json.dumps(d)
        assert "stake" not in js.lower()
        assert "bet_instruction" not in js.lower()
