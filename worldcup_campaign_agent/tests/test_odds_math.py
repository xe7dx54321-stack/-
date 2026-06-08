"""Tests for odds math module."""

import pytest

from worldcup_campaign.odds_math import (
    decimal_odds_to_implied_probability,
    normalize_no_vig_probabilities,
    calculate_edge,
    calculate_ev,
    calculate_parlay_odds,
    calculate_parlay_probability,
    calculate_parlay_ev,
)


class TestDecimalOddsToImpliedProbability:
    """Tests for implied probability conversion."""

    def test_odds_2_to_prob_0_5(self):
        assert decimal_odds_to_implied_probability(2.0) == 0.5

    def test_odds_1_5_to_prob_0_6667(self):
        result = decimal_odds_to_implied_probability(1.5)
        assert abs(result - 0.6667) < 0.001

    def test_odds_10_to_prob_0_1(self):
        assert decimal_odds_to_implied_probability(10.0) == 0.1

    def test_odds_1_fails(self):
        with pytest.raises(ValueError):
            decimal_odds_to_implied_probability(1.0)

    def test_odds_0_5_fails(self):
        with pytest.raises(ValueError):
            decimal_odds_to_implied_probability(0.5)

    def test_odds_negative_fails(self):
        with pytest.raises(ValueError):
            decimal_odds_to_implied_probability(-2.0)


class TestNormalizeNoVig:
    """Tests for no-vig normalization."""

    def test_normalize_sums_to_1(self):
        odds = {"home": 2.0, "draw": 3.5, "away": 4.0}
        probs = normalize_no_vig_probabilities(odds)
        total = sum(probs.values())
        assert abs(total - 1.0) < 0.001

    def test_normalize_with_vig(self):
        odds = {"home": 2.0, "away": 2.0}
        probs = normalize_no_vig_probabilities(odds)
        assert probs["home"] == 0.5
        assert probs["away"] == 0.5
        assert abs(sum(probs.values()) - 1.0) < 0.001

    def test_empty_odds_fails(self):
        with pytest.raises(ValueError):
            normalize_no_vig_probabilities({})


class TestCalculateEdge:
    """Tests for edge calculation."""

    def test_positive_edge(self):
        edge = calculate_edge(0.6, 0.5)
        assert abs(edge - 0.1) < 0.001

    def test_negative_edge(self):
        edge = calculate_edge(0.4, 0.5)
        assert abs(edge - (-0.1)) < 0.001

    def test_no_edge(self):
        edge = calculate_edge(0.5, 0.5)
        assert edge == 0.0

    def test_invalid_model_prob(self):
        with pytest.raises(ValueError):
            calculate_edge(1.5, 0.5)

    def test_invalid_market_prob(self):
        with pytest.raises(ValueError):
            calculate_edge(0.5, -0.1)


class TestCalculateEV:
    """Tests for expected value calculation."""

    def test_positive_ev(self):
        # p=0.6, odds=2.0: EV = 0.6*(1) - 0.4 = 0.2
        ev = calculate_ev(0.6, 2.0)
        assert abs(ev - 0.2) < 0.001

    def test_negative_ev(self):
        # p=0.3, odds=2.0: EV = 0.3*(1) - 0.7 = -0.4
        ev = calculate_ev(0.3, 2.0)
        assert abs(ev - (-0.4)) < 0.001

    def test_break_even_ev(self):
        # p=0.5, odds=2.0: EV = 0.5*(1) - 0.5 = 0.0
        ev = calculate_ev(0.5, 2.0)
        assert abs(ev - 0.0) < 0.001

    def test_invalid_probability(self):
        with pytest.raises(ValueError):
            calculate_ev(1.5, 2.0)

    def test_invalid_odds(self):
        with pytest.raises(ValueError):
            calculate_ev(0.5, 1.0)


class TestParlayOdds:
    """Tests for parlay odds calculation."""

    def test_two_leg_parlay(self):
        result = calculate_parlay_odds([2.0, 1.5])
        assert result == 3.0

    def test_three_leg_parlay(self):
        result = calculate_parlay_odds([2.0, 2.0, 2.0])
        assert result == 8.0

    def test_empty_list_fails(self):
        with pytest.raises(ValueError):
            calculate_parlay_odds([])

    def test_invalid_odds_in_list(self):
        with pytest.raises(ValueError):
            calculate_parlay_odds([2.0, 0.5])


class TestParlayProbability:
    """Tests for parlay probability calculation."""

    def test_two_leg_probability(self):
        result = calculate_parlay_probability([0.5, 0.4])
        assert result == 0.2

    def test_invalid_probability(self):
        with pytest.raises(ValueError):
            calculate_parlay_probability([0.5, 1.5])


class TestParlayEV:
    """Tests for parlay EV calculation."""

    def test_two_leg_parlay_ev(self):
        # p1=0.6, p2=0.5 -> joint=0.3
        # odds1=2.0, odds2=1.8 -> parlay odds=3.6
        # EV = 0.3*(3.6-1) - 0.7 = 0.3*2.6 - 0.7 = 0.78 - 0.7 = 0.08
        ev = calculate_parlay_ev([0.6, 0.5], [2.0, 1.8])
        assert abs(ev - 0.08) < 0.001

    def test_mismatched_lengths_fails(self):
        with pytest.raises(ValueError):
            calculate_parlay_ev([0.5], [2.0, 3.0])
