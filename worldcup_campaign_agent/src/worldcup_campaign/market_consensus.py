"""Market consensus: analyzes agreement/disagreement across multiple odds sources."""
from dataclasses import dataclass, field


@dataclass
class ConsensusMarket:
    match_id: str = ""
    market_type: str = ""
    source_count: int = 0
    consensus_level: str = "insufficient_data"
    average_odds: dict = field(default_factory=dict)
    min_odds: dict = field(default_factory=dict)
    max_odds: dict = field(default_factory=dict)
    dispersion: dict = field(default_factory=dict)
    no_vig_consensus: dict = field(default_factory=dict)


@dataclass
class ConsensusSummary:
    markets: list = field(default_factory=list)
    market_count: int = 0
    strong_consensus_count: int = 0
    usable_consensus_count: int = 0
    weak_consensus_count: int = 0
    dispersion_warning_count: int = 0
    warnings: list = field(default_factory=list)


def _classify_consensus_strength(source_count: int, max_dispersion: float,
                                  min_for_strong: int, min_for_usable: int,
                                  strong_threshold: float, usable_threshold: float,
                                  dispersion_warn: float) -> str:
    """Classify consensus strength based on source count and dispersion."""
    if source_count < min_for_usable:
        return "weak"
    if max_dispersion > dispersion_warn:
        return "weak"  # Force downgrade on high dispersion
    if source_count >= min_for_strong and max_dispersion <= strong_threshold:
        return "strong"
    if source_count >= min_for_usable and max_dispersion <= usable_threshold:
        return "usable"
    return "weak"


def build_market_consensus(normalized_snapshot, no_vig_summary, config: dict = None) -> ConsensusSummary:
    config = config or {}
    consensus_cfg = config.get("consensus", {})
    min_sources = consensus_cfg.get("min_sources_for_consensus", 2)
    min_for_strong = consensus_cfg.get("min_sources_for_strong_consensus", 3)
    min_for_usable = consensus_cfg.get("min_sources_for_usable_consensus", 2)
    strong_threshold = consensus_cfg.get("strong_consensus_threshold", 0.03)
    usable_threshold = consensus_cfg.get("usable_consensus_threshold", 0.08)
    weak_threshold = consensus_cfg.get("weak_consensus_threshold", 0.08)
    dispersion_threshold = consensus_cfg.get("dispersion_warning_threshold", 0.12)

    summary = ConsensusSummary()

    # Group by match_id + market_type across providers
    groups = {}
    for entry in normalized_snapshot.entries:
        key = (entry.match_id, entry.market_type)
        if key not in groups:
            groups[key] = {}
        sel_key = entry.selection_id
        if sel_key not in groups[key]:
            groups[key][sel_key] = []
        groups[key][sel_key].append(entry)

    for (match_id, market_type), selections in groups.items():
        source_providers = set()
        for sel_entries in selections.values():
            for e in sel_entries:
                source_providers.add(e.source_provider)

        source_count = len(source_providers)
        if source_count < min_sources:
            summary.markets.append(ConsensusMarket(
                match_id=match_id, market_type=market_type,
                source_count=source_count, consensus_level="insufficient_data",
            ))
            continue

        avg_odds = {}
        min_odds = {}
        max_odds = {}
        dispersion = {}

        for sel_id, sel_entries in selections.items():
            odds_vals = [e.decimal_odds for e in sel_entries]
            avg_odds[sel_id] = round(sum(odds_vals) / len(odds_vals), 4)
            min_odds[sel_id] = round(min(odds_vals), 4)
            max_odds[sel_id] = round(max(odds_vals), 4)
            if avg_odds[sel_id] > 0:
                dispersion[sel_id] = round((max_odds[sel_id] - min_odds[sel_id]) / avg_odds[sel_id], 6)
            else:
                dispersion[sel_id] = 0.0

        max_dispersion = max(dispersion.values()) if dispersion else 0.0

        consensus_level = _classify_consensus_strength(
            source_count, max_dispersion,
            min_for_strong, min_for_usable,
            strong_threshold, usable_threshold,
            dispersion_threshold
        )

        if consensus_level == "strong":
            summary.strong_consensus_count += 1
        elif consensus_level == "usable":
            summary.usable_consensus_count += 1
        elif consensus_level == "weak":
            summary.weak_consensus_count += 1

        if max_dispersion > dispersion_threshold:
            summary.dispersion_warning_count += 1
            summary.warnings.append(
                f"High dispersion ({max_dispersion:.3f}) for {match_id}/{market_type} across {source_count} sources"
            )

        # Build no-vig consensus from providers
        no_vig_consensus = {}
        for nv_market in no_vig_summary.markets:
            if nv_market.match_id == match_id and nv_market.market_type == market_type:
                for sel_id, prob in nv_market.no_vig_probabilities.items():
                    if sel_id not in no_vig_consensus:
                        no_vig_consensus[sel_id] = []
                    no_vig_consensus[sel_id].append(prob)

        avg_no_vig = {}
        for sel_id, probs in no_vig_consensus.items():
            avg_no_vig[sel_id] = round(sum(probs) / len(probs), 6) if probs else 0

        summary.markets.append(ConsensusMarket(
            match_id=match_id, market_type=market_type,
            source_count=source_count, consensus_level=consensus_level,
            average_odds=avg_odds, min_odds=min_odds, max_odds=max_odds,
            dispersion=dispersion, no_vig_consensus=avg_no_vig,
        ))

    summary.market_count = len(summary.markets)
    return summary
