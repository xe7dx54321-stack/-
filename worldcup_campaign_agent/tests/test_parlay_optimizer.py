"""Tests for parlay_optimizer module."""
import sys, json, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.parlay_optimizer import ParlayOptimizer, ParlayBucketPools
from worldcup_campaign.parlay_candidate_builder import ParlayCandidate

ROOT = Path(__file__).resolve().parent.parent
OPT_CONFIG = str(ROOT / "config" / "parlay_optimizer_config.json")
BUCKET_POLICY = str(ROOT / "config" / "parlay_bucket_policy.json")


def make_candidate(parlay_id, leg_count, combined_odds, combined_prob, combined_ev, band, score, eligible_bucket="edge"):
    return ParlayCandidate(
        parlay_id=parlay_id,
        leg_count=leg_count,
        parlay_type="base_plus_edge",
        legs=[],
        combined_odds=combined_odds,
        combined_model_probability=combined_prob,
        combined_ev=combined_ev,
        combined_odds_band=band,
        target_contribution_preview=0.0,
        correlation_result={"is_blocked": False, "penalty_score": 0.0, "warnings": [], "reason_codes": []},
        parlay_campaign_score=score,
        parlay_tier="campaign_candidate",
        eligible_bucket=eligible_bucket,
        warnings=[],
    )


class TestLoadConfig:
    def test_optimizer_config_loads(self):
        opt = ParlayOptimizer(OPT_CONFIG, BUCKET_POLICY)
        assert opt.config is not None
        assert opt.bucket_policy is not None


class TestRank:
    def test_rank_sorts_by_campaign_score(self):
        opt = ParlayOptimizer(OPT_CONFIG, BUCKET_POLICY)
        candidates = [
            make_candidate("P1", 2, 5.0, 0.2, -0.1, "medium", 0.3),
            make_candidate("P2", 2, 10.0, 0.1, 0.0, "high", 0.5),
            make_candidate("P3", 3, 20.0, 0.05, 0.1, "high", 0.2),
        ]
        ranked = opt.rank(candidates)
        assert ranked[0].parlay_id == "P2"
        assert ranked[-1].parlay_id == "P3"

    def test_rank_respects_max_ranked(self):
        opt = ParlayOptimizer(OPT_CONFIG, BUCKET_POLICY)
        candidates = [make_candidate(f"P{i}", 2, 5.0, 0.2, 0.0, "medium", 0.1 * i) for i in range(200)]
        ranked = opt.rank(candidates)
        assert len(ranked) <= opt.config["ranking"]["max_ranked_parlays"]

    def test_rank_handles_empty(self):
        opt = ParlayOptimizer(OPT_CONFIG, BUCKET_POLICY)
        ranked = opt.rank([])
        assert ranked == []


class TestAssignToBuckets:
    def test_edge_only_2_leg(self):
        opt = ParlayOptimizer(OPT_CONFIG, BUCKET_POLICY)
        candidates = [
            make_candidate("P1", 2, 5.0, 0.2, 0.0, "medium", 0.6),
        ]
        ranked = opt.rank(candidates)
        pools = opt.assign_to_buckets(ranked)
        assert len(pools.edge_parlays) >= 1
        for e in pools.edge_parlays:
            assert e["leg_count"] == 2

    def test_attack_2_3_4_leg(self):
        opt = ParlayOptimizer(OPT_CONFIG, BUCKET_POLICY)
        candidates = [
            make_candidate("P2", 2, 20.0, 0.05, 0.1, "high", 0.4),
            make_candidate("P3", 3, 100.0, 0.01, 0.2, "very_high", 0.5),
            make_candidate("P4", 4, 200.0, 0.005, 0.3, "lottery", 0.3),
        ]
        ranked = opt.rank(candidates)
        pools = opt.assign_to_buckets(ranked)
        for a in pools.attack_parlays:
            assert a["leg_count"] in [2, 3, 4]

    def test_core_not_in_policy(self):
        opt = ParlayOptimizer(OPT_CONFIG, BUCKET_POLICY)
        bp = opt.bucket_policy
        core_policy = bp.get("core", {})
        assert core_policy.get("allowed_parlay_types") == []
        assert core_policy.get("allowed_leg_counts") == []

    def test_reserve_not_in_policy(self):
        opt = ParlayOptimizer(OPT_CONFIG, BUCKET_POLICY)
        bp = opt.bucket_policy
        reserve_policy = bp.get("reserve", {})
        assert reserve_policy.get("receives_candidates") is False

    def test_futures_not_in_policy(self):
        opt = ParlayOptimizer(OPT_CONFIG, BUCKET_POLICY)
        bp = opt.bucket_policy
        futures_policy = bp.get("futures", {})
        assert futures_policy.get("allowed_parlay_types") == []

    def test_empty_candidates_no_fail(self):
        opt = ParlayOptimizer(OPT_CONFIG, BUCKET_POLICY)
        pools = opt.assign_to_buckets([])
        assert pools.edge_parlays == []
        assert pools.attack_parlays == []


class TestAnalysisOnly:
    def test_not_betting_advice_always_true(self):
        opt = ParlayOptimizer(OPT_CONFIG, BUCKET_POLICY)
        assert opt.config["not_betting_advice"] is True
        assert opt.config["analysis_only"] is True
