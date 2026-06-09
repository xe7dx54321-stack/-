"""Tests for parlay_candidate_builder module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.parlay_candidate_builder import ParlayCandidateBuilder, ParlayLeg
from worldcup_campaign.parlay_candidate_builder import ParlayCandidate

ROOT = Path(__file__).resolve().parent.parent
OPT_CONFIG = str(ROOT / "config" / "parlay_optimizer_config.json")
CORR_POLICY = str(ROOT / "config" / "parlay_correlation_policy.json")


def make_leg(match_id, decimal_odds, model_probability, ev=0.0, edge=0.0, source_bucket="edge", market_type="1x2"):
    return ParlayLeg(
        source_candidate_id=f"C_{match_id}",
        match_id=match_id,
        match_number=1,
        decimal_odds=decimal_odds,
        model_probability=model_probability,
        ev=ev, edge=edge,
        market_type=market_type,
        source_bucket=source_bucket,
        leg_role="balanced",
    )


class TestLegRoleClassification:
    def test_core_bucket_becomes_base(self):
        builder = ParlayCandidateBuilder(OPT_CONFIG, CORR_POLICY)
        c = {"mock_odds": 2.0, "model_probability": 0.5, "source_bucket": "core"}
        assert builder._classify_role(c) == "base"

    def test_high_prob_low_odds_becomes_base(self):
        builder = ParlayCandidateBuilder(OPT_CONFIG, CORR_POLICY)
        c = {"mock_odds": 2.5, "model_probability": 0.35, "source_bucket": "edge"}
        role = builder._classify_role(c)
        assert role == "base"

    def test_high_odds_becomes_attack(self):
        builder = ParlayCandidateBuilder(OPT_CONFIG, CORR_POLICY)
        c = {"mock_odds": 10.0, "model_probability": 0.1, "source_bucket": "attack"}
        role = builder._classify_role(c)
        assert role == "attack"

    def test_low_prob_becomes_attack(self):
        builder = ParlayCandidateBuilder(OPT_CONFIG, CORR_POLICY)
        c = {"mock_odds": 5.0, "model_probability": 0.03, "source_bucket": "attack"}
        role = builder._classify_role(c)
        assert role == "attack"


class TestGenerateCombinations:
    def test_generates_2_leg_combos(self):
        builder = ParlayCandidateBuilder(OPT_CONFIG, CORR_POLICY)
        legs = [make_leg("M001", 2.0, 0.5), make_leg("M002", 2.5, 0.4), make_leg("M003", 1.8, 0.6)]
        combos = builder.generate_combinations(legs)
        # Check there are 2-leg combos
        two_legs = [c for c in combos if len(c) == 2]
        assert len(two_legs) > 0

    def test_generates_3_leg_combos(self):
        builder = ParlayCandidateBuilder(OPT_CONFIG, CORR_POLICY)
        legs = [make_leg(f"M{i:03d}", 2.0, 0.5) for i in range(1, 5)]
        combos = builder.generate_combinations(legs)
        three_legs = [c for c in combos if len(c) == 3]
        assert len(three_legs) > 0

    def test_generates_4_leg_combos(self):
        builder = ParlayCandidateBuilder(OPT_CONFIG, CORR_POLICY)
        legs = [make_leg(f"M{i:03d}", 2.0, 0.5) for i in range(1, 6)]
        combos = builder.generate_combinations(legs)
        four_legs = [c for c in combos if len(c) == 4]
        assert len(four_legs) > 0

    def test_does_not_generate_5_leg_combos(self):
        builder = ParlayCandidateBuilder(OPT_CONFIG, CORR_POLICY)
        legs = [make_leg(f"M{i:03d}", 2.0, 0.5) for i in range(1, 7)]
        combos = builder.generate_combinations(legs)
        five_legs = [c for c in combos if len(c) == 5]
        assert len(five_legs) == 0

    def test_does_not_exceed_max_raw_combinations(self):
        builder = ParlayCandidateBuilder(OPT_CONFIG, CORR_POLICY)
        legs = [make_leg(f"M{i:03d}", 2.0, 0.5) for i in range(1, 50)]
        combos = builder.generate_combinations(legs)
        assert len(combos) <= builder.max_raw


class TestBuildCandidate:
    def test_build_valid_candidate(self):
        builder = ParlayCandidateBuilder(OPT_CONFIG, CORR_POLICY)
        legs = [
            make_leg("M001", 2.0, 0.5, source_bucket="core"),
            make_leg("M002", 3.0, 0.4, source_bucket="edge"),
        ]
        candidate = builder.build_candidate(tuple(legs), 100.0, 1_000_000.0)
        assert candidate is not None
        assert candidate.leg_count == 2
        assert candidate.combined_odds == pytest.approx(6.0, rel=0.01)
        assert candidate.analysis_only is True
        assert candidate.simulation_only is True
        assert candidate.not_betting_advice is True

    def test_same_match_blocked_returns_none(self):
        builder = ParlayCandidateBuilder(OPT_CONFIG, CORR_POLICY)
        legs = [
            make_leg("M001", 2.0, 0.5),
            make_leg("M001", 3.0, 0.4),
        ]
        candidate = builder.build_candidate(tuple(legs), 100.0, 1_000_000.0)
        assert candidate is None

    def test_candidate_contains_combined_odds_probability_ev(self):
        builder = ParlayCandidateBuilder(OPT_CONFIG, CORR_POLICY)
        legs = [
            make_leg("M001", 2.0, 0.6, source_bucket="edge"),
            make_leg("M002", 1.8, 0.5, source_bucket="edge"),
        ]
        candidate = builder.build_candidate(tuple(legs), 100.0, 1_000_000.0)
        assert candidate is not None
        assert candidate.combined_odds > 1.0
        assert 0 <= candidate.combined_model_probability <= 1.0
        assert isinstance(candidate.combined_ev, float)

    def test_no_stake_in_candidate(self):
        builder = ParlayCandidateBuilder(OPT_CONFIG, CORR_POLICY)
        legs = [
            make_leg("M001", 2.0, 0.5),
            make_leg("M002", 3.0, 0.4),
        ]
        candidate = builder.build_candidate(tuple(legs), 100.0, 1_000_000.0)
        assert candidate is not None
        d = candidate.__dict__
        assert "stake" not in d
        assert "stake_amount" not in d
        assert "bet_instruction" not in d

    def test_low_odds_base_leg_allowed(self):
        builder = ParlayCandidateBuilder(OPT_CONFIG, CORR_POLICY)
        legs = [
            make_leg("M001", 1.5, 0.6, source_bucket="core"),
            make_leg("M002", 5.0, 0.2, source_bucket="attack"),
        ]
        candidate = builder.build_candidate(tuple(legs), 100.0, 1_000_000.0)
        assert candidate is not None

    def test_low_probability_high_odds_leg_allowed(self):
        builder = ParlayCandidateBuilder(OPT_CONFIG, CORR_POLICY)
        legs = [
            make_leg("M001", 2.0, 0.5, source_bucket="edge"),
            make_leg("M002", 50.0, 0.01, source_bucket="attack"),
        ]
        candidate = builder.build_candidate(tuple(legs), 100.0, 1_000_000.0)
        assert candidate is not None
