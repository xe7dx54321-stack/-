"""Market alignment: classifies agreement/disagreement across signal lines."""
from dataclasses import dataclass, field


@dataclass
class AlignmentRecord:
    key: str = ""
    model_prob: float = 0.0
    sportsbook_prob: float = 0.0
    polymarket_prob: float = 0.0
    alignment_status: str = "insufficient_data"
    model_vs_market_gap: float = 0.0
    sportsbook_vs_polymarket_gap: float = 0.0
    is_major_disagreement: bool = False


@dataclass
class AlignmentSummary:
    records: list = field(default_factory=list)
    record_count: int = 0
    market_aligned_count: int = 0
    model_above_market_count: int = 0
    model_below_market_count: int = 0
    sportsbook_polymarket_disagree_count: int = 0
    major_disagreement_count: int = 0
    insufficient_data_count: int = 0
    warnings: list = field(default_factory=list)


def assess_market_alignment(sources: dict, config: dict = None) -> AlignmentSummary:
    config = config or {}
    al_cfg = config.get("alignment", {})
    aligned_threshold = al_cfg.get("aligned_threshold", 0.05)
    minor_threshold = al_cfg.get("minor_disagreement_threshold", 0.10)
    major_threshold = al_cfg.get("major_disagreement_threshold", 0.20)

    model_probs = sources.get("model_probs", {})
    sb_probs = sources.get("sportsbook_probs", {})
    pm_probs = sources.get("polymarket_probs", {})

    summary = AlignmentSummary()
    all_keys = set(list(model_probs.keys()) + list(sb_probs.keys()))

    for key in sorted(all_keys):
        model_p = model_probs.get(key, 0)
        sb_p = sb_probs.get(key, 0)
        pm_p = pm_probs.get(key, 0)

        available = sum(1 for p in [model_p, sb_p, pm_p] if p > 0)
        if available < 2:
            summary.insufficient_data_count += 1
            summary.records.append(AlignmentRecord(
                key=key, model_prob=model_p, sportsbook_prob=sb_p,
                polymarket_prob=pm_p, alignment_status="insufficient_data"
            ))
            continue

        model_vs_mkt = model_p - sb_p if model_p > 0 and sb_p > 0 else 0
        sb_vs_pm = sb_p - pm_p if sb_p > 0 and pm_p > 0 else 0
        max_gap = max(abs(model_vs_mkt), abs(sb_vs_pm))

        if max_gap <= aligned_threshold:
            status = "aligned"
            summary.market_aligned_count += 1
        elif max_gap <= minor_threshold:
            status = "minor_disagreement"
        elif max_gap >= major_threshold:
            status = "major_disagreement"
            summary.major_disagreement_count += 1
        else:
            status = "minor_disagreement"

        record = AlignmentRecord(
            key=key, model_prob=round(model_p, 6),
            sportsbook_prob=round(sb_p, 6), polymarket_prob=round(pm_p, 6),
            alignment_status=status,
            model_vs_market_gap=round(model_vs_mkt, 6),
            sportsbook_vs_polymarket_gap=round(sb_vs_pm, 6),
            is_major_disagreement=status == "major_disagreement",
        )
        summary.records.append(record)
        summary.record_count += 1

        if model_vs_mkt > aligned_threshold:
            summary.model_above_market_count += 1
        elif model_vs_mkt < -aligned_threshold:
            summary.model_below_market_count += 1
        if abs(sb_vs_pm) > aligned_threshold:
            summary.sportsbook_polymarket_disagree_count += 1

    return summary
