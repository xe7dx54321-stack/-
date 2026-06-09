"""No-vig calculator: removes overround/vig from bookmaker odds to derive true market probability."""
from dataclasses import dataclass, field


@dataclass
class NoVigMarket:
    match_id: str = ""
    market_type: str = ""
    source_provider: str = ""
    selections: list = field(default_factory=list)
    raw_overround: float = 0.0
    no_vig_probabilities: dict = field(default_factory=dict)
    method: str = "multiplicative"


@dataclass
class NoVigSummary:
    markets: list = field(default_factory=list)
    market_count: int = 0
    average_overround: float = 0.0
    max_overround: float = 0.0
    high_overround_count: int = 0
    warnings: list = field(default_factory=list)


def calculate_overround(odds_list: list) -> float:
    if not odds_list:
        return 0.0
    implied_sum = sum(1.0 / o for o in odds_list if o > 0)
    return max(0.0, implied_sum - 1.0)


def calculate_no_vig_probabilities(odds_list: list, method: str = "multiplicative") -> list:
    if not odds_list:
        return []
    implied = [1.0 / o if o > 0 else 0.0 for o in odds_list]
    total_implied = sum(implied)
    if total_implied <= 0:
        return [0.0] * len(odds_list)

    if method == "multiplicative":
        return [p / total_implied for p in implied]
    elif method == "additive":
        overround = total_implied - 1.0
        n = len(odds_list)
        return [p - overround / n for p in implied]
    else:
        return [p / total_implied for p in implied]


def build_no_vig_markets(normalized_snapshot, config: dict = None) -> NoVigSummary:
    config = config or {}
    max_overround = config.get("overround_policy", {}).get("max_overround", 0.15)
    warn_overround = config.get("overround_policy", {}).get("warn_overround", 0.08)

    summary = NoVigSummary()

    # Group by match_id + market_type + source_provider
    groups = {}
    for entry in normalized_snapshot.entries:
        key = (entry.match_id, entry.market_type, entry.source_provider)
        if key not in groups:
            groups[key] = []
        groups[key].append(entry)

    for (match_id, market_type, provider), entries in groups.items():
        odds_list = [e.decimal_odds for e in entries]
        overround = calculate_overround(odds_list)
        no_vig_probs = calculate_no_vig_probabilities(odds_list)

        market = NoVigMarket(
            match_id=match_id,
            market_type=market_type,
            source_provider=provider,
            selections=[{
                "selection_id": e.selection_id,
                "selection_label": e.selection_label,
                "decimal_odds": e.decimal_odds,
                "raw_implied": round(1.0 / e.decimal_odds, 6) if e.decimal_odds > 0 else 0,
                "no_vig_probability": round(no_vig_probs[i], 6) if i < len(no_vig_probs) else 0,
            } for i, e in enumerate(entries)],
            raw_overround=round(overround, 6),
            no_vig_probabilities={e.selection_id: round(no_vig_probs[i], 6) for i, e in enumerate(entries) if i < len(no_vig_probs)},
        )
        summary.markets.append(market)

        if overround > warn_overround:
            summary.warnings.append(
                f"High overround {overround:.3f} for {match_id}/{market_type}/{provider} (warn threshold: {warn_overround})"
            )
        if overround > max_overround:
            summary.high_overround_count += 1

    summary.market_count = len(summary.markets)
    if summary.markets:
        summary.average_overround = round(sum(m.raw_overround for m in summary.markets) / len(summary.markets), 6)
        summary.max_overround = round(max(m.raw_overround for m in summary.markets), 6)

    return summary
