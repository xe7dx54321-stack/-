"""Signal quality: assesses quality of each probability signal line."""
from dataclasses import dataclass, field


@dataclass
class QualityScore:
    source: str = ""
    key: str = ""
    score: float = 1.0
    quality_level: str = "high"
    penalties_applied: list = field(default_factory=list)


@dataclass
class SignalQualitySummary:
    scores: list = field(default_factory=list)
    high_quality_count: int = 0
    medium_quality_count: int = 0
    low_quality_count: int = 0
    average_quality_score: float = 0.0
    penalty_count: int = 0
    warnings: list = field(default_factory=list)


def assess_signal_quality(sources, config: dict = None) -> SignalQualitySummary:
    config = config or {}
    sq_config = config.get("signal_quality", {})
    high_threshold = sq_config.get("high_quality_threshold", 0.7)
    medium_threshold = sq_config.get("medium_quality_threshold", 0.4)
    penalties = sq_config.get("penalties", {})

    summary = SignalQualitySummary()
    all_scores = []

    # Model quality scores
    model_probs = sources.get("model_probs", {})
    mp_data = sources.get("model_data", {})
    model_conf = sum(1 for m in mp_data.get("matches", []) if m.get("confidence", 0) >= 0.1) if mp_data else 0
    for key in model_probs:
        score = 0.85
        p = []
        if model_conf < 4:
            score -= penalties.get("small_sample", 0.2)
            p.append("small_sample")
        qs = QualityScore(source="model", key=key, score=round(max(0.1, score), 4), penalties_applied=p)
        qs.quality_level = "high" if qs.score >= high_threshold else ("medium" if qs.score >= medium_threshold else "low")
        summary.scores.append(qs)
        all_scores.append(qs.score)
        summary.penalty_count += len(p)

    # Sportsbook quality scores
    sb_probs = sources.get("sportsbook_probs", {})
    sb_data = sources.get("sportsbook_data", {})
    sb_sources = len(sb_data.get("normalized_snapshot", {}).get("source_providers", []))
    nv = sb_data.get("no_vig_summary", {})
    avg_overround = nv.get("average_overround", 0.10)
    freshness = sb_data.get("freshness_summary", {})
    stale_count = freshness.get("stale_count", 0)

    for key in sb_probs:
        score = 0.80
        p = []
        if sb_sources < 2:
            score -= penalties.get("single_source", 0.25)
            p.append("single_source")
        if avg_overround > 0.10:
            score -= penalties.get("high_dispersion", 0.15)
            p.append("high_overround")
        if stale_count > 0:
            score -= penalties.get("stale_data", 0.2)
            p.append("stale_data")
        qs = QualityScore(source="sportsbook", key=key, score=round(max(0.1, score), 4), penalties_applied=p)
        qs.quality_level = "high" if qs.score >= high_threshold else ("medium" if qs.score >= medium_threshold else "low")
        summary.scores.append(qs)
        all_scores.append(qs.score)
        summary.penalty_count += len(p)

    # Polymarket quality scores
    pm_probs = sources.get("polymarket_probs", {})
    pm_data = sources.get("polymarket_data", {})
    ds = pm_data.get("discovery_summary", {})
    low_liq_count = 0
    for event in ds.get("events", []):
        for m in event.get("markets", []):
            if m.get("liquidity", 0) < 5000:
                low_liq_count += 1

    for key in pm_probs:
        score = 0.75
        p = []
        if low_liq_count > 5:
            score -= penalties.get("low_liquidity", 0.3)
            p.append("low_liquidity")
        qs = QualityScore(source="polymarket", key=key, score=round(max(0.1, score), 4), penalties_applied=p)
        qs.quality_level = "high" if qs.score >= high_threshold else ("medium" if qs.score >= medium_threshold else "low")
        summary.scores.append(qs)
        all_scores.append(qs.score)
        summary.penalty_count += len(p)

    # Summary stats
    for qs in summary.scores:
        if qs.quality_level == "high":
            summary.high_quality_count += 1
        elif qs.quality_level == "medium":
            summary.medium_quality_count += 1
        else:
            summary.low_quality_count += 1

    summary.average_quality_score = round(sum(all_scores) / len(all_scores), 4) if all_scores else 0

    if summary.low_quality_count > 0:
        summary.warnings.append(f"{summary.low_quality_count} low-quality signals; review penalties before using in strategy.")

    return summary
