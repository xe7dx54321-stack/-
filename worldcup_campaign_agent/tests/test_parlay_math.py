"""Tests for parlay_math module."""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.parlay_math import (
    calculate_combined_odds,
    calculate_combined_probability,
    calculate_combined_ev,
    classify_odds_band,
    calculate_leg_quality_summary,
)


class TestCombinedOdds:
    def test_product_of_leg_odds(self):
        legs = [
            {"decimal_odds": 2.0},
            {"decimal_odds": 1.5},
        ]
        assert calculate_combined_odds(legs) == pytest.approx(3.0, rel=0.01)

    def test_single_leg_returns_its_odds(self):
        legs = [{"decimal_odds": 3.5}]
        assert calculate_combined_odds(legs) == pytest.approx(3.5, rel=0.01)

    def test_three_leg_product(self):
        legs = [
            {"decimal_odds": 2.0},
            {"decimal_odds": 3.0},
            {"decimal_odds": 4.0},
        ]
        assert calculate_combined_odds(legs) == pytest.approx(24.0, rel=0.01)

    def test_falls_back_to_mock_odds(self):
        legs = [{"mock_odds": 2.5}]
        assert calculate_combined_odds(legs) == pytest.approx(2.5, rel=0.01)

    def test_falls_back_to_odds_key(self):
        legs = [{"odds": 1.8}]
        assert calculate_combined_odds(legs) == pytest.approx(1.8, rel=0.01)

    def test_defaults_to_2_when_no_odds_field(self):
        legs = [{}]
        assert calculate_combined_odds(legs) == pytest.approx(2.0, rel=0.01)

    def test_odds_leq_1_fails(self):
        legs = [{"decimal_odds": 1.0}]
        with pytest.raises(ValueError, match="must be > 1"):
            calculate_combined_odds(legs)

    def test_odds_below_1_fails(self):
        legs = [{"decimal_odds": 0.5}]
        with pytest.raises(ValueError):
            calculate_combined_odds(legs)

    def test_no_dict_output(self):
        legs = [{"decimal_odds": 2.0}, {"decimal_odds": 1.5}]
        result = calculate_combined_odds(legs)
        assert isinstance(result, float)


class TestCombinedProbability:
    def test_product_of_probabilities(self):
        legs = [
            {"model_probability": 0.5},
            {"model_probability": 0.4},
        ]
        assert calculate_combined_probability(legs) == pytest.approx(0.2, rel=0.01)

    def test_single_leg(self):
        legs = [{"model_probability": 0.7}]
        assert calculate_combined_probability(legs) == pytest.approx(0.7, rel=0.01)

    def test_three_legs(self):
        legs = [
            {"model_probability": 0.5},
            {"model_probability": 0.5},
            {"model_probability": 0.5},
        ]
        assert calculate_combined_probability(legs) == pytest.approx(0.125, rel=0.01)

    def test_defaults_to_0_5(self):
        legs = [{}]
        assert calculate_combined_probability(legs) == pytest.approx(0.5, rel=0.01)

    def test_probability_negative_fails(self):
        legs = [{"model_probability": -0.1}]
        with pytest.raises(ValueError):
            calculate_combined_probability(legs)

    def test_probability_above_1_fails(self):
        legs = [{"model_probability": 1.5}]
        with pytest.raises(ValueError):
            calculate_combined_probability(legs)

    def test_probability_exactly_1_ok(self):
        legs = [{"model_probability": 1.0}]
        assert calculate_combined_probability(legs) == pytest.approx(1.0, rel=0.01)

    def test_probability_exactly_0_ok(self):
        legs = [{"model_probability": 0.0}]
        assert calculate_combined_probability(legs) == pytest.approx(0.0, rel=0.01)


class TestCombinedEV:
    def test_positive_ev(self):
        assert calculate_combined_ev(0.5, 3.0) == pytest.approx(0.5, rel=0.01)

    def test_negative_ev(self):
        assert calculate_combined_ev(0.3, 2.0) == pytest.approx(-0.4, rel=0.01)

    def test_breakeven_ev(self):
        result = calculate_combined_ev(0.5, 2.0)
        assert result == pytest.approx(0.0, rel=0.01)

    def test_high_odds_low_prob(self):
        result = calculate_combined_ev(0.01, 100.0)
        assert result == pytest.approx(0.0, rel=0.01)


class TestOddsBand:
    def test_low_band(self):
        assert classify_odds_band(1.5) == "low"

    def test_medium_band(self):
        assert classify_odds_band(5.0) == "medium"

    def test_high_band(self):
        assert classify_odds_band(30.0) == "high"

    def test_very_high_band(self):
        assert classify_odds_band(100.0) == "very_high"

    def test_lottery_band(self):
        assert classify_odds_band(600.0) == "lottery"

    def test_boundary_low_to_medium(self):
        assert classify_odds_band(3.0) == "medium"

    def test_boundary_medium_to_high(self):
        assert classify_odds_band(10.0) == "high"

    def test_custom_config(self):
        config = {
            "odds_bands": {
                "low": {"min": 1.01, "max": 2.0},
                "medium": {"min": 2.0, "max": 5.0},
                "high": {"min": 5.0, "max": 10000.0},
            }
        }
        assert classify_odds_band(1.5, config) == "low"
        assert classify_odds_band(3.0, config) == "medium"
        assert classify_odds_band(10.0, config) == "high"


class TestLegQualitySummary:
    def test_averages(self):
        legs = [
            {"model_probability": 0.3, "decimal_odds": 3.0},
            {"model_probability": 0.5, "decimal_odds": 2.0},
        ]
        result = calculate_leg_quality_summary(legs)
        assert result["avg_prob"] == pytest.approx(0.4, rel=0.01)
        assert result["avg_odds"] == pytest.approx(2.5, rel=0.01)
        assert result["min_prob"] == pytest.approx(0.3, rel=0.01)
        assert result["max_odds"] == pytest.approx(3.0, rel=0.01)
        assert result["count"] == 2

    def test_empty_legs(self):
        result = calculate_leg_quality_summary([])
        assert result["count"] == 0
        assert result["avg_prob"] == 0
