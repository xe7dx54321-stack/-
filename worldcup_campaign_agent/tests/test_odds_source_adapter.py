"""Tests for odds_source_adapter module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.odds_source_adapter import (
    load_odds_from_csv, load_odds_from_json, load_synthetic_odds_from_ev_ranking,
    OddsSnapshot, OddsEntry
)

ROOT = Path(__file__).resolve().parent.parent
SEED_CSV = str(ROOT / "data" / "seed" / "manual_odds_seed.csv")
SEED_JSON = str(ROOT / "data" / "seed" / "manual_odds_seed.json")


class TestCSVLoad:
    def test_load_csv(self):
        snapshot = load_odds_from_csv(SEED_CSV)
        assert len(snapshot.entries) >= 10
        assert "sportsbook_A" in snapshot.source_providers

    def test_entries_have_required_fields(self):
        snapshot = load_odds_from_csv(SEED_CSV)
        for e in snapshot.entries:
            assert e.match_id
            assert e.market_type
            assert e.decimal_odds > 1.0

    def test_source_providers_tracked(self):
        snapshot = load_odds_from_csv(SEED_CSV)
        assert len(snapshot.source_providers) >= 1


class TestJSONLoad:
    def test_load_json(self):
        snapshot = load_odds_from_json(SEED_JSON)
        assert len(snapshot.entries) >= 10
        assert snapshot.snapshot_date == "2026-06-11"

    def test_source_providers(self):
        snapshot = load_odds_from_json(SEED_JSON)
        assert "sportsbook_A" in snapshot.source_providers


class TestSynthetic:
    def test_load_synthetic(self):
        ev_data = {
            "date": "2026-06-11",
            "candidates": [
                {"match_id": "GS_A_R1_001", "market_type": "1X2", "selection_id": "H", "selection_label": "Home", "decimal_odds": 1.85},
            ]
        }
        snapshot = load_synthetic_odds_from_ev_ranking(ev_data)
        assert len(snapshot.entries) == 1
        assert snapshot.source_providers == ["synthetic_model"]
        assert "Synthetic" in snapshot.warnings[0]


class TestSafety:
    def test_no_bookmaker_account(self):
        snapshot = load_odds_from_csv(SEED_CSV)
        import json
        d = {"source_providers": snapshot.source_providers, "warnings": snapshot.warnings}
        js = json.dumps(d)
        assert "bookmaker_account" not in js

    def test_no_stake(self):
        snapshot = load_odds_from_json(SEED_JSON)
        import json
        d = {"entries_count": len(snapshot.entries)}
        js = json.dumps(d)
        assert "stake" not in js.lower() or "stake" not in js
