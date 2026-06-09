"""Polymarket gap analysis: sportsbook vs Polymarket vs model probability gaps."""
from dataclasses import dataclass, field


@dataclass
class GapRecord:
    record_id: str = ""
    team_or_event: str = ""
    model_probability: float = 0.0
    sportsbook_implied: float = 0.0
    polymarket_probability: float = 0.0
    model_vs_polymarket_gap: float = 0.0
    sportsbook_vs_polymarket_gap: float = 0.0
    gap_direction: str = "aligned"
    liquidity_level: str = "unknown"
    is_major_disagreement: bool = False


@dataclass
class GapSummary:
    records: list = field(default_factory=list)
    gap_record_count: int = 0
    model_above_polymarket_count: int = 0
    model_below_polymarket_count: int = 0
    sportsbook_above_polymarket_count: int = 0
    sportsbook_below_polymarket_count: int = 0
    major_disagreement_count: int = 0
    low_liquidity_gap_count: int = 0
    warnings: list = field(default_factory=list)


def analyze_polymarket_gaps(
    discovery_summary,
    signal_summary,
    consensus_summary,
    market_odds_data: dict = None,
    model_data: dict = None,
    config: dict = None
) -> GapSummary:
    config = config or {}
    major_threshold = config.get("gap_analysis", {}).get("major_disagreement_threshold", 0.15)
    minor_threshold = config.get("gap_analysis", {}).get("minor_disagreement_threshold", 0.05)

    summary = GapSummary()

    # Build sportsbook lookup
    sportsbook_probs = {}
    if market_odds_data:
        nv = market_odds_data.get("no_vig_summary", {})
        for m in nv.get("markets", []):
            for sel_id, prob in m.get("no_vig_probabilities", {}).items():
                key = f"{m.get('match_id','')}_{sel_id}"
                sportsbook_probs[key] = prob

    # Build model lookup
    model_probs = {}
    if model_data:
        for m in model_data.get("matches", []):
            mid = m.get("match_id", "")
            for sel, field in [("H", "home_win_prob"), ("D", "draw_prob"), ("A", "away_win_prob")]:
                val = m.get(field)
                if val is not None:
                    model_probs[f"{mid}_{sel}"] = float(val)

    # Cross-reference polymarket markets with sportsbook/model
    for event in discovery_summary.events:
        if not event.is_relevant:
            continue

        for market in event.markets:
            if market.is_deferred:
                continue

            pm_prob = market.last_price
            team = market.market_id.replace("pm_winner_", "").replace("pm_final_", "").replace("pm_gc_", "")
            liq_level = "high" if market.liquidity >= 100000 else ("medium" if market.liquidity >= 10000 else "low")

            # Find matching sportsbook/model probabilities
            sb_prob = 0.0
            md_prob = 0.0
            for key_prefix, prob_map in [("sb", sportsbook_probs), ("md", model_probs)]:
                for key, prob in prob_map.items():
                    if team.lower() in key.lower() or key.lower() in team.lower():
                        if key_prefix == "sb":
                            sb_prob = max(sb_prob, prob)
                        else:
                            md_prob = max(md_prob, prob)

            model_vs_pm = md_prob - pm_prob if md_prob > 0 else 0
            sb_vs_pm = sb_prob - pm_prob if sb_prob > 0 else 0

            # Determine gap direction
            max_abs_gap = max(abs(model_vs_pm), abs(sb_vs_pm))
            if max_abs_gap < minor_threshold:
                direction = "aligned"
            elif model_vs_pm > 0 or sb_vs_pm > 0:
                direction = "above_polymarket"
            else:
                direction = "below_polymarket"

            is_major = max_abs_gap >= major_threshold
            is_low_liq = liq_level == "low"

            record = GapRecord(
                record_id=market.market_id,
                team_or_event=team,
                model_probability=round(md_prob, 6),
                sportsbook_implied=round(sb_prob, 6),
                polymarket_probability=round(pm_prob, 6),
                model_vs_polymarket_gap=round(model_vs_pm, 6),
                sportsbook_vs_polymarket_gap=round(sb_vs_pm, 6),
                gap_direction=direction,
                liquidity_level=liq_level,
                is_major_disagreement=is_major,
            )
            summary.records.append(record)
            summary.gap_record_count += 1

            if model_vs_pm > minor_threshold:
                summary.model_above_polymarket_count += 1
            elif model_vs_pm < -minor_threshold:
                summary.model_below_polymarket_count += 1
            if sb_vs_pm > minor_threshold:
                summary.sportsbook_above_polymarket_count += 1
            elif sb_vs_pm < -minor_threshold:
                summary.sportsbook_below_polymarket_count += 1
            if is_major:
                summary.major_disagreement_count += 1
            if is_low_liq and is_major:
                summary.low_liquidity_gap_count += 1

    if summary.gap_record_count == 0:
        summary.warnings.append("No gap records generated; sportsbook/model data may not overlap with Polymarket events.")

    return summary
