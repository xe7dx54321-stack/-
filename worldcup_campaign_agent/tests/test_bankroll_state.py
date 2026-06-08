"""Tests for bankroll state machine."""

import json
from pathlib import Path

import pytest

from worldcup_campaign.bankroll_state import (
    BankrollState,
    BankrollStateResult,
    load_bankroll_states,
    validate_bankroll_states,
    classify_bankroll_state,
    get_bucket_allocation_amounts,
)


def _config_path(filename: str) -> str:
    return str(
        Path(__file__).resolve().parent.parent / "config" / filename
    )


class TestLoadBankrollStates:
    """Tests for loading bankroll states."""

    def test_load_valid_states(self):
        """Valid states should load without error."""
        states = load_bankroll_states(_config_path("bankroll_states.json"))
        assert len(states) == 8
        state_names = [s.state for s in states]
        assert state_names == ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7"]


class TestValidateBankrollStates:
    """Tests for bankroll state validation."""

    def test_bucket_sum_equals_1(self):
        """Each state bucket allocation must sum to 1."""
        states = load_bankroll_states(_config_path("bankroll_states.json"))
        for s in states:
            total = sum(s.bucket_allocation.values())
            assert abs(total - 1.0) < 0.001, f"State {s.state} bucket sum is {total}"

    def test_reserve_gte_50_percent(self):
        """Each state must have reserve >= 0.5."""
        states = load_bankroll_states(_config_path("bankroll_states.json"))
        for s in states:
            assert s.bucket_allocation["reserve"] >= 0.5, (
                f"State {s.state} reserve is {s.bucket_allocation['reserve']}"
            )

    def test_deployed_lte_50_percent(self):
        """Non-reserve (deployed) must be <= 0.5."""
        states = load_bankroll_states(_config_path("bankroll_states.json"))
        for s in states:
            deployed = sum(
                v for k, v in s.bucket_allocation.items() if k != "reserve"
            )
            assert deployed <= 0.5, (
                f"State {s.state} deployed is {deployed}"
            )

    def test_duplicate_state_name_fails(self):
        """Duplicate state names should fail validation."""
        states = [
            BankrollState("S1", 0, 50, "test", "high", {"reserve": 0.5, "core": 0.1, "edge": 0.1, "attack": 0.25, "futures": 0.05}),
            BankrollState("S1", 50, 100, "test2", "high", {"reserve": 0.5, "core": 0.1, "edge": 0.15, "attack": 0.2, "futures": 0.05}),
        ]
        with pytest.raises(ValueError, match="Duplicate"):
            validate_bankroll_states(states)

    def test_bucket_sum_not_1_fails(self):
        """Bucket allocation not summing to 1 should fail."""
        states = [
            BankrollState("S0", 0, 50, "test", "high", {"reserve": 0.5, "core": 0.0, "edge": 0.0, "attack": 0.0, "futures": 0.0}),
        ]
        with pytest.raises(ValueError, match="bucket allocation sum"):
            validate_bankroll_states(states)


class TestClassifyBankrollState:
    """Tests for bankroll state classification."""

    @pytest.fixture
    def states(self):
        return load_bankroll_states(_config_path("bankroll_states.json"))

    def test_49_is_S0(self, states):
        result = classify_bankroll_state(49.0, states, 1000000.0)
        assert result.state == "S0"

    def test_50_is_S1(self, states):
        result = classify_bankroll_state(50.0, states, 1000000.0)
        assert result.state == "S1"

    def test_100_is_S2(self, states):
        result = classify_bankroll_state(100.0, states, 1000000.0)
        assert result.state == "S2"

    def test_300_is_S3(self, states):
        result = classify_bankroll_state(300.0, states, 1000000.0)
        assert result.state == "S3"

    def test_1000_is_S4(self, states):
        result = classify_bankroll_state(1000.0, states, 1000000.0)
        assert result.state == "S4"

    def test_5000_is_S5(self, states):
        result = classify_bankroll_state(5000.0, states, 1000000.0)
        assert result.state == "S5"

    def test_20000_is_S6(self, states):
        result = classify_bankroll_state(20000.0, states, 1000000.0)
        assert result.state == "S6"

    def test_100000_is_S7(self, states):
        result = classify_bankroll_state(100000.0, states, 1000000.0)
        assert result.state == "S7"

    def test_target_reached(self, states):
        result = classify_bankroll_state(1000000.0, states, 1000000.0)
        assert result.state == "TARGET_REACHED"
        assert result.is_target_reached is True

    def test_above_target_reached(self, states):
        result = classify_bankroll_state(2000000.0, states, 1000000.0)
        assert result.state == "TARGET_REACHED"

    def test_negative_bankroll_fails(self, states):
        with pytest.raises(ValueError, match="negative"):
            classify_bankroll_state(-10.0, states, 1000000.0)

    def test_boundary_99_is_S1(self, states):
        """99 should be S1 (in [50, 100))."""
        result = classify_bankroll_state(99.0, states, 1000000.0)
        assert result.state == "S1"

    def test_boundary_299_is_S2(self, states):
        """299 should be S2 (in [100, 300))."""
        result = classify_bankroll_state(299.0, states, 1000000.0)
        assert result.state == "S2"


class TestBucketAllocationAmounts:
    """Tests for bucket allocation amounts."""

    @pytest.fixture
    def states(self):
        return load_bankroll_states(_config_path("bankroll_states.json"))

    def test_100_bucket_amounts(self, states):
        """Bankroll 100 in S2 should produce correct amounts."""
        result = classify_bankroll_state(100.0, states, 1000000.0)
        amounts = get_bucket_allocation_amounts(100.0, result)
        assert amounts["reserve"] == 50.0
        assert amounts["core"] == 10.0
        assert amounts["edge"] == 15.0
        assert amounts["attack"] == 20.0
        assert amounts["futures"] == 5.0

    def test_bucket_amounts_sum_to_bankroll(self, states):
        """Sum of bucket amounts should equal current bankroll."""
        for bankroll in [49, 50, 100, 300, 500, 1000, 5000, 20000, 100000]:
            result = classify_bankroll_state(float(bankroll), states, 1000000.0)
            amounts = get_bucket_allocation_amounts(float(bankroll), result)
            total = sum(amounts.values())
            assert abs(total - bankroll) < 0.02, f"Bankroll {bankroll}: sum {total} != {bankroll}"

    def test_reserve_gte_50_percent_amounts(self, states):
        """Reserve amount must be >= 50% of bankroll."""
        for bankroll in [50, 100, 300, 1000, 5000]:
            result = classify_bankroll_state(float(bankroll), states, 1000000.0)
            amounts = get_bucket_allocation_amounts(float(bankroll), result)
            assert amounts["reserve"] >= bankroll * 0.5

    def test_deployed_lte_50_percent_amounts(self, states):
        """Deployed amount must be <= 50% of bankroll."""
        for bankroll in [50, 100, 300, 1000, 5000]:
            result = classify_bankroll_state(float(bankroll), states, 1000000.0)
            amounts = get_bucket_allocation_amounts(float(bankroll), result)
            deployed = sum(v for k, v in amounts.items() if k != "reserve")
            assert deployed <= bankroll * 0.5
