"""Tests for probability_calibration module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.probability_calibration import (
    build_probability_calibration_records, review_probability_calibration,
    ProbabilityCalibrationRecord, ProbabilityCalibrationReview
)

CALIBRATION_CONFIG = {
    "calibration_bins": [0.0, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 1.0],
    "min_sample_size_for_recommendation": 10,
}


class TestBuildRecords:
    def test_empty_ledger(self):
        records = build_probability_calibration_records([], {}, None)
        assert records == []

    def test_from_settlement_ledger(self):
        ledger = [
            {"record_id": "r1", "market_type": "1x2", "predicted_probability": 0.6, "actual_outcome": 1, "is_pending": False},
            {"record_id": "r2", "market_type": "over_under", "predicted_probability": 0.4, "actual_outcome": 0, "is_pending": False},
        ]
        records = build_probability_calibration_records(ledger, {}, None)
        assert len(records) == 2
        assert records[0].market_type == "1x2"
        assert records[1].is_pending is False

    def test_pending_records_identified(self):
        ledger = [
            {"record_id": "r1", "predicted_probability": 0.5, "actual_outcome": None, "is_pending": True},
        ]
        records = build_probability_calibration_records(ledger, {}, None)
        assert len(records) == 1
        assert records[0].is_pending is True
        assert records[0].outcome_status == "pending"

    def test_unknown_treated_as_pending(self):
        ledger = [
            {"record_id": "r1", "predicted_probability": 0.5},
        ]
        records = build_probability_calibration_records(ledger, {}, None)
        assert len(records) == 1
        assert records[0].is_pending is True

    def test_source_type_default(self):
        ledger = [
            {"record_id": "r1", "predicted_probability": 0.5, "source": "test", "market": "1x2"},
        ]
        records = build_probability_calibration_records(ledger, {}, None)
        assert records[0].source_type == "test"
        assert records[0].market_type == "1x2"


class TestReview:
    def test_basic_review(self):
        records = [
            ProbabilityCalibrationRecord(record_id="1", market_type="1x2", predicted_probability=0.7, actual_outcome=1, is_pending=False),
            ProbabilityCalibrationRecord(record_id="2", market_type="1x2", predicted_probability=0.3, actual_outcome=0, is_pending=False),
            ProbabilityCalibrationRecord(record_id="3", market_type="over_under", predicted_probability=0.5, is_pending=True),
        ]
        review = review_probability_calibration(records, CALIBRATION_CONFIG)
        assert review.record_count == 3
        assert review.realized_count == 2
        assert review.pending_count == 1
        assert review.brier_score is not None
        assert review.log_loss is not None
        assert review.hit_rate is not None

    def test_brier_score_output(self):
        records = [
            ProbabilityCalibrationRecord(record_id="1", predicted_probability=0.8, actual_outcome=1, is_pending=False),
            ProbabilityCalibrationRecord(record_id="2", predicted_probability=0.2, actual_outcome=0, is_pending=False),
        ]
        review = review_probability_calibration(records, CALIBRATION_CONFIG)
        assert review.brier_score is not None
        assert 0 <= review.brier_score <= 1

    def test_log_loss_output(self):
        records = [
            ProbabilityCalibrationRecord(record_id="1", predicted_probability=0.9, actual_outcome=1, is_pending=False),
        ]
        review = review_probability_calibration(records, CALIBRATION_CONFIG)
        assert review.log_loss is not None

    def test_hit_rate_output(self):
        records = [
            ProbabilityCalibrationRecord(record_id="1", predicted_probability=0.5, actual_outcome=1, is_pending=False),
            ProbabilityCalibrationRecord(record_id="2", predicted_probability=0.5, actual_outcome=0, is_pending=False),
        ]
        review = review_probability_calibration(records, CALIBRATION_CONFIG)
        assert review.hit_rate == 0.5

    def test_market_type_breakdown(self):
        records = [
            ProbabilityCalibrationRecord(record_id="1", market_type="1x2", predicted_probability=0.6, actual_outcome=1, is_pending=False),
            ProbabilityCalibrationRecord(record_id="2", market_type="over_under", predicted_probability=0.4, actual_outcome=0, is_pending=False),
        ]
        review = review_probability_calibration(records, CALIBRATION_CONFIG)
        assert "1x2" in review.market_type_breakdown
        assert "over_under" in review.market_type_breakdown

    def test_confidence_breakdown(self):
        records = [
            ProbabilityCalibrationRecord(record_id="1", confidence="low", predicted_probability=0.5, actual_outcome=1, is_pending=False),
        ]
        review = review_probability_calibration(records, CALIBRATION_CONFIG)
        assert "low" in review.confidence_breakdown

    def test_small_sample_warning(self):
        records = [
            ProbabilityCalibrationRecord(record_id="1", predicted_probability=0.5, actual_outcome=1, is_pending=False),
        ]
        review = review_probability_calibration(records, CALIBRATION_CONFIG)
        assert len(review.warnings) > 0

    def test_no_betting_advice(self):
        records = [
            ProbabilityCalibrationRecord(record_id="1", predicted_probability=0.5, actual_outcome=1, is_pending=False),
        ]
        review = review_probability_calibration(records, CALIBRATION_CONFIG)
        import json
        d = {
            "brier_score": review.brier_score,
            "warnings": review.warnings,
        }
        js = json.dumps(d)
        assert "stake" not in js.lower()
        assert "bet" not in js.lower() or "not_betting" in js.lower()
