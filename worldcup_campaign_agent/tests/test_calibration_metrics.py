"""Tests for calibration_metrics module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.calibration_metrics import (
    calculate_brier_score, calculate_log_loss, calculate_hit_rate,
    build_calibration_bins, summarize_metric_distribution,
    CalibrationBin, CalibrationBins, MetricDistributionSummary
)


class TestBrierScore:
    def test_perfect_prediction_win(self):
        score = calculate_brier_score(1.0, 1)
        assert score == 0.0

    def test_perfect_prediction_loss(self):
        score = calculate_brier_score(0.0, 0)
        assert score == 0.0

    def test_max_error(self):
        score = calculate_brier_score(1.0, 0)
        assert score == 1.0

    def test_moderate_error(self):
        score = calculate_brier_score(0.7, 0)
        assert pytest.approx(score, abs=0.01) == 0.49

    def test_invalid_probability_negative(self):
        with pytest.raises(ValueError):
            calculate_brier_score(-0.1, 1)

    def test_invalid_probability_above_one(self):
        with pytest.raises(ValueError):
            calculate_brier_score(1.5, 0)

    def test_invalid_outcome(self):
        with pytest.raises(ValueError):
            calculate_brier_score(0.5, 2)


class TestLogLoss:
    def test_perfect_prediction_win(self):
        loss = calculate_log_loss(0.999, 1)
        assert loss < 0.01

    def test_perfect_prediction_loss(self):
        loss = calculate_log_loss(0.001, 0)
        assert loss < 0.01

    def test_wrong_prediction(self):
        loss = calculate_log_loss(0.001, 1)
        assert loss > 1.0

    def test_invalid_probability(self):
        with pytest.raises(ValueError):
            calculate_log_loss(-0.1, 1)

    def test_invalid_outcome(self):
        with pytest.raises(ValueError):
            calculate_log_loss(0.5, 3)


class TestHitRate:
    def test_all_hits(self):
        assert calculate_hit_rate([1, 1, 1]) == 1.0

    def test_all_misses(self):
        assert calculate_hit_rate([0, 0, 0]) == 0.0

    def test_mixed(self):
        assert calculate_hit_rate([1, 0, 1, 0]) == 0.5

    def test_empty(self):
        assert calculate_hit_rate([]) == 0.0

    def test_with_nones(self):
        assert calculate_hit_rate([1, None, 0, None]) == 0.5


class TestCalibrationBins:
    def test_build_bins(self):
        class FakeRecord:
            def __init__(self, prob, outcome, pending=False):
                self.predicted_probability = prob
                self.actual_outcome = outcome
                self.is_pending = pending

        records = [
            FakeRecord(0.05, 0),
            FakeRecord(0.15, 0),
            FakeRecord(0.25, 1),
            FakeRecord(0.45, 1),
            FakeRecord(0.55, 1),
            FakeRecord(0.75, 1),
            FakeRecord(0.85, 1),
            FakeRecord(0.95, 1),
        ]
        bins = [0.0, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 1.0]
        result = build_calibration_bins(records, bins)
        assert result.total_samples == 8
        assert len(result.bins) == 8

    def test_pending_excluded_from_bins(self):
        class FakeRecord:
            def __init__(self, prob, outcome, pending=False):
                self.predicted_probability = prob
                self.actual_outcome = outcome
                self.is_pending = pending

        records = [
            FakeRecord(0.5, 1),
            FakeRecord(0.5, 0, pending=True),
            FakeRecord(0.5, 1),
        ]
        bins = [0.0, 0.5, 1.0]
        result = build_calibration_bins(records, bins)
        assert result.total_samples == 2

    def test_small_sample_warning(self):
        class FakeRecord:
            def __init__(self, prob, outcome):
                self.predicted_probability = prob
                self.actual_outcome = outcome
                self.is_pending = False

        records = [FakeRecord(0.5, 1)]
        bins = [0.0, 0.5, 1.0]
        result = build_calibration_bins(records, bins)
        assert any("Small sample" in b.warning for b in result.bins if b.warning)


class TestMetricDistribution:
    def test_summarize(self):
        class FakeRecord:
            def __init__(self, prob, outcome, pending=False):
                self.predicted_probability = prob
                self.actual_outcome = outcome
                self.is_pending = pending

        records = [
            FakeRecord(0.8, 1),
            FakeRecord(0.3, 0),
            FakeRecord(0.5, 1, pending=True),
        ]
        summary = summarize_metric_distribution(records)
        assert summary.realized_count == 2
        assert summary.pending_count == 1

    def test_small_sample_warning(self):
        class FakeRecord:
            def __init__(self, prob, outcome):
                self.predicted_probability = prob
                self.actual_outcome = outcome
                self.is_pending = False

        records = [FakeRecord(0.5, 1)]
        summary = summarize_metric_distribution(records)
        assert len(summary.warnings) > 0
