"""Futures performance review: tracks long-horizon futures candidate outcomes."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FuturesPerformanceReview:
    futures_candidate_count: int = 0
    futures_bucket_count: int = 0
    attack_longshot_count: int = 0
    watch_only_count: int = 0
    settled_futures_count: int = 0
    pending_futures_count: int = 0
    hit_rate: Optional[float] = None
    path_model_warning_summary: dict = field(default_factory=dict)
    winner_probability_sum_warning: str = ""
    performance_by_market_type: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


def review_futures_performance(
    futures_preview: dict,
    settlement_result: dict = None,
    config: dict = None
) -> FuturesPerformanceReview:
    review = FuturesPerformanceReview()
    config = config or {}

    if futures_preview:
        review.futures_candidate_count = futures_preview.get("futures_candidate_count", futures_preview.get("candidate_count", 0))
        review.futures_bucket_count = futures_preview.get("futures_bucket_count", 0)
        review.attack_longshot_count = futures_preview.get("attack_longshot_count", 0)
        review.watch_only_count = futures_preview.get("watch_only_count", 0)

        # Winner probability sum
        wps = futures_preview.get("winner_probability_sum_warning", futures_preview.get("winner_probability_sum", ""))
        if wps:
            review.winner_probability_sum_warning = str(wps)

        # Path model warnings
        path_warnings = futures_preview.get("path_model_warnings", futures_preview.get("path_sanity", {}))
        review.path_model_warning_summary = {
            "winner_probability_sum": futures_preview.get("winner_probability_sum_warning", ""),
            "golden_boot_deferred": futures_preview.get("golden_boot_deferred", True),
            "path_simulation_note": futures_preview.get("path_simulation_note", "synthetic futures odds, proxy-based path model"),
        }

    # Cross-reference with settlement
    if settlement_result:
        ledger = settlement_result.get("simulation_ledger", settlement_result.get("ledger", []))
        futures_entries = [e for e in ledger if isinstance(e, dict) and (
            e.get("source_type") == "futures" or e.get("bucket") == "futures" or
            "futures" in str(e.get("record_id", ""))
        )]
        review.settled_futures_count = sum(1 for e in futures_entries if not e.get("is_pending", False) and e.get("actual_outcome") is not None)
        review.pending_futures_count = sum(1 for e in futures_entries if e.get("is_pending", False) or e.get("actual_outcome") is None)

        settled = [e for e in futures_entries if not e.get("is_pending", False) and e.get("actual_outcome") is not None]
        if settled:
            hits = sum(1 for e in settled if e.get("actual_outcome") == 1)
            review.hit_rate = hits / len(settled)

        # By market type
        mt_stats = {}
        for e in futures_entries:
            mt = e.get("market_type", e.get("market", "unknown"))
            if mt not in mt_stats:
                mt_stats[mt] = {"total": 0, "settled": 0, "pending": 0, "hits": 0}
            mt_stats[mt]["total"] += 1
            if not e.get("is_pending", False) and e.get("actual_outcome") is not None:
                mt_stats[mt]["settled"] += 1
                if e.get("actual_outcome") == 1:
                    mt_stats[mt]["hits"] += 1
            else:
                mt_stats[mt]["pending"] += 1
        review.performance_by_market_type = mt_stats

    # Pending is normal for futures
    review.warnings.append("Pending futures are normal—long-horizon settlement. Do not treat pending as miss.")
    review.warnings.append("Winner probability sum may exceed 1.0 due to synthetic proxy model; this is a known model limitation.")

    if review.winner_probability_sum_warning:
        review.warnings.append(f"Winner probability sum warning: {review.winner_probability_sum_warning}")

    review.warnings.append("Golden boot market deferred—not modeled in current version.")

    return review
