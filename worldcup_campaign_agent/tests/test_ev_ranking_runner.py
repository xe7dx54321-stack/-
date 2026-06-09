"""Tests for EV ranking runner."""
import json, tempfile
from pathlib import Path
import pytest
from worldcup_campaign.ev_ranking_runner import EVRankingRunner
def _cfg(f): return str(Path(__file__).resolve().parent.parent/"config"/f)
def _data(f): return str(Path(__file__).resolve().parent.parent/"data"/"seed"/f)

class TestEVRankingRunner:
    @pytest.fixture
    def runner(self):
        return EVRankingRunner(
            _data("worldcup_2026_team_ratings.json"),
            _cfg("probability_model_config.json"),
            _data("worldcup_2026_match_registry.json"),
            _cfg("campaign_policy.json"),
            _cfg("probability_sanity_config.json"),
            _cfg("odds_snapshot_policy.json"),
            _cfg("ev_ranking_config.json"),
        )
    def test_runs_opens(self, runner):
        p = runner.run("2026-06-11", 100.0)
        assert p.candidate_count > 0
        assert p.uses_real_bookmaker_odds is False
    def test_runs_third_round(self, runner):
        p = runner.run("2026-06-24", 100.0)
        assert p.candidate_count > 0
    def test_runs_final(self, runner):
        p = runner.run("2026-07-19", 100.0)
        assert p.candidate_count > 0
    def test_sanity_repairs_draw(self, runner):
        p = runner.run("2026-06-11", 100.0)
        assert "total_checked" in p.sanity_summary
    def test_no_stake_no_bet(self, runner):
        p = runner.run("2026-06-11", 100.0)
        d = p.__dict__ if hasattr(p,'__dict__') else {}
        for f in ["stake","bet_instruction","guaranteed","real_odds_from_bookmaker"]:
            for k in d:
                assert f not in str(k).lower()
    def test_safety_flags(self, runner):
        p = runner.run("2026-06-11", 100.0)
        assert p.safety["campaign_analysis_only"] is True
        assert p.safety["real_bet_execution"] is False
    def test_write_json(self, runner):
        with tempfile.TemporaryDirectory() as tmp:
            p = runner.run("2026-06-11", 100.0)
            path = Path(tmp)/"test.json"
            runner.write_json(p, str(path))
            assert path.exists()
            d = json.loads(path.read_text())
            assert d["uses_real_bookmaker_odds"] is False
    def test_write_md(self, runner):
        with tempfile.TemporaryDirectory() as tmp:
            p = runner.run("2026-06-11", 100.0)
            path = Path(tmp)/"test.md"
            runner.write_markdown(p, str(path))
            assert path.exists()
            c = path.read_text(encoding="utf-8")
            assert "EV Ranking Preview" in c
    def test_candidates_have_required_fields(self, runner):
        p = runner.run("2026-06-11", 100.0)
        for c in p.candidates:
            for field in ["match_id","market_type","mock_odds","model_probability","edge","ev","value_flag"]:
                assert field in c