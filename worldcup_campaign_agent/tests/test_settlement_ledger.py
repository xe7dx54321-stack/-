"""Tests for settlement_ledger module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.settlement_ledger import SettlementLedgerBuilder, SimulationLedger, LedgerEntry

ROOT = Path(__file__).resolve().parent.parent
SC = str(ROOT / "config" / "postmatch_settlement_config.json")

def test_build_empty_ledger():
    builder = SettlementLedgerBuilder(SC)
    ledger = builder.build_empty_ledger("2026-06-11")
    assert ledger.date == "2026-06-11"
    assert len(ledger.entries) == 0

def test_ledger_entry_has_no_forbidden_fields():
    entry = LedgerEntry(entry_id="TEST", date="2026-06-11")
    d = entry.__dict__
    assert "stake" not in d
    assert "stake_to_match" not in d
    assert "bet_instruction" not in d
    assert "bookmaker" not in d
    assert "real_money_balance" not in d

def test_ledger_analysis_only():
    entry = LedgerEntry(entry_id="TEST", date="2026-06-11")
    assert entry.analysis_only is True
    assert entry.simulation_only is True
    assert entry.not_betting_advice is True

def test_simulation_ledger_safety():
    ledger = SimulationLedger(date="2026-06-11")
    assert ledger.analysis_only is True
    assert ledger.simulation_only is True
    assert ledger.not_betting_advice is True

def test_validate_no_forbidden():
    builder = SettlementLedgerBuilder(SC)
    ledger = SimulationLedger(date="2026-06-11")
    warnings = builder.validate_ledger(ledger)
    assert isinstance(warnings, list)

def test_ledger_entry_default_outcome_unknown():
    entry = LedgerEntry(entry_id="TEST", date="2026-06-11")
    assert entry.outcome == "unknown"
    assert entry.is_settled is False

def test_forbidden_fields_in_config():
    builder = SettlementLedgerBuilder(SC)
    assert "stake" in builder.forbidden
    assert "stake_to_match" in builder.forbidden
    assert "bet_instruction" in builder.forbidden
