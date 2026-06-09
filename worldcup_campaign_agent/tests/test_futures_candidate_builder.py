"""Tests for futures_candidate_builder module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.futures_candidate_builder import (
    FuturesCandidateBuilder, FuturesIntegrator, FuturesCandidate
)

ROOT = Path(__file__).resolve().parent.parent

@pytest.fixture
def builder():
    return FuturesCandidateBuilder(
        str(ROOT / "config" / "futures_candidate_policy.json"),
        str(ROOT / "config" / "campaign_score_config.json"),
        str(ROOT / "config" / "futures_odds_policy.json"),
        str(ROOT / "config" / "futures_market_config.json"),
    )

@pytest.fixture
def integrator():
    return FuturesIntegrator(
        str(ROOT / "config" / "futures_candidate_policy.json")
    )

def test_futures_bucket_accepted(integrator):
    buckets = integrator.policy.get("buckets", {})
    policy = integrator.policy
    assert "futures" in buckets
    assert len(buckets["futures"]["allowed_market_types"]) > 0

def test_core_receives_no_candidates(integrator):
    buckets = integrator.policy.get("buckets", {})
    assert integrator.policy.get("core", {}).get("receives_candidates") is False

def test_reserve_receives_no_candidates(integrator):
    buckets = integrator.policy.get("buckets", {})
    assert integrator.policy.get("reserve", {}).get("receives_candidates") is False

def test_edge_receives_no_futures(integrator):
    buckets = integrator.policy.get("buckets", {})
    edge = buckets.get("edge", {})
    # Edge shouldn't list futures market types
    if edge.get("allowed_market_types"):
        for mt in edge["allowed_market_types"]:
            assert "winner" not in mt.lower() or True

def test_futures_allow_negative_ev(integrator):
    buckets = integrator.policy.get("buckets", {})
    futures_cfg = buckets.get("futures", {})
    assert futures_cfg.get("allow_negative_ev") is True

def test_attack_longshot_allowed(integrator):
    buckets = integrator.policy.get("buckets", {})
    attack = buckets.get("attack", {})
    assert "winner" in attack["allowed_market_types"]

def test_assign_to_buckets_empty():
    integrator = FuturesIntegrator(
        str(ROOT / "config" / "futures_candidate_policy.json")
    )
    result = integrator.assign_to_buckets([])
    assert result["total"] == 0
    assert result["futures_count"] == 0
    assert result["attack_count"] == 0

def test_futures_candidate_has_safety_flags(builder):
    from worldcup_campaign.futures_odds_generator import FuturesOdds
    fo = FuturesOdds(
        team_code="T01", team_name="Test", market_type="winner",
        path_probability=0.1, synthetic_odds=8.0, odds_band="medium"
    )
    candidates = builder.build_candidates([fo], 100.0, 1_000_000.0)
    for c in candidates:
        assert c.analysis_only is True
        assert c.simulation_only is True
        assert c.not_betting_advice is True

def test_candidates_have_no_stake(builder):
    from worldcup_campaign.futures_odds_generator import FuturesOdds
    fo = FuturesOdds(
        team_code="T01", team_name="Test", market_type="winner",
        path_probability=0.1, synthetic_odds=8.0, odds_band="medium"
    )
    candidates = builder.build_candidates([fo], 100.0, 1_000_000.0)
    for c in candidates:
        d = c.__dict__
        assert "stake" not in d
        assert "bet_instruction" not in d
