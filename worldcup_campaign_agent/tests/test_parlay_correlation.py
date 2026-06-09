"""Tests for parlay_correlation module."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.parlay_correlation import ParlayCorrelationAnalyzer

POLICY_PATH = str(Path(__file__).resolve().parent.parent / "config" / "parlay_correlation_policy.json")


def test_load_policy_succeeds():
    analyzer = ParlayCorrelationAnalyzer(POLICY_PATH)
    assert analyzer.policy is not None
    assert "same_match_policy" in analyzer.policy


def test_same_match_legs_blocked():
    analyzer = ParlayCorrelationAnalyzer(POLICY_PATH)
    legs = [
        {"match_id": "M001", "decimal_odds": 2.0, "model_probability": 0.5},
        {"match_id": "M001", "decimal_odds": 3.0, "model_probability": 0.3},
    ]
    result = analyzer.analyze(legs)
    assert result.is_blocked is True
    assert result.penalty_score > 0
    assert any("Blocked" in r for r in result.reason_codes)


def test_same_group_over_limit_warning():
    analyzer = ParlayCorrelationAnalyzer(POLICY_PATH)
    legs = [
        {"match_id": "M001", "group": "A", "decimal_odds": 2.0, "model_probability": 0.5},
        {"match_id": "M002", "group": "A", "decimal_odds": 2.0, "model_probability": 0.5},
        {"match_id": "M003", "group": "A", "decimal_odds": 2.0, "model_probability": 0.5},
    ]
    result = analyzer.analyze(legs)
    assert result.is_blocked is False
    assert result.penalty_score > 0
    assert any("same group" in w.lower() for w in result.warnings)


def test_same_market_type_warning():
    analyzer = ParlayCorrelationAnalyzer(POLICY_PATH)
    legs = [
        {"match_id": "M001", "group": "A", "market_type": "1x2", "decimal_odds": 2.0, "model_probability": 0.5},
        {"match_id": "M002", "group": "B", "market_type": "1x2", "decimal_odds": 2.0, "model_probability": 0.5},
    ]
    result = analyzer.analyze(legs)
    assert result.is_blocked is False
    assert any("same market type" in w.lower() for w in result.warnings)


def test_same_stage_same_day_warning():
    analyzer = ParlayCorrelationAnalyzer(POLICY_PATH)
    legs = [
        {"match_id": "M001", "stage": "group_stage", "date": "2026-06-11", "decimal_odds": 2.0, "model_probability": 0.5},
        {"match_id": "M002", "stage": "group_stage", "date": "2026-06-11", "decimal_odds": 2.0, "model_probability": 0.5},
    ]
    result = analyzer.analyze(legs)
    assert result.is_blocked is False
    assert len(result.reason_codes) > 0


def test_penalty_score_effective():
    analyzer = ParlayCorrelationAnalyzer(POLICY_PATH)
    legs = [
        {"match_id": "M001", "group": "A", "market_type": "1x2", "decimal_odds": 2.0, "model_probability": 0.5},
        {"match_id": "M002", "group": "A", "market_type": "1x2", "decimal_odds": 2.0, "model_probability": 0.5},
    ]
    result = analyzer.analyze(legs)
    assert result.is_blocked is False
    assert result.penalty_score > 0


def test_no_issue_clean_combo():
    analyzer = ParlayCorrelationAnalyzer(POLICY_PATH)
    legs = [
        {"match_id": "M001", "group": "A", "market_type": "1x2", "date": "2026-06-11", "stage": "group_stage", "decimal_odds": 2.0, "model_probability": 0.6},
        {"match_id": "M002", "group": "B", "market_type": "over_under", "date": "2026-06-12", "stage": "group_stage", "decimal_odds": 1.9, "model_probability": 0.5},
    ]
    result = analyzer.analyze(legs)
    assert result.is_blocked is False
    # penalty still possible but should be small (from same_stage_day or none)
    assert result.penalty_score < 0.3


def test_blocked_combination_not_silently_passed():
    analyzer = ParlayCorrelationAnalyzer(POLICY_PATH)
    legs = [
        {"match_id": "M001", "decimal_odds": 2.0, "model_probability": 0.5},
        {"match_id": "M001", "decimal_odds": 1.5, "model_probability": 0.6},
    ]
    result = analyzer.analyze(legs)
    assert result.is_blocked is True
