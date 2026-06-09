"""Blended probability: weighted fusion of model, sportsbook, and polymarket probabilities."""
from dataclasses import dataclass, field


@dataclass
class BlendedRecord:
    key: str = ""
    model_prob: float = 0.0
    sportsbook_prob: float = 0.0
    polymarket_prob: float = 0.0
    blended_probability: float = 0.0
    model_weight: float = 0.0
    sportsbook_weight: float = 0.0
    polymarket_weight: float = 0.0


@dataclass
class BlendedSummary:
    records: list = field(default_factory=list)
    blended_record_count: int = 0
    average_model_weight: float = 0.0
    average_sportsbook_weight: float = 0.0
    average_polymarket_weight: float = 0.0
    warnings: list = field(default_factory=list)


def compute_blended_probability(sources: dict, quality_summary, config: dict = None) -> BlendedSummary:
    config = config or {}
    bl_cfg = config.get("blending", {})
    default_weights = bl_cfg.get("default_weights", {"model": 0.35, "sportsbook": 0.35, "polymarket": 0.30})
    liq_penalty = bl_cfg.get("liquidity_penalty_multiplier", 0.5)
    freshness_penalty = bl_cfg.get("freshness_penalty_multiplier", 0.7)
    low_source_penalty = bl_cfg.get("low_source_penalty_multiplier", 0.6)
    min_w = bl_cfg.get("min_weight", 0.1)
    max_w = bl_cfg.get("max_weight", 0.6)

    model_probs = sources.get("model_probs", {})
    sb_probs = sources.get("sportsbook_probs", {})
    pm_probs = sources.get("polymarket_probs", {})

    # Build quality lookup
    quality_lookup = {}
    for qs in quality_summary.scores:
        if qs.score > 0:
            quality_lookup[(qs.source, qs.key)] = qs.score

    # Determine source-level adjustments
    sb_sources = len(sources.get("sportsbook_data", {}).get("normalized_snapshot", {}).get("source_providers", []))
    freshness = sources.get("sportsbook_data", {}).get("freshness_summary", {})
    stale_count = freshness.get("stale_count", 0)

    summary = BlendedSummary()
    all_keys = set(list(model_probs.keys()) + list(sb_probs.keys()) + list(pm_probs.keys()))

    model_w_sum = 0; sb_w_sum = 0; pm_w_sum = 0; count = 0

    for key in sorted(all_keys):
        mw = default_weights["model"]
        sw = default_weights["sportsbook"]
        pw = default_weights["polymarket"]

        # Adjust based on quality
        mq = quality_lookup.get(("model", key), 0.5)
        sq = quality_lookup.get(("sportsbook", key), 0.5)
        pq = quality_lookup.get(("polymarket", key), 0.5)

        mw *= (0.5 + 0.5 * mq)
        sw *= (0.5 + 0.5 * sq)
        pw *= (0.5 + 0.5 * pq)

        # Source-level adjustments
        if sb_sources < 2:
            sw *= low_source_penalty
        if stale_count > 0:
            sw *= freshness_penalty

        # Normalize
        total_w = mw + sw + pw
        if total_w > 0:
            mw = max(min_w, min(max_w, mw / total_w))
            sw = max(min_w, min(max_w, sw / total_w))
            pw = max(min_w, min(max_w, pw / total_w))

        total_w2 = mw + sw + pw
        mw /= total_w2; sw /= total_w2; pw /= total_w2

        mp = model_probs.get(key, 0)
        sp = sb_probs.get(key, 0)
        pp = pm_probs.get(key, 0)

        blended = mp * mw + sp * sw + pp * pw

        record = BlendedRecord(
            key=key, model_prob=round(mp, 6),
            sportsbook_prob=round(sp, 6), polymarket_prob=round(pp, 6),
            blended_probability=round(blended, 6),
            model_weight=round(mw, 4), sportsbook_weight=round(sw, 4),
            polymarket_weight=round(pw, 4),
        )
        summary.records.append(record)
        summary.blended_record_count += 1
        model_w_sum += mw; sb_w_sum += sw; pm_w_sum += pw; count += 1

    if count > 0:
        summary.average_model_weight = round(model_w_sum / count, 4)
        summary.average_sportsbook_weight = round(sb_w_sum / count, 4)
        summary.average_polymarket_weight = round(pm_w_sum / count, 4)

    return summary
