"""Tests for parlay_performance_review module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.parlay_performance_review import (
    review_parlay_performance, ParlayPerformanceReview
)


class TestParlayPerformance:
    def test_generates_review(self):
        preview = {"source_candidate_count": 10, "raw_combination_count": 100, "blocked_combination_count": 15}
        review = review_parlay_performance(preview)
        assert review.source_candidate_count == 10
        assert review.raw_combination_count == 100
        assert review.blocked_combination_count == 15

    def test_same_match_blocked_not_failure(self):
        preview = {"blocked_combination_count": 20}
        review = review_parlay_performance(preview)
        ws = " ".join(review.warnings)
        assert "blocked" in ws.lower()

    def test_leg_count_breakdown(self):
        preview = {
            "parlay_summary": {"edge_parlay_count": 3, "attack_parlay_count": 7, "ranked_parlay_count": 10}
        }
        review = review_parlay_performance(preview)
        assert review.performance_by_leg_count.get("edge_parlay_count") == 3
        assert review.performance_by_leg_count.get("attack_parlay_count") == 7

    def test_pending_not_in_realized_hit_rate(self):
        preview = {"blocked_combination_count": 0}
        settlement = {
            "simulation_ledger": [
                {"record_id": "parlay_1", "source_type": "parlay", "is_pending": True, "actual_outcome": None},
                {"record_id": "parlay_2", "source_type": "parlay", "is_pending": False, "actual_outcome": 1, "decimal_odds": 5.0},
            ]
        }
        review = review_parlay_performance(preview, settlement)
        assert review.resolved_parlay_count == 1

    def test_correlation_warning_summary(self):
        preview = {
            "correlation_summary": {
                "same_match_blocked": 15, "same_group_warnings": 5, "same_market_warnings": 10, "is_blocked_enforced": True
            }
        }
        review = review_parlay_performance(preview)
        cs = review.correlation_warning_summary
        assert cs.get("same_match_blocked") == 15
        assert cs.get("same_group_warnings") == 5

    def test_synthetic_odds_warning(self):
        preview = {"odds_source": "synthetic", "synthetic_odds_warning": True}
        review = review_parlay_performance(preview)
        assert any("synthetic" in w.lower() for w in review.warnings)

    def test_no_stake_output(self):
        preview = {"blocked_combination_count": 0}
        review = review_parlay_performance(preview)
        d = {
            "source_candidate_count": review.source_candidate_count,
            "warnings": review.warnings,
        }
        js = json.dumps(d)
        assert "stake" not in js.lower()
        assert "bookmaker" not in js.lower()
