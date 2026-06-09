"""Bucket performance review: analyzes candidate performance per bucket."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BucketBreakdown:
    bucket_name: str = ""
    candidate_count: int = 0
    realized_count: int = 0
    pending_count: int = 0
    hit_rate: Optional[float] = None
    simulated_pl: float = 0.0
    notes: str = ""
    warnings: list = field(default_factory=list)


@dataclass
class BucketPerformanceReview:
    bucket_breakdowns: dict = field(default_factory=dict)
    overall_summary: str = ""
    realized_return_units: float = 0.0
    pending_units: float = 0.0
    hit_rate_by_bucket: dict = field(default_factory=dict)
    simulated_pl_by_bucket: dict = field(default_factory=dict)
    candidate_count_by_bucket: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


def review_bucket_performance(
    settlement_result: dict,
    simulation_ledger: list = None,
    config: dict = None
) -> BucketPerformanceReview:
    review = BucketPerformanceReview()
    config = config or {}
    ledger = simulation_ledger or settlement_result.get("simulation_ledger", settlement_result.get("ledger", []))

    buckets = ["core", "edge", "attack", "futures", "parlay"]
    breakdowns = {}

    for bucket in buckets:
        bd = BucketBreakdown(bucket_name=bucket)
        if isinstance(ledger, list):
            bucket_entries = [e for e in ledger if isinstance(e, dict) and e.get("bucket", e.get("source_bucket", "")) == bucket]
            bd.candidate_count = len(bucket_entries)
            realized_entries = [e for e in bucket_entries if not e.get("is_pending", False) and e.get("actual_outcome") is not None]
            pending_entries = [e for e in bucket_entries if e.get("is_pending", False) or e.get("actual_outcome") is None]
            bd.realized_count = len(realized_entries)
            bd.pending_count = len(pending_entries)

            if realized_entries:
                hits = sum(1 for e in realized_entries if e.get("actual_outcome") == 1)
                bd.hit_rate = hits / len(realized_entries)

            # Simulated P/L
            pl = 0.0
            for e in bucket_entries:
                if not e.get("is_pending", False) and e.get("actual_outcome") is not None:
                    if e.get("actual_outcome") == 1:
                        odds = e.get("decimal_odds", e.get("odds", 1.0))
                        pl += max(0, odds - 1.0)  # simplified: win returns odds-1 units
                    else:
                        pl -= 1.0  # simplified: lose costs 1 unit
                elif e.get("is_pending", False):
                    pass  # pending does not affect P/L
            bd.simulated_pl = round(pl, 2)

        # Bucket-specific notes
        if bucket == "attack":
            bd.notes = "High variance path. Short-term misses expected; evaluate over multiple windows, not single outcomes."
            bd.warnings.append("Attack bucket has high variance; small sample may be misleading.")
        elif bucket == "core":
            bd.notes = "Base stability focus. Low odds, high probability candidates for floor contribution."
        elif bucket == "edge":
            bd.notes = "Balanced EV/probability candidates for edge multiplier role."
        elif bucket == "futures":
            bd.notes = "Long-horizon futures. Pending is normal state—do not treat as realized loss."
            bd.warnings.append("Futures pending balance is not realized loss; settlement horizon spans tournament.")
        elif bucket == "parlay":
            bd.notes = "Multi-leg combinations. Evaluate combined probability and correlation."
            bd.warnings.append("Parlay performance requires larger sample for statistical significance.")

        breakdowns[bucket] = bd
        review.hit_rate_by_bucket[bucket] = bd.hit_rate
        review.simulated_pl_by_bucket[bucket] = bd.simulated_pl
        review.candidate_count_by_bucket[bucket] = bd.candidate_count

    review.bucket_breakdowns = {k: {
        "bucket_name": v.bucket_name,
        "candidate_count": v.candidate_count,
        "realized_count": v.realized_count,
        "pending_count": v.pending_count,
        "hit_rate": v.hit_rate,
        "simulated_pl": v.simulated_pl,
        "notes": v.notes,
        "warnings": v.warnings,
    } for k, v in breakdowns.items()}

    # Overall summary
    total_realized = sum(v.realized_count for v in breakdowns.values())
    total_pending = sum(v.pending_count for v in breakdowns.values())
    review.realized_return_units = sum(v.simulated_pl for v in breakdowns.values())
    review.pending_units = float(total_pending)
    review.overall_summary = (
        f"{total_realized} realized, {total_pending} pending across {len(buckets)} buckets. "
        f"Simulated P/L: {review.realized_return_units:+.2f} units realized. "
        f"Pending units: {review.pending_units}. Pending is NOT realized loss."
    )

    pending_policy = config.get("pending_policy", {})
    if pending_policy.get("exclude_pending_from_realized_metrics", True):
        review.warnings.append("Pending positions excluded from realized metrics per pending_policy.")

    return review
