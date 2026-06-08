"""Opportunity window: count remaining matches and strategy windows."""

from datetime import date

from worldcup_campaign.match_registry import MatchEntry


def count_effective_windows(
    from_date: date, matches: list[MatchEntry]
) -> int:
    """Count the number of distinct dates with at least one match remaining.

    This represents the number of effective strategy windows left.
    """
    remaining_dates = set()
    for m in matches:
        if m.date >= from_date:
            remaining_dates.add(m.date)
    return len(remaining_dates)


def count_remaining_matches(
    from_date: date, matches: list[MatchEntry]
) -> int:
    """Count total matches remaining from a given date (inclusive)."""
    return sum(1 for m in matches if m.date >= from_date)


def get_remaining_matches_by_stage(
    from_date: date, matches: list[MatchEntry]
) -> dict[str, int]:
    """Count remaining matches grouped by stage."""
    counts = {}
    for m in matches:
        if m.date >= from_date:
            counts[m.stage] = counts.get(m.stage, 0) + 1
    return counts