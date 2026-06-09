"""Tests for mock odds generator."""
from pathlib import Path
import pytest
from worldcup_campaign.mock_odds import MockOddsGenerator
def _cfg(f): return str(Path(__file__).resolve().parent.parent/"config"/f)

class TestMockOdds:
    @pytest.fixture
    def gen(self): return MockOddsGenerator(_cfg("odds_snapshot_policy.json"))
    def test_generate_1x2_3_selections(self, gen):
        odds = gen.generate_1x2("m1", 0.45, 0.25, 0.30)
        assert len(odds) == 3
    def test_odds_in_range(self, gen):
        odds = gen.generate_1x2("m1", 0.5, 0.25, 0.25)
        for o in odds:
            assert 1.05 <= o.odds <= 100.0
    def test_higher_prob_lower_odds(self, gen):
        odds = gen.generate_1x2("m1", 0.6, 0.2, 0.2)
        home = next(o for o in odds if o.selection=="home")
        draw = next(o for o in odds if o.selection=="draw")
        assert home.odds < draw.odds
    def test_all_mock_flags(self, gen):
        odds = gen.generate_1x2("m1", 0.5, 0.25, 0.25)
        for o in odds:
            assert o.is_mock is True
            assert o.is_synthetic is True
    def test_generate_ou(self, gen):
        odds = gen.generate_over_under("m1", 2.5, 0.5, 0.5)
        assert len(odds) == 2