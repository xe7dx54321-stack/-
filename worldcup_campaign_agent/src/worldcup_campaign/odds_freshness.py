"""Odds freshness: timestamp-based freshness guard for odds snapshots."""
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class FreshnessRecord:
    source_provider: str = ""
    latest_timestamp: str = ""
    age_hours: float = 0.0
    is_fresh: bool = True
    is_stale: bool = False


@dataclass
class FreshnessSummary:
    records: list = field(default_factory=list)
    fresh_count: int = 0
    stale_count: int = 0
    oldest_age_hours: float = 0.0
    freshness_warning_count: int = 0
    warnings: list = field(default_factory=list)


def _parse_timestamp_naive(ts: str) -> datetime:
    """Parse an ISO timestamp and return a timezone-naive datetime."""
    s = ts.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=None)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc).replace(tzinfo=None)


def check_odds_freshness(
    normalized_snapshot,
    config: dict = None,
    reference_time: str = None
) -> FreshnessSummary:
    config = config or {}
    max_age = config.get("freshness", {}).get("max_age_hours", 24)
    warn_age = config.get("freshness", {}).get("warn_age_hours", 8)
    stale_age = config.get("freshness", {}).get("stale_age_hours", 48)

    summary = FreshnessSummary()

    if reference_time is not None:
        ref_dt = _parse_timestamp_naive(reference_time)
    else:
        ref_dt = datetime.now(timezone.utc).replace(tzinfo=None)

    provider_latest = {}
    for entry in normalized_snapshot.entries:
        if not entry.snapshot_timestamp:
            continue
        provider = entry.source_provider
        ts = entry.snapshot_timestamp
        if provider not in provider_latest or ts > provider_latest[provider]:
            provider_latest[provider] = ts

    if not provider_latest:
        summary.warnings.append("No timestamped odds entries; cannot assess freshness.")
        return summary

    for provider, ts_str in provider_latest.items():
        ts_dt = _parse_timestamp_naive(ts_str)
        age = (ref_dt - ts_dt).total_seconds() / 3600.0
        is_fresh = age <= max_age
        is_stale = age > stale_age

        record = FreshnessRecord(
            source_provider=provider,
            latest_timestamp=ts_str,
            age_hours=round(age, 2),
            is_fresh=is_fresh,
            is_stale=is_stale,
        )
        summary.records.append(record)

        if is_fresh:
            summary.fresh_count += 1
        if is_stale:
            summary.stale_count += 1
            summary.warnings.append(f"Provider '{provider}' odds are stale ({age:.1f}h old, threshold: {stale_age}h)")
        elif age > warn_age:
            summary.freshness_warning_count += 1
            summary.warnings.append(f"Provider '{provider}' odds are aging ({age:.1f}h, warn threshold: {warn_age}h)")

        if age > summary.oldest_age_hours:
            summary.oldest_age_hours = round(age, 2)

    return summary
