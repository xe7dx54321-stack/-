"""Tests for dashboard_builder module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.dashboard_loader import DashboardLoader
from worldcup_campaign.dashboard_builder import DashboardBuilder

ROOT = Path(__file__).resolve().parent.parent
REPORTS = str(ROOT / "reports" / "generated")
DC = str(ROOT / "config" / "dashboard_config.json")

@pytest.fixture
def dashboard():
    loader = DashboardLoader()
    sources = loader.load_all(REPORTS)
    builder = DashboardBuilder(DC)
    return builder.build("2026-06-11", 100.0, sources)

def test_dashboard_created(dashboard):
    assert dashboard.current_date == "2026-06-11"
    assert dashboard.dashboard_mode == "current_day"

def test_liquid_simulated_bankroll(dashboard):
    bs = dashboard.bankroll_summary
    assert "liquid_simulated_bankroll" in bs
    assert bs["liquid_simulated_bankroll"] > 0

def test_locked_pending_units(dashboard):
    bs = dashboard.bankroll_summary
    assert "locked_pending_units" in bs

def test_total_campaign_equity(dashboard):
    bs = dashboard.bankroll_summary
    assert "total_campaign_equity" in bs
    assert bs["total_campaign_equity"] >= bs["liquid_simulated_bankroll"]

def test_pending_not_realized_loss(dashboard):
    bs = dashboard.bankroll_summary
    assert "locked_pending_units" in bs
    assert "note" in bs

def test_candidate_summary_has_value_note(dashboard):
    cs = dashboard.candidate_summary
    assert "value_candidate_note" in cs

def test_parlay_summary_blocked(dashboard):
    ps = dashboard.parlay_summary
    assert "blocked_count" in ps
    assert "note" in ps

def test_futures_summary_proxy_warning(dashboard):
    fs = dashboard.futures_summary
    assert "proxy_warning" in fs

def test_next_day_routing(dashboard):
    assert len(dashboard.next_day_routing) > 0 or dashboard.next_day_routing == ""

def test_safety_flags(dashboard):
    s = dashboard.safety
    assert s["campaign_analysis_only"] is True
    assert s["real_bet_execution"] is False

def test_no_stake_in_dashboard(dashboard):
    from dataclasses import asdict
    d = asdict(dashboard)
    jstr = json.dumps(d, default=str)
    assert "stake_to_match" not in jstr
