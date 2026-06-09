"""Odds normalizer: standardizes odds entries to uniform schema."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NormalizedOddsEntry:
    match_id: str = ""
    market_type: str = ""
    selection_id: str = ""
    selection_label: str = ""
    decimal_odds: float = 1.0
    implied_probability: float = 0.0
    source_provider: str = ""
    snapshot_type: str = "current"
    snapshot_timestamp: str = ""
    is_valid: bool = True
    validation_warning: str = ""


@dataclass
class NormalizedOddsSnapshot:
    snapshot_date: str = ""
    source_providers: list = field(default_factory=list)
    snapshot_type: str = "current"
    entries: list = field(default_factory=list)
    raw_count: int = 0
    normalized_count: int = 0
    invalid_count: int = 0
    warnings: list = field(default_factory=list)


def normalize_odds_entries(raw_entries: list, config: dict = None) -> NormalizedOddsSnapshot:
    config = config or {}
    odds_range = config.get("decimal_odds_range", {"min": 1.01, "max": 1001.0})
    allowed_markets = config.get("allowed_market_types", ["1X2", "over_under", "handicap", "correct_score", "both_to_score", "draw_no_bet"])

    snapshot = NormalizedOddsSnapshot(raw_count=len(raw_entries))
    providers = set()

    for entry in raw_entries:
        match_id = getattr(entry, "match_id", entry.get("match_id", "")) if isinstance(entry, dict) else entry.match_id
        market_type = getattr(entry, "market_type", entry.get("market_type", "")) if isinstance(entry, dict) else entry.market_type
        selection_id = getattr(entry, "selection_id", entry.get("selection_id", "")) if isinstance(entry, dict) else entry.selection_id
        selection_label = getattr(entry, "selection_label", entry.get("selection_label", "")) if isinstance(entry, dict) else entry.selection_label
        decimal_odds = getattr(entry, "decimal_odds", entry.get("decimal_odds", 1.0)) if isinstance(entry, dict) else entry.decimal_odds
        source_provider = getattr(entry, "source_provider", entry.get("source_provider", "")) if isinstance(entry, dict) else entry.source_provider
        snapshot_type = getattr(entry, "snapshot_type", entry.get("snapshot_type", "current")) if isinstance(entry, dict) else entry.snapshot_type
        snapshot_timestamp = getattr(entry, "snapshot_timestamp", entry.get("snapshot_timestamp", "")) if isinstance(entry, dict) else entry.snapshot_timestamp

        decimal_odds = float(decimal_odds)
        is_valid = True
        warnings = []

        if decimal_odds < odds_range["min"] or decimal_odds > odds_range["max"]:
            is_valid = False
            warnings.append(f"Odds {decimal_odds} outside range [{odds_range['min']}, {odds_range['max']}]")

        if market_type not in allowed_markets:
            warnings.append(f"Market type '{market_type}' not in allowed list")

        implied_prob = 1.0 / decimal_odds if decimal_odds > 0 else 0.0

        normalized = NormalizedOddsEntry(
            match_id=match_id,
            market_type=market_type,
            selection_id=selection_id,
            selection_label=selection_label,
            decimal_odds=decimal_odds,
            implied_probability=round(implied_prob, 6),
            source_provider=source_provider,
            snapshot_type=snapshot_type,
            snapshot_timestamp=snapshot_timestamp,
            is_valid=is_valid,
            validation_warning="; ".join(warnings) if warnings else "",
        )
        snapshot.entries.append(normalized)
        if source_provider:
            providers.add(source_provider)

    snapshot.normalized_count = sum(1 for e in snapshot.entries if e.is_valid)
    snapshot.invalid_count = snapshot.raw_count - snapshot.normalized_count
    snapshot.source_providers = list(providers)
    if snapshot.entries:
        snapshot.snapshot_date = snapshot.entries[0].snapshot_timestamp[:10] if snapshot.entries[0].snapshot_timestamp else ""

    return snapshot
