"""Tests for handicap model."""
import pytest
from worldcup_campaign.scoreline_model import ScorelineModel
from worldcup_campaign.handicap_model import HandicapModel

class TestHandicapModel:
    @pytest.fixture
    def model(self): return HandicapModel()
    @pytest.fixture
    def scorelines(self):
        sm = ScorelineModel(8)
        return sm.calculate(1.8, 1.0)
    def test_has_lines(self, model, scorelines):
        results = model.calculate(scorelines)
        assert len(results) == 9
    def test_triple_sums_to_1(self, model, scorelines):
        results = model.calculate(scorelines)
        for r in results:
            s = r.home_cover_probability + r.away_cover_probability + r.push_probability
            assert abs(s - 1.0) < 0.01
    def test_negative_line_favors_home(self, model, scorelines):
        results = model.calculate(scorelines)
        neg = [r for r in results if r.line == -0.5][0]
        assert neg.home_cover_probability > neg.away_cover_probability