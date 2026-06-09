"""Odds source adapter: multi-source odds retrieval (manual CSV/JSON, optional API)."""
import json, csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from datetime import datetime


@dataclass
class OddsEntry:
    match_id: str = ""
    market_type: str = ""
    selection_id: str = ""
    selection_label: str = ""
    decimal_odds: float = 1.0
    source_provider: str = ""
    snapshot_type: str = "current"
    snapshot_timestamp: str = ""


@dataclass
class OddsSnapshot:
    snapshot_date: str = ""
    source_providers: list = field(default_factory=list)
    snapshot_type: str = "current"
    entries: list = field(default_factory=list)
    loaded_from: str = ""
    warnings: list = field(default_factory=list)
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


def load_odds_from_csv(path: str) -> OddsSnapshot:
    snapshot = OddsSnapshot(loaded_from=path)
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entry = OddsEntry(
                    match_id=row.get("match_id", ""),
                    market_type=row.get("market_type", ""),
                    selection_id=row.get("selection_id", ""),
                    selection_label=row.get("selection_label", ""),
                    decimal_odds=float(row.get("decimal_odds", 1.0)),
                    source_provider=row.get("source_provider", ""),
                    snapshot_type=row.get("snapshot_type", "current"),
                    snapshot_timestamp=row.get("snapshot_timestamp", ""),
                )
                snapshot.entries.append(entry)
                if entry.source_provider not in snapshot.source_providers:
                    snapshot.source_providers.append(entry.source_provider)
        if snapshot.entries:
            first_ts = snapshot.entries[0].snapshot_timestamp
            snapshot.snapshot_date = first_ts[:10] if first_ts else ""
    except Exception as e:
        snapshot.warnings.append(f"CSV load error: {e}")
    return snapshot


def load_odds_from_json(path: str) -> OddsSnapshot:
    snapshot = OddsSnapshot(loaded_from=path)
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        snapshot.snapshot_date = data.get("snapshot_date", "")
        snapshot.snapshot_type = data.get("snapshot_type", "current")
        for e in data.get("entries", []):
            entry = OddsEntry(
                match_id=e.get("match_id", ""),
                market_type=e.get("market_type", ""),
                selection_id=e.get("selection_id", ""),
                selection_label=e.get("selection_label", ""),
                decimal_odds=float(e.get("decimal_odds", 1.0)),
                source_provider=e.get("source_provider", ""),
                snapshot_type=e.get("snapshot_type", data.get("snapshot_type", "current")),
                snapshot_timestamp=e.get("snapshot_timestamp", ""),
            )
            snapshot.entries.append(entry)
            if entry.source_provider not in snapshot.source_providers:
                snapshot.source_providers.append(entry.source_provider)
        snapshot.source_providers = data.get("source_providers", snapshot.source_providers)
    except Exception as e:
        snapshot.warnings.append(f"JSON load error: {e}")
    return snapshot


def load_synthetic_odds_from_ev_ranking(ev_ranking_preview: dict, match_probability_preview: dict = None) -> OddsSnapshot:
    """Generate synthetic odds snapshot from EV ranking output (fallback when no real odds)."""
    snapshot = OddsSnapshot(
        snapshot_date=ev_ranking_preview.get("date", ""),
        snapshot_type="synthetic",
        loaded_from="synthetic_from_ev_ranking",
    )
    snapshot.source_providers = ["synthetic_model"]
    candidates = ev_ranking_preview.get("candidates", ev_ranking_preview.get("ranked_candidates", []))
    for c in candidates if isinstance(candidates, list) else []:
        entry = OddsEntry(
            match_id=c.get("match_id", ""),
            market_type=c.get("market_type", ""),
            selection_id=c.get("selection_id", c.get("selection", "")),
            selection_label=c.get("selection_label", c.get("label", "")),
            decimal_odds=float(c.get("decimal_odds", c.get("odds", 1.0))),
            source_provider="synthetic_model",
            snapshot_type="synthetic",
            snapshot_timestamp=datetime.now().isoformat(),
        )
        snapshot.entries.append(entry)
    snapshot.warnings.append("Synthetic odds used; not real sportsbook odds. For analysis/simulation only.")
    return snapshot
