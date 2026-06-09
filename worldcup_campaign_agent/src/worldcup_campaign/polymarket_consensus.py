"""Polymarket consensus: prediction market agreement analysis."""
from dataclasses import dataclass, field


@dataclass
class PredictionConsensus:
    event_id: str = ""
    event_title: str = ""
    outcome_count: int = 0
    consensus_probability: float = 0.0
    price_range_min: float = 0.0
    price_range_max: float = 0.0
    dispersion: float = 0.0
    consensus_level: str = "insufficient_data"


@dataclass
class ConsensusSummary:
    consensus_records: list = field(default_factory=list)
    prediction_consensus_count: int = 0
    strong_consensus_count: int = 0
    usable_consensus_count: int = 0
    warnings: list = field(default_factory=list)


def build_polymarket_consensus(discovery_summary, config: dict) -> ConsensusSummary:
    consensus_cfg = config.get("consensus", {})
    strong_threshold = consensus_cfg.get("strong_consensus_threshold", 0.03)
    usable_threshold = consensus_cfg.get("usable_consensus_threshold", 0.08)

    summary = ConsensusSummary()

    for event in discovery_summary.events:
        if not event.is_relevant:
            continue
        if not event.markets:
            continue

        prices = [m.last_price for m in event.markets]
        if len(prices) < 2:
            continue

        price_range_min = min(prices)
        price_range_max = max(prices)
        avg_price = sum(prices) / len(prices)
        dispersion = round((price_range_max - price_range_min) / avg_price, 6) if avg_price > 0 else 0

        if dispersion <= strong_threshold:
            level = "strong"
            summary.strong_consensus_count += 1
        elif dispersion <= usable_threshold:
            level = "usable"
            summary.usable_consensus_count += 1
        else:
            level = "weak"

        pc = PredictionConsensus(
            event_id=event.event_id,
            event_title=event.title,
            outcome_count=len(prices),
            consensus_probability=round(avg_price, 6),
            price_range_min=round(price_range_min, 4),
            price_range_max=round(price_range_max, 4),
            dispersion=dispersion,
            consensus_level=level,
        )
        summary.consensus_records.append(pc)
        summary.prediction_consensus_count += 1

    return summary
