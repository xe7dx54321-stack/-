"""Tests for integrated strategy runner."""
import json, tempfile
from pathlib import Path
import pytest
from worldcup_campaign.integrated_strategy_runner import IntegratedStrategyRunner
def _cfg(f): return str(Path(__file__).resolve().parent.parent/"config"/f)
def _data(f): return str(Path(__file__).resolve().parent.parent/"data"/"seed"/f)

def _paths():
    return {
        "policy":_cfg("campaign_policy.json"),"states":_cfg("bankroll_states.json"),
        "stage_map":_cfg("worldcup_stage_map.json"),
        "match_registry":_data("worldcup_2026_match_registry.json"),
        "strategy_rules":_cfg("daily_strategy_rules.json"),
        "tagging_rules":_cfg("match_tagging_rules.json"),
        "scenario_rules":_cfg("scenario_rules.json"),
        "ratings":_data("worldcup_2026_team_ratings.json"),
        "prob_config":_cfg("probability_model_config.json"),
        "sanity_config":_cfg("probability_sanity_config.json"),
        "odds_policy":_cfg("odds_snapshot_policy.json"),
        "ev_config":_cfg("ev_ranking_config.json"),
        "score_config":_cfg("campaign_score_config.json"),
        "bucket_policy":_cfg("bucket_candidate_policy.json"),
        "integration_config":_cfg("daily_candidate_integration_config.json"),
        "market_registry":_cfg("market_universe.json"),
    }

class TestRunner:
    @pytest.fixture
    def runner(self): return IntegratedStrategyRunner(_paths())
    def test_run(self, runner):
        s = runner.run("2026-06-11", 100.0)
        assert s.current_date == "2026-06-11"
    def test_write_json(self, runner):
        with tempfile.TemporaryDirectory() as tmp:
            s = runner.run("2026-06-11", 100.0)
            p = Path(tmp)/"t.json"
            runner.write_json(s, str(p))
            assert p.exists()
            d = json.loads(p.read_text())
            assert d["not_betting_advice"] is True
    def test_write_md(self, runner):
        with tempfile.TemporaryDirectory() as tmp:
            s = runner.run("2026-06-11", 100.0)
            p = Path(tmp)/"t.md"
            runner.write_markdown(s, str(p))
            assert p.exists()
            c = p.read_text(encoding="utf-8")
            assert "Integrated Daily Strategy" in c
    def test_not_betting_advice(self, runner):
        s = runner.run("2026-06-11", 100.0)
        assert s.not_betting_advice is True
        assert s.simulation_only is True
    def test_no_forbidden_fields(self, runner):
        s = runner.run("2026-06-11", 100.0)
        d = s.__dict__
        for f in ["stake_to_match","bet_instruction","bookmaker_account"]:
            for k in d:
                assert f not in str(k).lower()