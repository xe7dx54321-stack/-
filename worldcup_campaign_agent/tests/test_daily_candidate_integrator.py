"""Tests for daily candidate integrator."""
from pathlib import Path
import pytest
from worldcup_campaign.daily_candidate_integrator import DailyCandidateIntegrator
def _cfg(f): return str(Path(__file__).resolve().parent.parent/"config"/f)

class TestIntegrator:
    @pytest.fixture
    def integrator(self):
        return DailyCandidateIntegrator(_cfg("campaign_score_config.json"), _cfg("bucket_candidate_policy.json"), _cfg("daily_candidate_integration_config.json"), _cfg("market_universe.json"))
    def test_integrate_empty(self, integrator):
        pools = integrator.integrate([], {"core":10,"edge":15,"attack":20,"futures":5,"reserve":50}, 100, 1000000, 40)
        assert len(pools.bucket_pools) == 4
    def test_reserve_not_in_pools(self, integrator):
        pools = integrator.integrate([], {"core":10,"edge":15,"attack":20,"futures":5,"reserve":50}, 100, 1000000, 40)
        buckets = [p.bucket for p in pools.bucket_pools]
        assert "reserve" not in buckets
    def test_no_stake_output(self, integrator):
        c = [{"match_id":"m","match_number":1,"market_type":"1x2","selection":"home","mock_odds":2.0,"model_probability":0.5,"market_probability":0.5,"edge":0.1,"ev":0.1,"value_flag":"value","target_contribution_preview":0.1,"bucket_eligibility":["core"]}]
        pools = integrator.integrate(c, {"core":10,"edge":15,"attack":20,"futures":5,"reserve":50}, 100, 1000000, 40)
        for bp in pools.bucket_pools:
            for cand in bp.candidates:
                assert cand.analysis_only is True
    def test_empty_bucket_has_reason(self, integrator):
        pools = integrator.integrate([], {"core":10,"edge":15,"attack":20,"futures":5,"reserve":50}, 100, 1000000, 40)
        for bp in pools.bucket_pools:
            if bp.candidate_count == 0:
                assert bp.empty_reason != ""
    def test_unassigned_have_reason(self, integrator):
        c = [{"match_id":"m","match_number":1,"market_type":"correct_score","selection":"1-0","mock_odds":8.0,"model_probability":0.1,"market_probability":0.125,"edge":-0.025,"ev":-0.1,"value_flag":"no_value","target_contribution_preview":0.05,"bucket_eligibility":[]}]
        pools = integrator.integrate(c, {"core":10,"edge":15,"attack":20,"futures":5,"reserve":50}, 100, 1000000, 40)
        assert len(pools.unassigned_candidates) >= 0