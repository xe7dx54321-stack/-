"""Tests for probability sanity guard."""
from pathlib import Path
import pytest
from worldcup_campaign.probability_sanity import ProbabilitySanityGuard
def _cfg(f): return str(Path(__file__).resolve().parent.parent/"config"/f)

class TestProbabilitySanity:
    @pytest.fixture
    def guard(self): return ProbabilitySanityGuard(_cfg("probability_sanity_config.json"))
    def test_normal_passes(self, guard):
        r = guard.check_1x2(0.45, 0.15, 0.40)
        assert r.blocked is False
        assert abs(r.repaired_home_prob+r.repaired_draw_prob+r.repaired_away_prob-1.0)<0.01
    def test_draw_2_percent_repaired(self, guard):
        r = guard.check_1x2(0.46, 0.02, 0.52)
        assert r.repaired is True
        assert r.repaired_draw_prob >= 0.12
    def test_draw_at_min_passes(self, guard):
        r = guard.check_1x2(0.44, 0.12, 0.44)
        assert r.repaired is False or r.repaired_draw_prob >= 0.12
    def test_very_low_all_blocked(self, guard):
        r = guard.check_1x2(0.0, 0.12, 0.0)
        assert r.repaired is True
    def test_sum_not_one_repaired(self, guard):
        r = guard.check_1x2(0.5, 0.3, 0.3)
        assert r.repaired is True
    def test_get_effective_returns_tuple(self, guard):
        r = guard.get_effective_1x2(0.46, 0.02, 0.52)
        assert r is not None
        hp, dp, ap, result = r
        assert dp >= 0.12