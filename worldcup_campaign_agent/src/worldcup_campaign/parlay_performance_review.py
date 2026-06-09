"""Parlay performance review: analyzes parlay combination outcomes."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParlayPerformanceReview:
    source_candidate_count: int = 0
    raw_combination_count: int = 0
    blocked_combination_count: int = 0
    ranked_parlay_count: int = 0
    resolved_parlay_count: int = 0
    pending_parlay_count: int = 0
    hit_rate: Optional[float] = None
    simulated_pl: float = 0.0
    performance_by_leg_count: dict = field(default_factory=dict)
    correlation_warning_summary: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


def review_parlay_performance(
    parlay_preview: dict,
    settlement_result: dict = None,
    config: dict = None
) -> ParlayPerformanceReview:
    review = ParlayPerformanceReview()
    config = config or {}

    if parlay_preview:
        review.source_candidate_count = parlay_preview.get("source_candidate_count", 0)
        review.raw_combination_count = parlay_preview.get("raw_combination_count", 0)
        review.blocked_combination_count = parlay_preview.get("blocked_combination_count", 0)

        # Get ranked parlays
        ranked = parlay_preview.get("ranked_parlays", parlay_preview.get("parlays", []))
        if isinstance(ranked, list):
            review.ranked_parlay_count = len(ranked)
        elif isinstance(parlay_preview.get("parlay_summary"), dict):
            ps = parlay_preview["parlay_summary"]
            review.ranked_parlay_count = ps.get("ranked_parlay_count", 0)

        # Correlation warning summary
        corr = parlay_preview.get("correlation_summary", parlay_preview.get("correlation", {}))
        review.correlation_warning_summary = {
            "same_match_blocked": corr.get("same_match_blocked", corr.get("blocked_count", 0)),
            "same_group_warnings": corr.get("same_group_warnings", 0),
            "same_market_warnings": corr.get("same_market_warnings", 0),
            "is_blocked_enforced": corr.get("is_blocked_enforced", True),
        }

    # Cross-reference with settlement
    if settlement_result:
        ledger = settlement_result.get("simulation_ledger", settlement_result.get("ledger", []))
        parlay_entries = [e for e in ledger if isinstance(e, dict) and (
            e.get("source_type") == "parlay" or e.get("bucket") == "parlay" or
            "parlay" in str(e.get("record_id", ""))
        )]
        review.resolved_parlay_count = sum(1 for e in parlay_entries if not e.get("is_pending", False) and e.get("actual_outcome") is not None)
        review.pending_parlay_count = sum(1 for e in parlay_entries if e.get("is_pending", False) or e.get("actual_outcome") is None)

        resolved = [e for e in parlay_entries if not e.get("is_pending", False) and e.get("actual_outcome") is not None]
        if resolved:
            hits = sum(1 for e in resolved if e.get("actual_outcome") == 1)
            review.hit_rate = hits / len(resolved)

        # Simulated P/L for parlays
        pl = 0.0
        for e in parlay_entries:
            if not e.get("is_pending", False) and e.get("actual_outcome") is not None:
                if e.get("actual_outcome") == 1:
                    odds = e.get("decimal_odds", e.get("combined_odds", 1.0))
                    pl += max(0, odds - 1.0)
                else:
                    pl -= 1.0
        review.simulated_pl = round(pl, 2)

    # Performance by leg count (from preview)
    if isinstance(parlay_preview.get("parlay_summary"), dict):
        ps = parlay_preview["parlay_summary"]
        review.performance_by_leg_count = {
            "edge_parlay_count": ps.get("edge_parlay_count", 0),
            "attack_parlay_count": ps.get("attack_parlay_count", 0),
        }

    # Synthetic odds warning
    if parlay_preview.get("synthetic_odds_warning", False) or parlay_preview.get("odds_source", "") == "synthetic":
        review.warnings.append("Synthetic odds used for parlay legs; real-odds calibration not yet applied.")

    # Same-match blocked is NOT failure
    review.warnings.append("Same-match blocked combinations are NOT counted as failures; they are blocked by design.")

    pending_policy = config.get("pending_policy", {})
    if pending_policy.get("exclude_pending_from_realized_metrics", True):
        review.warnings.append("Pending parlays excluded from realized hit rate per pending_policy.")

    return review
