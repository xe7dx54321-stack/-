"""Tests for bucket candidate policy."""
from pathlib import Path
import pytest
from worldcup_campaign.bucket_candidate_policy import BucketCandidatePolicy
def _cfg(f): return str(Path(__file__).resolve().parent.parent/"config"/f)

class TestBucketPolicy:
    @pytest.fixture
    def policy(self): return BucketCandidatePolicy(_cfg("bucket_candidate_policy.json"), _cfg("market_universe.json"))
    def test_reserve_no_candidates(self, policy):
        r = policy.is_allowed({"market_type":"1x2","mock_odds":2.0,"model_probability":0.5,"ev":0.0},"reserve")
        assert r.allowed is False
    def test_core_blocks_correct_score(self, policy):
        r = policy.is_allowed({"market_type":"correct_score","mock_odds":2.0,"model_probability":0.5,"ev":0.1},"core")
        assert r.allowed is False
    def test_core_blocks_lottery_odds(self, policy):
        r = policy.is_allowed({"market_type":"1x2","mock_odds":50.0,"model_probability":0.5,"ev":0.0},"core")
        assert r.allowed is False
    def test_attack_allows_correct_score(self, policy):
        r = policy.is_allowed({"market_type":"correct_score","mock_odds":10.0,"model_probability":0.05,"ev":0.0},"attack")
        assert r.allowed is True
    def test_attack_allows_high_odds(self, policy):
        r = policy.is_allowed({"market_type":"1x2","mock_odds":15.0,"model_probability":0.05,"ev":0.0},"attack")
        assert r.allowed is True
    def test_core_blocks_negative_ev(self, policy):
        r = policy.is_allowed({"market_type":"1x2","mock_odds":1.5,"model_probability":0.5,"ev":-0.1},"core")
        assert r.allowed is False
    def test_edge_allows_negative_ev(self, policy):
        r = policy.is_allowed({"market_type":"1x2","mock_odds":3.0,"model_probability":0.3,"ev":-0.1},"edge")
        assert r.allowed is True
    def test_get_allowed_buckets(self, policy):
        b = policy.get_allowed_buckets({"market_type":"1x2","mock_odds":2.5,"model_probability":0.5,"ev":0.05})
        assert "core" in b or "edge" in b
    def test_max_candidates(self, policy):
        assert policy.get_max_candidates("core") == 5
        assert policy.get_max_candidates("attack") == 10
    def test_unknown_bucket_fails(self, policy):
        with pytest.raises(ValueError): policy.is_allowed({"market_type":"1x2"},"invalid")