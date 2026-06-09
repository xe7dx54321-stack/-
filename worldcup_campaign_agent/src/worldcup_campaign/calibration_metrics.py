"""Calibration metrics: Brier score, log loss, hit rate, calibration bins."""
import math
from dataclasses import dataclass, field


@dataclass
class CalibrationBin:
    bin_lower: float = 0.0
    bin_upper: float = 1.0
    sample_count: int = 0
    average_predicted: float = 0.0
    observed_rate: float = 0.0
    calibration_gap: float = 0.0
    warning: str = ""


@dataclass
class CalibrationBins:
    bins: list = field(default_factory=list)
    total_samples: int = 0
    warnings: list = field(default_factory=list)


@dataclass
class MetricDistributionSummary:
    brier_score: float = 0.0
    log_loss: float = 0.0
    hit_rate: float = 0.0
    sample_count: int = 0
    pending_count: int = 0
    realized_count: int = 0
    warnings: list = field(default_factory=list)


def calculate_brier_score(predicted_probability: float, actual_outcome: int) -> float:
    if not (0 <= predicted_probability <= 1):
        raise ValueError(f"Probability must be in [0,1], got {predicted_probability}")
    if actual_outcome not in (0, 1):
        raise ValueError(f"Actual outcome must be 0 or 1, got {actual_outcome}")
    return (predicted_probability - actual_outcome) ** 2


def calculate_log_loss(predicted_probability: float, actual_outcome: int, epsilon: float = 1e-15) -> float:
    if not (0 <= predicted_probability <= 1):
        raise ValueError(f"Probability must be in [0,1], got {predicted_probability}")
    if actual_outcome not in (0, 1):
        raise ValueError(f"Actual outcome must be 0 or 1, got {actual_outcome}")
    p = max(epsilon, min(1 - epsilon, predicted_probability))
    return -(actual_outcome * math.log(p) + (1 - actual_outcome) * math.log(1 - p))


def calculate_hit_rate(outcomes: list) -> float:
    if not outcomes:
        return 0.0
    realized = [o for o in outcomes if o is not None]
    if not realized:
        return 0.0
    return sum(1 for o in realized if o == 1) / len(realized)


def build_calibration_bins(records: list, bins: list) -> CalibrationBins:
    cb = CalibrationBins()
    realized_records = [r for r in records if not getattr(r, "is_pending", False) and getattr(r, "actual_outcome", None) is not None]

    if not realized_records:
        cb.warnings.append("No realized records for calibration bin analysis.")
        return cb

    for i in range(len(bins) - 1):
        lower = bins[i]
        upper = bins[i + 1]
        bucket_records = []
        for r in realized_records:
            prob = getattr(r, "predicted_probability", 0)
            if lower <= prob < upper:
                bucket_records.append(r)
            elif abs(upper - 1.0) < 1e-9 and abs(prob - 1.0) < 1e-9:
                bucket_records.append(r)

        bin_obj = CalibrationBin(bin_lower=lower, bin_upper=upper, sample_count=len(bucket_records))
        if bucket_records:
            bin_obj.average_predicted = sum(getattr(r, "predicted_probability", 0) for r in bucket_records) / len(bucket_records)
            bin_obj.observed_rate = sum(getattr(r, "actual_outcome", 0) for r in bucket_records) / len(bucket_records)
            bin_obj.calibration_gap = bin_obj.average_predicted - bin_obj.observed_rate
        if len(bucket_records) < 5:
            bin_obj.warning = f"Small sample (n={len(bucket_records)}) in bin [{lower}, {upper})"
        cb.bins.append(bin_obj)

    cb.total_samples = len(realized_records)
    return cb


def summarize_metric_distribution(records: list) -> MetricDistributionSummary:
    summary = MetricDistributionSummary()
    summary.sample_count = len(records)
    summary.pending_count = sum(1 for r in records if getattr(r, "is_pending", False))
    realized = [r for r in records if not getattr(r, "is_pending", False) and getattr(r, "actual_outcome", None) is not None]
    summary.realized_count = len(realized)

    if realized:
        briers = []
        log_losses = []
        outcomes = []
        for r in realized:
            prob = getattr(r, "predicted_probability", 0)
            actual = getattr(r, "actual_outcome", 0)
            briers.append(calculate_brier_score(prob, actual))
            log_losses.append(calculate_log_loss(prob, actual))
            outcomes.append(actual)

        summary.brier_score = sum(briers) / len(briers) if briers else 0
        summary.log_loss = sum(log_losses) / len(log_losses) if log_losses else 0
        summary.hit_rate = calculate_hit_rate(outcomes)

    if summary.realized_count < 10:
        summary.warnings.append(f"Small sample: only {summary.realized_count} realized records; conclusions are indicative only.")

    return summary
