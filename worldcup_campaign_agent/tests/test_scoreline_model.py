"""Tests for Poisson scoreline model."""
import pytest
from worldcup_campaign.scoreline_model import ScorelineModel

class TestScorelineModel:
    @pytest.fixture
    def model(self): return ScorelineModel(max_goals=8)
    def test_distribution_sums_approximately_1(self, model):
        results = model.calculate(1.5, 1.2)
        total = sum(s.probability for s in results)
        assert abs(total - 1.0) < 0.05
    def test_top_scorelines(self, model):
        results = model.calculate(1.5, 1.2)
        top = model.get_top_scorelines(results, 5)
        assert len(top) == 5
        assert top[0].probability >= top[-1].probability
    def test_higher_eg_yields_higher_scores(self, model):
        r1 = model.calculate(3.0, 0.5)
        r2 = model.calculate(0.5, 0.5)
        r1_high = sum(s.probability for s in r1 if s.home_goals + s.away_goals >= 3)
        r2_high = sum(s.probability for s in r2 if s.home_goals + s.away_goals >= 3)
        assert r1_high > r2_high