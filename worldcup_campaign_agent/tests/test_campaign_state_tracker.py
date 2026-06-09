"""Tests for campaign_state_tracker module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.campaign_state_tracker import CampaignStateTracker, CampaignStateSnapshot

def test_snapshot_created():
    snapshot = CampaignStateSnapshot(
        date="2026-06-11", simulated_bankroll=100.0,
        bankroll_state="S2", required_multiplier=10000.0
    )
    assert snapshot.date == "2026-06-11"
    assert snapshot.simulated_bankroll == 100.0

def test_snapshot_safety_flags():
    snapshot = CampaignStateSnapshot(
        date="2026-06-11", simulated_bankroll=100.0,
        bankroll_state="S2", required_multiplier=10000.0
    )
    assert snapshot.analysis_only is True
    assert snapshot.simulation_only is True
    assert snapshot.not_betting_advice is True

def test_tracker_record():
    tracker = CampaignStateTracker()
    from worldcup_campaign.settlement_engine import SettlementResult
    result = SettlementResult(
        date="2026-06-11",
        simulated_bankroll_before=100.0,
        simulated_bankroll_after=95.0,
        bankroll_state_after="S1",
        required_multiplier_after=10526.0,
    )
    snapshot = tracker.record_snapshot(result)
    assert len(tracker.history) == 1
    assert snapshot.simulated_bankroll == 95.0

def test_tracker_save_load(tmp_path):
    tracker = CampaignStateTracker()
    from worldcup_campaign.settlement_engine import SettlementResult
    result = SettlementResult(
        date="2026-06-11",
        simulated_bankroll_before=100.0,
        simulated_bankroll_after=95.0,
        bankroll_state_after="S1",
        required_multiplier_after=10526.0,
    )
    tracker.record_snapshot(result)
    p = str(tmp_path / "history.json")
    tracker.save_history(p)
    assert Path(p).exists()

    tracker2 = CampaignStateTracker()
    tracker2.load_history(p)
    assert len(tracker2.history) == 1
    assert tracker2.history[0].simulated_bankroll == 95.0

def test_current_positions():
    tracker = CampaignStateTracker()
    pos = tracker.get_current_positions()
    assert pos["total_snapshots"] == 0
    assert pos["open_positions"] == 0
    assert pos["pending_positions"] == 0

def test_no_stake_in_snapshot():
    snapshot = CampaignStateSnapshot(
        date="2026-06-11", simulated_bankroll=100.0,
        bankroll_state="S2", required_multiplier=10000.0
    )
    d = snapshot.__dict__
    assert "stake" not in d
    assert "stake_to_match" not in d
    assert "bet_instruction" not in d
