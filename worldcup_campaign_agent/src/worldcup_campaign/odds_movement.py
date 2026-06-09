"""Odds movement: tracks line movement between snapshot types (opening -> current)."""
from dataclasses import dataclass, field


@dataclass
class MovementRecord:
    match_id: str = ""
    market_type: str = ""
    selection_id: str = ""
    opening_odds: float = 0.0
    current_odds: float = 0.0
    movement_pct: float = 0.0
    direction: str = "stable"
    is_significant: bool = False


@dataclass
class MovementSummary:
    records: list = field(default_factory=list)
    record_count: int = 0
    significant_move_count: int = 0
    insufficient_history_count: int = 0
    warnings: list = field(default_factory=list)


def analyze_odds_movement(
    normalized_snapshot,
    config: dict = None
) -> MovementSummary:
    config = config or {}
    sig_threshold = config.get("movement", {}).get("significant_move_threshold", 0.05)

    summary = MovementSummary()

    # Need opening and current snapshots
    opening_entries = {}
    current_entries = {}

    for entry in normalized_snapshot.entries:
        key = (entry.match_id, entry.market_type, entry.selection_id, entry.source_provider)
        if entry.snapshot_type == "opening":
            opening_entries[key] = entry
        else:
            current_entries[key] = entry

    if not opening_entries:
        summary.insufficient_history_count = len(current_entries)
        summary.warnings.append("No opening odds available for movement analysis; need historical snapshots.")
        return summary

    for key, current in current_entries.items():
        opening = opening_entries.get(key)
        if not opening:
            continue

        if opening.decimal_odds <= 0 or current.decimal_odds <= 0:
            continue

        movement_pct = (current.decimal_odds - opening.decimal_odds) / opening.decimal_odds
        direction = "steam" if movement_pct < -0.01 else ("drift" if movement_pct > 0.01 else "stable")
        is_sig = abs(movement_pct) >= sig_threshold

        record = MovementRecord(
            match_id=current.match_id,
            market_type=current.market_type,
            selection_id=current.selection_id,
            opening_odds=round(opening.decimal_odds, 4),
            current_odds=round(current.decimal_odds, 4),
            movement_pct=round(movement_pct, 6),
            direction=direction,
            is_significant=is_sig,
        )
        summary.records.append(record)
        if is_sig:
            summary.significant_move_count += 1

    summary.record_count = len(summary.records)
    return summary
