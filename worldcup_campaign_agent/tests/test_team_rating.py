"""Tests for team rating registry."""
from pathlib import Path
import pytest
from worldcup_campaign.team_rating import TeamRatingRegistry

def _data_path(f): return str(Path(__file__).resolve().parent.parent/"data"/"seed"/f)

class TestTeamRatingRegistry:
    @pytest.fixture
    def registry(self): return TeamRatingRegistry(_data_path("worldcup_2026_team_ratings.json"))
    def test_load_48_teams(self, registry): assert registry.team_count == 48
    def test_get_arg(self, registry):
        r = registry.get("ARG"); assert r is not None; assert r.team_name == "Argentina"
    def test_get_unknown_returns_none(self, registry): assert registry.get("XXX") is None
    def test_get_or_default_unknown(self, registry):
        r = registry.get_or_default("XXX"); assert r.is_placeholder is True
    def test_get_by_group(self, registry):
        g = registry.get_by_group("GROUP_A"); assert len(g) == 4
    def test_elite_rating(self, registry):
        r = registry.get("FRA"); assert r.overall >= 2000
    def test_ratings_in_range(self, registry):
        for c in ["ARG","BRA","FRA","NZL"]:
            r = registry.get(c); assert 1400 <= r.overall <= 2300