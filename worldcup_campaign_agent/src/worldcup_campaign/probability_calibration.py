"""Probability calibration review: compares model probabilities against actual outcomes."""
from dataclasses import dataclass, field
from typing import Optional
from .calibration_metrics import (
    calculate_brier_score, calculate_log_loss, calculate_hit_rate,
    build_calibration_bins, summarize_metric_distribution
)


@dataclass
class ProbabilityCalibrationRecord:
    record_id: str = ""
    source_type: str = ""
    market_type: str = ""
    selection_id: str = ""
    predicted_probability: float = 0.0
    actual_outcome: Optional[int] = None
    outcome_status: str = "pending"
    is_pending: bool = True
    confidence: str = "low"
    data_quality: str = "synthetic"
    warnings: list = field(default_factory=list)


@dataclass
class ProbabilityCalibrationReview:
    record_count: int = 0
    realized_count: int = 0
    pending_count: int = 0
    brier_score: Optional[float] = None
    log_loss: Optional[float] = None
    hit_rate: Optional[float] = None
    calibration_bins: list = field(default_factory=list)
    market_type_breakdown: dict = field(default_factory=dict)
    confidence_breakdown: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


def build_probability_calibration_records(
    settlement_ledger: list,
    match_probability_preview: dict,
    manual_results: dict = None
) -> list:
    records = []
    if not settlement_ledger:
        return records

    for i, entry in enumerate(settlement_ledger):
        if not isinstance(entry, dict):
            continue

        record_id = entry.get("record_id", entry.get("candidate_id", f"record_{i}"))
        is_pending = entry.get("is_pending", entry.get("status", "") == "pending")
        actual = entry.get("actual_outcome", None)
        if actual is None and not is_pending:
            is_pending = True

        prob = entry.get("predicted_probability", entry.get("model_probability", 0.0))
        market = entry.get("market_type", entry.get("market", "unknown"))
        source = entry.get("source_type", entry.get("source", "settlement_ledger"))

        record = ProbabilityCalibrationRecord(
            record_id=record_id,
            source_type=source,
            market_type=market,
            selection_id=entry.get("selection_id", entry.get("selection", "")),
            predicted_probability=float(prob) if prob else 0.0,
            actual_outcome=int(actual) if actual is not None else None,
            outcome_status="pending" if is_pending else ("hit" if actual == 1 else "miss"),
            is_pending=is_pending,
            confidence=entry.get("confidence", entry.get("data_confidence", "low")),
            data_quality=entry.get("data_quality", "synthetic"),
            warnings=[]
        )
        records.append(record)

    # Also try to extract from match_probability_preview if available
    if match_probability_preview and isinstance(match_probability_preview, dict):
        matches = match_probability_preview.get("matches", match_probability_preview.get("match_previews", []))
        if isinstance(matches, list):
            for m in matches:
                if not isinstance(m, dict):
                    continue
                match_id = m.get("match_id", m.get("id", ""))
                # Only add if not already present
                existing_ids = {r.record_id for r in records}
                for market_type in ["1x2", "over_under", "handicap"]:
                    record_id = f"prob_{match_id}_{market_type}"
                    if record_id in existing_ids:
                        continue
                    prob_data = m.get(market_type, m.get("probabilities", {}))
                    if isinstance(prob_data, dict) and "probability" in prob_data:
                        records.append(ProbabilityCalibrationRecord(
                            record_id=record_id,
                            source_type="probability_model",
                            market_type=market_type,
                            selection_id=match_id,
                            predicted_probability=float(prob_data.get("probability", 0)),
                            is_pending=True,
                            confidence="low",
                            data_quality="synthetic",
                        ))

    return records


def review_probability_calibration(records: list, config: dict) -> ProbabilityCalibrationReview:
    review = ProbabilityCalibrationReview()
    review.record_count = len(records)
    review.pending_count = sum(1 for r in records if r.is_pending)
    review.realized_count = review.record_count - review.pending_count

    realized = [r for r in records if not r.is_pending]
    if realized:
        briers = [calculate_brier_score(r.predicted_probability, r.actual_outcome or 0) for r in realized]
        review.brier_score = sum(briers) / len(briers)
        losses = [calculate_log_loss(r.predicted_probability, r.actual_outcome or 0) for r in realized]
        review.log_loss = sum(losses) / len(losses)
        review.hit_rate = calculate_hit_rate([r.actual_outcome for r in realized])
    else:
        review.brier_score = None
        review.log_loss = None
        review.hit_rate = None
        review.warnings.append("No realized records available; all records are pending.")

    # Calibration bins
    bins_config = config.get("calibration_bins", [0.0, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 1.0])
    cb = build_calibration_bins(records, bins_config)
    review.calibration_bins = [{
        "bin_lower": b.bin_lower,
        "bin_upper": b.bin_upper,
        "sample_count": b.sample_count,
        "average_predicted": round(b.average_predicted, 4),
        "observed_rate": round(b.observed_rate, 4),
        "calibration_gap": round(b.calibration_gap, 4),
        "warning": b.warning,
    } for b in cb.bins]

    # Market type breakdown
    market_types = {}
    for r in records:
        mt = r.market_type or "unknown"
        if mt not in market_types:
            market_types[mt] = {"total": 0, "realized": 0, "hits": 0}
        market_types[mt]["total"] += 1
        if not r.is_pending:
            market_types[mt]["realized"] += 1
            if r.actual_outcome == 1:
                market_types[mt]["hits"] += 1
    review.market_type_breakdown = market_types

    # Confidence breakdown
    conf = {}
    for r in records:
        c = r.confidence or "unknown"
        if c not in conf:
            conf[c] = {"total": 0, "realized": 0}
        conf[c]["total"] += 1
        if not r.is_pending:
            conf[c]["realized"] += 1
    review.confidence_breakdown = conf

    # Small sample warnings
    min_samples = config.get("min_sample_size_for_recommendation", 10)
    if review.realized_count < min_samples:
        review.warnings.append(
            f"Only {review.realized_count} realized records (minimum {min_samples} for recommendations). "
            "Conclusions are indicative only; recommend needs_more_sample for any model changes."
        )

    return review
