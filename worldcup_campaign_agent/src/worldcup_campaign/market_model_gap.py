"""Market model gap: compares model probabilities against market implied probabilities."""
from dataclasses import dataclass, field


@dataclass
class GapRecord:
    match_id: str = ""
    market_type: str = ""
    selection_id: str = ""
    model_probability: float = 0.0
    market_implied_probability: float = 0.0
    gap: float = 0.0
    direction: str = "aligned"


@dataclass
class ModelMarketGapSummary:
    records: list = field(default_factory=list)
    record_count: int = 0
    model_above_market_count: int = 0
    model_below_market_count: int = 0
    aligned_count: int = 0
    average_gap: float = 0.0
    warnings: list = field(default_factory=list)


# Selection ID normalization: odds selection_id -> model probability field name
SELECTION_NORMALIZATION = {
    "H": ["home_win_prob", "home_probability", "home", "H"],
    "D": ["draw_prob", "draw_probability", "draw", "D"],
    "A": ["away_win_prob", "away_probability", "away", "A"],
    "HOME": ["home_win_prob", "home_probability", "home", "H"],
    "DRAW": ["draw_prob", "draw_probability", "draw", "D"],
    "AWAY": ["away_win_prob", "away_probability", "away", "A"],
    "home": ["home_win_prob", "home_probability"],
    "draw": ["draw_prob", "draw_probability"],
    "away": ["away_win_prob", "away_probability"],
}


def _normalize_selection_id(sel_id: str) -> str:
    """Map various selection_id forms to canonical (H, D, A)."""
    upper = sel_id.upper().strip()
    if upper in ("H", "HOME", "1", "HOME_WIN"):
        return "H"
    if upper in ("D", "DRAW", "X", "DRAW_WIN"):
        return "D"
    if upper in ("A", "AWAY", "2", "AWAY_WIN"):
        return "A"
    return sel_id


def _get_model_prob(match_data: dict, market_type: str, selection_id: str) -> float:
    """Extract model probability from match data for a given market type and selection."""
    canonical = _normalize_selection_id(selection_id)

    # Direct fields on match_data for 1X2
    if market_type == "1X2" or market_type == "1x2":
        field_map = {"H": "home_win_prob", "D": "draw_prob", "A": "away_win_prob"}
        field = field_map.get(canonical)
        if field and field in match_data:
            return float(match_data[field])

    # Check nested probabilities
    probs = match_data.get("probabilities", match_data.get("market_probabilities", {}))
    if isinstance(probs, dict):
        market_probs = probs.get(market_type, probs)
        if isinstance(market_probs, dict):
            # Try canonical first
            for key in [canonical, selection_id, selection_id.upper(), selection_id.lower()]:
                if key in market_probs:
                    return float(market_probs[key])
            # Try selections nested
            selections = market_probs.get("selections", market_probs.get("outcomes", {}))
            if isinstance(selections, dict):
                for key in [canonical, selection_id]:
                    val = selections.get(key, None)
                    if val is not None:
                        if isinstance(val, dict):
                            return float(val.get("probability", 0))
                        return float(val)

    return None


def compute_model_vs_market_gap(
    normalized_snapshot,
    match_probability_preview: dict,
    config: dict = None
) -> ModelMarketGapSummary:
    config = config or {}
    summary = ModelMarketGapSummary()

    # Build model probability lookup
    model_probs = {}
    matches = match_probability_preview.get("matches", match_probability_preview.get("match_previews", []))
    if not isinstance(matches, list):
        matches = []

    for m in matches:
        if not isinstance(m, dict):
            continue
        match_id = m.get("match_id", m.get("id", ""))

        # Extract all 1X2 probabilities
        for sel_canon, field in [("H", "home_win_prob"), ("D", "draw_prob"), ("A", "away_win_prob")]:
            val = m.get(field)
            if val is not None:
                model_probs[(match_id, "1X2", sel_canon)] = float(val)

        # Also check alternative field names
        for sel_canon, fields in [("H", ["home_probability"]), ("D", ["draw_probability"]), ("A", ["away_probability"])]:
            for f in fields:
                val = m.get(f)
                if val is not None and (match_id, "1X2", sel_canon) not in model_probs:
                    model_probs[(match_id, "1X2", sel_canon)] = float(val)

    # Compute gaps
    for entry in normalized_snapshot.entries:
        if entry.market_type not in ("1X2", "1x2"):
            continue

        canonical = _normalize_selection_id(entry.selection_id)
        key = (entry.match_id, "1X2", canonical)
        model_prob = model_probs.get(key)

        if model_prob is None:
            # Try with original selection_id
            key2 = (entry.match_id, "1X2", entry.selection_id)
            model_prob = model_probs.get(key2)

        if model_prob is None:
            continue

        market_implied = 1.0 / entry.decimal_odds if entry.decimal_odds > 0 else 0.0
        gap = model_prob - market_implied
        abs_gap = abs(gap)
        if abs_gap < 0.03:
            direction = "aligned"
        elif gap > 0:
            direction = "model_above"
        else:
            direction = "model_below"

        record = GapRecord(
            match_id=entry.match_id,
            market_type=entry.market_type,
            selection_id=entry.selection_id,
            model_probability=round(model_prob, 6),
            market_implied_probability=round(market_implied, 6),
            gap=round(gap, 6),
            direction=direction,
        )
        summary.records.append(record)

        if direction == "model_above":
            summary.model_above_market_count += 1
        elif direction == "model_below":
            summary.model_below_market_count += 1
        else:
            summary.aligned_count += 1

    summary.record_count = len(summary.records)
    if summary.records:
        summary.average_gap = round(sum(abs(r.gap) for r in summary.records) / len(summary.records), 6)

    if summary.model_above_market_count > summary.model_below_market_count * 2 and summary.record_count >= 4:
        summary.warnings.append(
            f"Model tends to be above market ({summary.model_above_market_count} vs {summary.model_below_market_count} below). "
            "Check for systematic probability overestimation."
        )

    return summary
