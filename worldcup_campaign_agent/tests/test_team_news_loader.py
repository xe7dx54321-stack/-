"""Tests for team_news_loader module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.team_news_loader import load_team_news_fixture, normalize_team_news
ROOT = Path(__file__).resolve().parent.parent; SEED = str(ROOT / "data" / "seed" / "team_news_seed.json")
CONFIG = {"reliability": {"confirmed": 1.0, "reported": 0.7, "rumor": 0.3, "stale_age_hours": 48}}
class TestLoader:
    def test_load(self):
        f = load_team_news_fixture(SEED)
        assert len(f["news_items"]) >= 10
    def test_normalize(self):
        f = load_team_news_fixture(SEED)
        n = normalize_team_news(f, CONFIG, "2026-06-11T10:00:00Z")
        assert n.normalized_news_count >= 10
        assert n.team_count >= 4
        assert n.match_count >= 2
    def test_rumor_warning(self):
        f = load_team_news_fixture(SEED)
        n = normalize_team_news(f, CONFIG, "2026-06-11T10:00:00Z")
        assert n.reliability_warning_count >= 1
    def test_no_stake(self):
        f = load_team_news_fixture(SEED)
        n = normalize_team_news(f, CONFIG, "2026-06-11T10:00:00Z")
        js = json.dumps({"count": n.normalized_news_count})
        assert "stake" not in js.lower()
