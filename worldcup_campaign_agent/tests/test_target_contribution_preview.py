import pytest
"""Tests for target contribution preview."""
from worldcup_campaign.target_contribution_preview import TargetContributionCalculator

class TestTargetContribution:
    @pytest.fixture
    def calc(self): return TargetContributionCalculator(1000000.0)
    def test_large_gap_small_contribution(self, calc):
        r = calc.calculate(100.0, 2.0, 40)
        assert r.difficulty_label != ""
        assert r.contribution_ratio < 0.01
    def test_near_target(self, calc):
        r = calc.calculate(500000.0, 2.0, 40)
        assert r.contribution_ratio > 0
    def test_single_hit_reaches(self, calc):
        r = calc.calculate(100.0, 10001.0, 40)
        assert r.difficulty_label == "single_hit_reaches_target"