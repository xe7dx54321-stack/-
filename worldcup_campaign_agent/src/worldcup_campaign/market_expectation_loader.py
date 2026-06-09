"""Market expectation loader: loads model, sportsbook, and polymarket sources."""
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MarketExpectationSources:
    model_data: dict = field(default_factory=dict)
    sportsbook_data: dict = field(default_factory=dict)
    polymarket_data: dict = field(default_factory=dict)
    model_available: bool = False
    sportsbook_available: bool = False
    polymarket_available: bool = False
    source_warnings: list = field(default_factory=list)


def load_market_expectation_sources(reports_dir: str) -> MarketExpectationSources:
    sources = MarketExpectationSources()
    p = Path(reports_dir)

    # Model probability
    mp_path = p / "match_probability_preview.json"
    if mp_path.exists():
        try:
            sources.model_data = json.loads(mp_path.read_text(encoding="utf-8"))
            sources.model_available = True
        except Exception as e:
            sources.source_warnings.append(f"Model data load error: {e}")
    else:
        sources.source_warnings.append("Model probability source not found.")

    # Sportsbook consensus
    mo_path = p / "market_odds_consensus.json"
    if mo_path.exists():
        try:
            sources.sportsbook_data = json.loads(mo_path.read_text(encoding="utf-8"))
            sources.sportsbook_available = True
        except Exception as e:
            sources.source_warnings.append(f"Sportsbook data load error: {e}")
    else:
        sources.source_warnings.append("Sportsbook consensus source not found.")

    # Polymarket
    pm_path = p / "polymarket_preview.json"
    if pm_path.exists():
        try:
            sources.polymarket_data = json.loads(pm_path.read_text(encoding="utf-8"))
            sources.polymarket_available = True
        except Exception as e:
            sources.source_warnings.append(f"Polymarket data load error: {e}")
    else:
        sources.source_warnings.append("Polymarket source not found.")

    return sources


def extract_model_probabilities(model_data: dict) -> dict:
    """Extract model probabilities keyed by match_id_selection."""
    probs = {}
    for m in model_data.get("matches", []):
        mid = m.get("match_id", "")
        for sel, field in [("H", "home_win_prob"), ("D", "draw_prob"), ("A", "away_win_prob")]:
            val = m.get(field)
            if val is not None:
                probs[f"{mid}_{sel}"] = float(val)
    return probs


def extract_sportsbook_probabilities(sportsbook_data: dict) -> dict:
    """Extract no-vig sportsbook consensus probabilities."""
    probs = {}
    nv = sportsbook_data.get("no_vig_summary", {})
    for m in nv.get("markets", []):
        mid = m.get("match_id", "")
        for sel_id, prob in m.get("no_vig_probabilities", {}).items():
            probs[f"{mid}_{sel_id}"] = float(prob)
    return probs


def extract_polymarket_probabilities(polymarket_data: dict) -> dict:
    """Extract Polymarket probabilities from discovery data."""
    probs = {}
    ds = polymarket_data.get("discovery_summary", {})
    for event in ds.get("events", []):
        if not event.get("is_relevant"):
            continue
        for market in event.get("markets", []):
            mid = market.get("market_id", "")
            if mid:
                probs[mid] = float(market.get("last_price", 0))
    return probs
