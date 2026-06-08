"""Match registry: load and query the 104-match schedule."""

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional


@dataclass
class MatchEntry:
    match_id: str
    match_number: int
    stage: str
    group: Optional[str]
    date: date
    home_team: str
    away_team: str
    venue: str
    venue_city: str
    venue_country: str
    is_knockout: bool
    knockout_round: Optional[str]
    matchday: Optional[int]
    kickoff_slot: Optional[str]


def load_match_registry(path: str) -> list[MatchEntry]:
    """Load match registry from JSON seed data."""
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    matches = []
    for entry in raw:
        m = MatchEntry(
            match_id=entry["match_id"],
            match_number=int(entry["match_number"]),
            stage=entry["stage"],
            group=entry.get("group"),
            date=date.fromisoformat(entry["date"]),
            home_team=entry["home_team"],
            away_team=entry["away_team"],
            venue=entry.get("venue", ""),
            venue_city=entry.get("venue_city", ""),
            venue_country=entry.get("venue_country", ""),
            is_knockout=bool(entry.get("is_knockout", False)),
            knockout_round=entry.get("knockout_round"),
            matchday=entry.get("matchday"),
            kickoff_slot=entry.get("kickoff_slot"),
        )
        matches.append(m)
    validate_match_registry(matches)
    return matches


def validate_match_registry(matches: list[MatchEntry]) -> None:
    """Validate match registry integrity."""
    if len(matches) != 104:
        raise ValueError(
            f"Match registry has {len(matches)} matches, expected 104"
        )
    # Match numbers 1-104 contiguous
    nums = sorted([m.match_number for m in matches])
    if nums != list(range(1, 105)):
        raise ValueError("Match numbers must be 1-104 contiguous")
    # Unique match IDs
    ids = [m.match_id for m in matches]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate match IDs found")
    # Group vs knockout checks
    for m in matches:
        if m.is_knockout and m.group is not None:
            raise ValueError(
                f"Match {m.match_id}: is_knockout=true but has group {m.group}"
            )
        if not m.is_knockout and m.group is None:
            raise ValueError(
                f"Match {m.match_id}: is_knockout=false but no group"
            )
    # Verify counts
    group_count = sum(1 for m in matches if not m.is_knockout)
    ko_count = sum(1 for m in matches if m.is_knockout)
    if group_count != 72:
        raise ValueError(f"Group matches: {group_count}, expected 72")
    if ko_count != 32:
        raise ValueError(f"Knockout matches: {ko_count}, expected 32")


def get_matches_by_date(
    target_date: date, matches: list[MatchEntry]
) -> list[MatchEntry]:
    """Get all matches on a specific date."""
    return [m for m in matches if m.date == target_date]


def get_matches_by_stage(
    stage: str, matches: list[MatchEntry]
) -> list[MatchEntry]:
    """Get all matches in a specific stage."""
    return [m for m in matches if m.stage == stage]


def get_matches_by_group(
    group: str, matches: list[MatchEntry]
) -> list[MatchEntry]:
    """Get all matches for a specific group."""
    return [m for m in matches if m.group == group]


def get_upcoming_matches(
    from_date: date, matches: list[MatchEntry], limit: int = 10
) -> list[MatchEntry]:
    """Get upcoming matches from a given date (inclusive)."""
    upcoming = [m for m in matches if m.date >= from_date]
    upcoming.sort(key=lambda m: (m.date, m.match_number))
    return upcoming[:limit]


def get_remaining_matches(
    from_date: date, matches: list[MatchEntry]
) -> list[MatchEntry]:
    """Get all remaining matches from a given date (inclusive)."""
    remaining = [m for m in matches if m.date >= from_date]
    remaining.sort(key=lambda m: (m.date, m.match_number))
    return remaining


def get_match_count_by_stage(matches: list[MatchEntry]) -> dict[str, int]:
    """Count matches per stage."""
    counts = {}
    for m in matches:
        counts[m.stage] = counts.get(m.stage, 0) + 1
    return counts