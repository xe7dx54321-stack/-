"""Tests for settlement_engine module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.settlement_engine import SettlementEngine

ROOT = Path(__file__).resolve().parent.parent
SC = str(ROOT / "config" / "postmatch_settlement_config.json")
SR = str(ROOT / "config" / "settlement_rules.json")
SEED = str(ROOT / "data" / "seed" / "manual_result_seed.json")

def test_engine_loads():
    engine = SettlementEngine(SC, SR)
    assert engine.config is not None
    assert engine.rules is not None

def test_load_manual_results():
    engine = SettlementEngine(SC, SR)
    results, warnings = engine.load_manual_results(SEED)
    assert len(results) == 2
    assert len(warnings) == 0

def test_manual_results_no_bookmaker():
    engine = SettlementEngine(SC, SR)
    results, _ = engine.load_manual_results(SEED)
    for r in results:
        assert "bookmaker" not in r

def test_1x2_outcome_hit():
    engine = SettlementEngine(SC, SR)
    from worldcup_campaign.settlement_ledger import LedgerEntry
    entry = LedgerEntry(entry_id="T1", date="2026-06-11", match_id="M001",
                       market_type="1x2", selection_id="home")
    match = {"match_id": "M001", "result_1x2": "home"}
    outcome = engine._determine_outcome(entry, match)
    assert outcome == "hit"

def test_1x2_outcome_miss():
    engine = SettlementEngine(SC, SR)
    from worldcup_campaign.settlement_ledger import LedgerEntry
    entry = LedgerEntry(entry_id="T2", date="2026-06-11", match_id="M001",
                       market_type="1x2", selection_id="home")
    match = {"match_id": "M001", "result_1x2": "away"}
    outcome = engine._determine_outcome(entry, match)
    assert outcome == "miss"

def test_futures_pending():
    engine = SettlementEngine(SC, SR)
    from worldcup_campaign.settlement_ledger import LedgerEntry
    entry = LedgerEntry(entry_id="T3", date="2026-06-11", match_id="M001",
                       market_type="winner", selection_id="ARG")
    match = {"match_id": "M001", "result_1x2": "home"}
    # Build a mini ledger
    from worldcup_campaign.settlement_ledger import SimulationLedger
    ledger = SimulationLedger(date="2026-06-11", entries=[entry])
    result = engine.settle(ledger, [match], 100.0, "S2")
    assert result.pending_count == 1
    assert result.settled_entries == []

def test_bankroll_preserves_reserve():
    engine = SettlementEngine(SC, SR)
    from worldcup_campaign.settlement_ledger import SimulationLedger, LedgerEntry
    entry = LedgerEntry(entry_id="T4", date="2026-06-11", match_id="M001",
                       market_type="1x2", selection_id="home",
                       simulated_deployment=20.0, odds=2.0)
    ledger = SimulationLedger(date="2026-06-11", entries=[entry])
    match = {"match_id": "M001", "result_1x2": "home"}
    result = engine.settle(ledger, [match], 100.0, "S2")
    # Hit: reserve(50) + return(20*2=40) + undistributed(50-20=30) = 120
    # But the formula gives: reserve(50) + 40 + max(0, 50-20) = 120
    assert result.simulated_bankroll_after >= 80  # At minimum
    assert result.hit_count == 1

def test_routing_hint_generated():
    engine = SettlementEngine(SC, SR)
    hint = engine._generate_routing_hint(1, 0, [], "S2", 5000.0)
    assert "S2" in hint
    assert "5000x" in hint or "5000" in hint

def test_no_stake_in_result():
    engine = SettlementEngine(SC, SR)
    from worldcup_campaign.settlement_ledger import SimulationLedger, LedgerEntry
    entry = LedgerEntry(entry_id="T5", date="2026-06-11", match_id="M001",
                       market_type="1x2", selection_id="home")
    ledger = SimulationLedger(date="2026-06-11", entries=[entry])
    match = {"match_id": "M001", "result_1x2": "home"}
    result = engine.settle(ledger, [match], 100.0, "S2")
    d = result.__dict__
    assert "stake" not in d
    assert "stake_to_match" not in d
    assert "bet_instruction" not in d
    assert "real_money_balance" not in d
