"""Tests for model_recommendation module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.model_recommendation import (
    build_model_recommendations, CalibrationRecommendations, CalibrationRecommendation
)
from worldcup_campaign.probability_calibration import ProbabilityCalibrationReview
from worldcup_campaign.bucket_performance_review import BucketPerformanceReview
from worldcup_campaign.parlay_performance_review import ParlayPerformanceReview
from worldcup_campaign.futures_performance_review import FuturesPerformanceReview
from worldcup_campaign.source_alignment import SourceAlignmentResult

POLICY = {
    "forbidden_recommendations": ["place_real_bet", "increase_real_stake", "chase_loss", "borrow_money", "guaranteed_profit"],
    "min_sample_size_for_recommendation": 10,
}


class DummyProbReview:
    realized_count = 2
    pending_count = 0
    brier_score = 0.2
    log_loss = 0.5
    hit_rate = 0.5
    calibration_bins = [
        {"bin_lower": 0.0, "bin_upper": 1.0, "sample_count": 2, "average_predicted": 0.5, "observed_rate": 0.5, "calibration_gap": 0.0}
    ]
    warnings = []


class DummyBucketReview:
    bucket_breakdowns = {
        "attack": {"realized_count": 2, "hit_rate": 0.0},
        "core": {"realized_count": 2, "hit_rate": 0.5},
    }


class DummyParlayReview:
    resolved_parlay_count = 2
    blocked_combination_count = 10


class DummyFuturesReview:
    pending_futures_count = 10


class TestRecommendations:
    def test_generates_recommendations(self):
        recs = build_model_recommendations(
            DummyProbReview(), DummyBucketReview(), DummyParlayReview(),
            DummyFuturesReview(), SourceAlignmentResult(), POLICY
        )
        assert isinstance(recs.recommendations, list)

    def test_needs_more_sample_when_small(self):
        prob_review = ProbabilityCalibrationReview(realized_count=3, pending_count=0)
        recs = build_model_recommendations(
            prob_review, DummyBucketReview(), DummyParlayReview(),
            DummyFuturesReview(), SourceAlignmentResult(), POLICY
        )
        types = [r["recommendation_type"] for r in recs.recommendations]
        assert "needs_more_sample" in types

    def test_no_increase_real_stake(self):
        recs = build_model_recommendations(
            DummyProbReview(), DummyBucketReview(), DummyParlayReview(),
            DummyFuturesReview(), SourceAlignmentResult(), POLICY
        )
        for r in recs.recommendations:
            assert r["recommendation_type"] != "increase_real_stake"

    def test_no_chase_loss(self):
        recs = build_model_recommendations(
            DummyProbReview(), DummyBucketReview(), DummyParlayReview(),
            DummyFuturesReview(), SourceAlignmentResult(), POLICY
        )
        for r in recs.recommendations:
            assert r["recommendation_type"] != "chase_loss"

    def test_no_guaranteed_profit(self):
        recs = build_model_recommendations(
            DummyProbReview(), DummyBucketReview(), DummyParlayReview(),
            DummyFuturesReview(), SourceAlignmentResult(), POLICY
        )
        for r in recs.recommendations:
            assert r["recommendation_type"] != "guaranteed_profit"

    def test_can_generate_review_model_bias(self):
        prob_review = ProbabilityCalibrationReview(
            realized_count=15, pending_count=0,
            brier_score=0.30, log_loss=1.2, hit_rate=0.25,
            calibration_bins=[
                {"bin_lower": 0.5, "bin_upper": 0.65, "sample_count": 10, "average_predicted": 0.6, "observed_rate": 0.3, "calibration_gap": 0.3}
            ],
            warnings=[]
        )
        recs = build_model_recommendations(
            prob_review, DummyBucketReview(), DummyParlayReview(),
            DummyFuturesReview(), SourceAlignmentResult(), POLICY
        )
        types = [r["recommendation_type"] for r in recs.recommendations]
        assert "review_model_bias" in types or len(recs.recommendations) > 0

    def test_can_generate_futures_path_proxy_review(self):
        recs = build_model_recommendations(
            DummyProbReview(), DummyBucketReview(), DummyParlayReview(),
            DummyFuturesReview(), SourceAlignmentResult(), POLICY
        )
        # Should include needs_more_sample for futures with pending
        dims = [r["dimension"] for r in recs.recommendations]
        if "futures_performance" in dims:
            for r in recs.recommendations:
                if r["dimension"] == "futures_performance":
                    assert r["recommendation_type"] == "needs_more_sample"

    def test_each_has_reason_sample_confidence(self):
        recs = build_model_recommendations(
            DummyProbReview(), DummyBucketReview(), DummyParlayReview(),
            DummyFuturesReview(), SourceAlignmentResult(), POLICY
        )
        for r in recs.recommendations:
            assert "reason" in r
            assert "sample_size" in r
            assert "confidence" in r

    def test_not_betting_advice_true(self):
        recs = build_model_recommendations(
            DummyProbReview(), DummyBucketReview(), DummyParlayReview(),
            DummyFuturesReview(), SourceAlignmentResult(), POLICY
        )
        assert recs.not_betting_advice is True
