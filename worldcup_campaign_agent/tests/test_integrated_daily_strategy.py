"""Tests for integrated daily strategy."""
from pathlib import Path
import pytest
from worldcup_campaign.integrated_daily_strategy import IntegratedStrategyBuilder
def _cfg(f): return str(Path(__file__).resolve().parent.parent/"config"/f)
def _data(f): return str(Path(__file__).resolve().parent.parent/"data"/"seed"/f)

def _paths():
    return {
        "policy":_cfg("campaign_policy.json"),
        "states":_cfg("bankroll_states.json"),
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

class TestIntegratedStrategy:
    @pytest.fixture
    def builder(self): return IntegratedStrategyBuilder(_paths())
    def test_build_opens(self, builder):
        s = builder.build("2026-06-11", 100.0)
        assert s.bankroll_state == "S2"
        assert s.current_stage == "group_round_1"
    def test_build_third_round(self, builder):
        s = builder.build("2026-06-24", 100.0)
        assert s.current_stage == "group_round_3"
    def test_build_final(self, builder):
        s = builder.build("2026-07-19", 100.0)
        assert s.current_stage == "final"
    def test_build_bankroll_5000(self, builder):
        s = builder.build("2026-06-11", 5000.0)
        assert s.bankroll_state == "S5"
    def test_has_daily_strategy_summary(self, builder):
        s = builder.build("2026-06-11", 100.0)
        assert "state" in s.daily_strategy_summary
    def test_has_ev_ranking_summary(self, builder):
        s = builder.build("2026-06-11", 100.0)
        assert "candidate_count" in s.ev_ranking_summary
    def test_has_candidate_pools(self, builder):
        s = builder.build("2026-06-11", 100.0)
        pools = s.integrated_candidate_pools.get("pools", [])
        assert len(pools) == 4
    def test_value_zero_not_failure(self, builder):
        s = builder.build("2026-06-11", 100.0)
        assert s.ev_ranking_summary.get("value_candidate_count", -1) >= 0
    def test_safety_flags(self, builder):
        s = builder.build("2026-06-11", 100.0)
        assert s.safety["real_bet_execution"] is False
        assert s.safety["auto_betting"] is False
    def test_no_bookmaker(self, builder):
        s = builder.build("2026-06-11", 100.0)
        d = s.__dict__
        for k in d:
            assert "bookmaker" not in str(k).lower()
    def test_no_stake(self, builder):
        s = builder.build("2026-06-11", 100.0)
        d = s.__dict__
        for k in d:
            assert "stake" not in str(k).lower()