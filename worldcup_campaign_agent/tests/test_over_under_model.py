"""Tests for over/under model."""
import pytest
from worldcup_campaign.scoreline_model import ScorelineModel
from worldcup_campaign.over_under_model import OverUnderModel

class TestOverUnderModel:
    @pytest.fixture
    def model(self): return OverUnderModel([0.5, 1.5, 2.5, 3.5, 4.5])
    @pytest.fixture
    def scorelines(self):
        sm = ScorelineModel(8)
        return sm.calculate(1.5, 1.2)
    def test_five_lines(self, model, scorelines):
        results = model.calculate(scorelines)
        assert len(results) == 5
    def test_over_under_sum_is_1(self, model, scorelines):
        results = model.calculate(scorelines)
        for r in results:
            assert abs(r.over_probability + r.under_probability - 1.0) < 0.01
    def test_low_line_high_over(self, model, scorelines):
        results = model.calculate(scorelines)
        assert results[0].over_probability > results[-1].over_probability