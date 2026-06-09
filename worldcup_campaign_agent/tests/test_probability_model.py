"""Tests for probability model."""
from pathlib import Path
import pytest
from worldcup_campaign.probability_model import ProbabilityModel
def _cfg(f): return str(Path(__file__).resolve().parent.parent/"config"/f)

class TestProbabilityModel:
    @pytest.fixture
    def model(self): return ProbabilityModel(_cfg("probability_model_config.json"))
    def test_calculate_sums_to_1(self, model):
        mp = model.calculate("m1","BRA","ARG",2100,2000)
        s = mp.home_win_prob + mp.draw_prob + mp.away_win_prob
        assert abs(s - 1.0) < 0.01
    def test_home_advantage(self, model):
        mp1 = model.calculate("m1","A","B",1800,1800)
        assert mp1.home_win_prob > mp1.away_win_prob
    def test_strong_vs_weak(self, model):
        mp = model.calculate("m1","FRA","NZL",2100,1520)
        assert mp.home_win_prob > 0.6
    def test_expected_goals_reasonable(self, model):
        mp = model.calculate("m1","A","B",1800,1800)
        assert 1.0 <= mp.expected_goals_home <= 3.0
    def test_confidence_in_range(self, model):
        mp = model.calculate("m1","A","B",1800,1800)
        assert 0.1 <= mp.confidence <= 0.95
    def test_placeholder_warning(self, model):
        mp = model.calculate("m1","TBD","XYZ",1600,1600,home_is_placeholder=True)
        assert len(mp.warnings) >= 1
    def test_knockout_lowers_confidence(self, model):
        mp1 = model.calculate("m1","A","B",2000,1500)
        mp2 = model.calculate("m2","A","B",2000,1500,is_knockout=True)
        assert mp2.confidence < mp1.confidence