"""Tests for source_alignment module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.source_alignment import (
    load_source_alignment_policy, validate_source_alignment_policy,
    check_source_alignment, load_dashboard_sources_for_alignment,
    SourceAlignmentPolicy, SourceAlignmentResult
)

ROOT = Path(__file__).resolve().parent.parent


class TestSourceAlignmentPolicy:
    def test_load_policy(self):
        policy = load_source_alignment_policy(str(ROOT / "config" / "source_alignment_policy.json"))
        assert policy.check_cli_vs_snapshot is True
        assert policy.check_bankroll_alignment is True
        assert policy.analysis_only is True

    def test_validate_policy(self):
        policy = SourceAlignmentPolicy()
        validate_source_alignment_policy(policy)

    def test_validate_policy_negative_tolerance(self):
        policy = SourceAlignmentPolicy(bankroll_mismatch_tolerance=-0.1)
        with pytest.raises(ValueError):
            validate_source_alignment_policy(policy)


class TestSourceAlignment:
    def test_no_mismatch(self):
        policy = SourceAlignmentPolicy()
        sources = {
            "postmatch_settlement": {"date": "2026-06-11", "simulated_bankroll_after": 100.0},
            "source_status": {},
        }
        result = check_source_alignment("2026-06-11", 100.0, sources, policy)
        assert result.bankroll_aligned is True

    def test_bankroll_mismatch_triggers_warning(self):
        policy = SourceAlignmentPolicy()
        sources = {
            "postmatch_settlement": {"date": "2026-06-11", "simulated_bankroll_after": 3500.03},
            "source_status": {},
        }
        result = check_source_alignment("2026-06-11", 100.0, sources, policy)
        assert result.bankroll_aligned is False
        assert len(result.warnings) > 0
        assert any("bankroll" in w.lower() for w in result.warnings)

    def test_date_mismatch_triggers_warning(self):
        policy = SourceAlignmentPolicy()
        sources = {
            "postmatch_settlement": {"date": "2026-06-24", "simulated_bankroll_after": 100.0},
            "source_status": {},
        }
        result = check_source_alignment("2026-06-11", 100.0, sources, policy)
        assert result.date_aligned is False
        assert len(result.warnings) > 0

    def test_missing_source_warning_and_continue(self):
        policy = SourceAlignmentPolicy()
        sources = {"source_status": {}}
        result = check_source_alignment("2026-06-11", 100.0, sources, policy)
        assert result.source_freshness_summary is not None
        # Should not raise

    def test_source_freshness_summary(self):
        policy = SourceAlignmentPolicy()
        sources = {
            "postmatch_settlement": {"date": "2026-06-11", "simulated_bankroll_after": 100.0},
            "source_status": {"postmatch_settlement": "loaded", "parlay_preview": "missing"},
        }
        result = check_source_alignment("2026-06-11", 100.0, sources, policy)
        assert result.source_freshness_summary is not None

    def test_no_bookmaker_in_output(self):
        policy = SourceAlignmentPolicy()
        sources = {"source_status": {}}
        result = check_source_alignment("2026-06-11", 100.0, sources, policy)
        d = {
            "cli_date": result.cli_date,
            "cli_bankroll": result.cli_bankroll,
            "warnings": result.warnings,
        }
        js = json.dumps(d)
        assert "bookmaker" not in js.lower()

    def test_no_stake_in_output(self):
        policy = SourceAlignmentPolicy()
        sources = {"source_status": {}}
        result = check_source_alignment("2026-06-11", 100.0, sources, policy)
        d = {
            "cli_date": result.cli_date,
            "cli_bankroll": result.cli_bankroll,
            "warnings": result.warnings,
        }
        js = json.dumps(d)
        assert "stake" not in js.lower()
        assert "bet_instruction" not in js.lower()
