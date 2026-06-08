"""Tests for target math module."""

import pytest

from worldcup_campaign.target_math import (
    calculate_target_gap,
    calculate_required_growth_per_window,
    classify_target_urgency,
)


class TestTargetGap:
    """Tests for target gap calculation."""

    def test_100_to_1M_gap_is_10000(self):
        gap = calculate_target_gap(100.0, 1000000.0)
        assert gap == 10000.0

    def test_500_to_1M_gap(self):
        gap = calculate_target_gap(500.0, 1000000.0)
        assert gap == 2000.0

    def test_at_target_gap_is_1(self):
        gap = calculate_target_gap(1000000.0, 1000000.0)
        assert gap == 1.0

    def test_above_target_gap_less_than_1(self):
        gap = calculate_target_gap(2000000.0, 1000000.0)
        assert gap == 0.5

    def test_zero_bankroll_fails(self):
        with pytest.raises(ValueError):
            calculate_target_gap(0.0, 1000000.0)

    def test_negative_bankroll_fails(self):
        with pytest.raises(ValueError):
            calculate_target_gap(-100.0, 1000000.0)


class TestRequiredGrowthPerWindow:
    """Tests for required growth per window."""

    def test_100_to_1M_in_40_windows(self):
        growth = calculate_required_growth_per_window(100.0, 1000000.0, 40)
        expected = 10000.0 ** (1.0 / 40)
        assert abs(growth - expected) < 0.0001

    def test_at_target_returns_1(self):
        growth = calculate_required_growth_per_window(1000000.0, 1000000.0, 40)
        assert growth == 1.0

    def test_zero_windows_fails(self):
        with pytest.raises(ValueError):
            calculate_required_growth_per_window(100.0, 1000000.0, 0)

    def test_negative_windows_fails(self):
        with pytest.raises(ValueError):
            calculate_required_growth_per_window(100.0, 1000000.0, -1)


class TestTargetUrgency:
    """Tests for urgency classification."""

    def test_low_urgency(self):
        assert classify_target_urgency(1.05) == "low"

    def test_boundary_low_to_medium(self):
        # 1.1 is at the boundary: spec says <= 1.1 is low
        assert classify_target_urgency(1.1) == "low"
        assert classify_target_urgency(1.11) == "medium"

    def test_medium_urgency(self):
        assert classify_target_urgency(1.2) == "medium"

    def test_boundary_medium_to_high(self):
        # 1.3 is at the boundary: spec says <= 1.3 is medium
        assert classify_target_urgency(1.3) == "medium"
        assert classify_target_urgency(1.31) == "high"

    def test_high_urgency(self):
        assert classify_target_urgency(1.5) == "high"

    def test_boundary_high_to_extreme(self):
        # 2.0 is at the boundary: spec says <= 2.0 is high
        assert classify_target_urgency(2.0) == "high"
        assert classify_target_urgency(2.01) == "extreme"

    def test_extreme_urgency(self):
        assert classify_target_urgency(3.0) == "extreme"

    def test_target_reached(self):
        assert classify_target_urgency(1.0) == "target_reached"
        assert classify_target_urgency(0.5) == "target_reached"
