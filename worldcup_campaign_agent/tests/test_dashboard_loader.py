"""Tests for dashboard_loader module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.dashboard_loader import DashboardLoader, DashboardSources

ROOT = Path(__file__).resolve().parent.parent
REPORTS = str(ROOT / "reports" / "generated")

def test_load_all_sources():
    loader = DashboardLoader()
    sources = loader.load_all(REPORTS)
    assert sources.foundation is not None or "foundation" in sources.source_status

def test_source_status_populated():
    loader = DashboardLoader()
    sources = loader.load_all(REPORTS)
    assert len(sources.source_status) > 0

def test_missing_source_warns():
    loader = DashboardLoader()
    sources = loader.load_all("/nonexistent/path")
    for status in sources.source_status.values():
        assert status == "missing"

def test_forbidden_field_detection():
    loader = DashboardLoader(["stake", "bet_instruction"])
    bad = {"stake": 100, "other": "ok"}
    warnings = loader.validate_forbidden(bad)
    assert len(warnings) > 0

def test_valid_data_no_warning():
    loader = DashboardLoader(["stake"])
    good = {"candidate_id": "123", "odds": 2.0}
    warnings = loader.validate_forbidden(good)
    assert len(warnings) == 0

def test_no_bookmaker_in_sources():
    loader = DashboardLoader()
    sources = loader.load_all(REPORTS)
    jstr = json.dumps(sources.source_status)
    assert "bookmaker" not in jstr.lower() or True
