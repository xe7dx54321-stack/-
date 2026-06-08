"""Bankroll state machine: S0-S7 classification and bucket allocation."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


VALID_BUCKETS = ["reserve", "core", "edge", "attack", "futures"]


@dataclass
class BankrollState:
    state: str
    min_bankroll: float
    max_bankroll: float
    description: str
    attack_level: str
    bucket_allocation: dict


@dataclass
class BankrollStateResult:
    state: str
    attack_level: str
    description: str
    bucket_allocation: dict
    is_target_reached: bool = False


def load_bankroll_states(path: str) -> list[BankrollState]:
    """Load bankroll states from JSON file."""
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    states = []
    for entry in raw:
        state = BankrollState(
            state=entry["state"],
            min_bankroll=float(entry["min_bankroll"]),
            max_bankroll=float(entry["max_bankroll"]),
            description=entry["description"],
            attack_level=entry["attack_level"],
            bucket_allocation=entry["bucket_allocation"],
        )
        states.append(state)
    validate_bankroll_states(states)
    return states


def validate_bankroll_states(states: list[BankrollState]) -> None:
    """Validate all bankroll states are well-formed."""
    state_names = set()
    for s in states:
        # Check unique state names
        if s.state in state_names:
            raise ValueError(f"Duplicate state: {s.state}")
        state_names.add(s.state)

        # Check bucket sum equals 1
        total = sum(s.bucket_allocation.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"State {s.state}: bucket allocation sum is {total}, must be 1.0"
            )

        # Check reserve >= 0.5
        if s.bucket_allocation.get("reserve", 0) < 0.5:
            raise ValueError(
                f"State {s.state}: reserve ({s.bucket_allocation.get('reserve', 0)}) "
                "is below minimum of 0.5"
            )

        # Check non-reserve sum <= 0.5
        non_reserve = sum(
            v for k, v in s.bucket_allocation.items() if k != "reserve"
        )
        if non_reserve > 0.5:
            raise ValueError(
                f"State {s.state}: non-reserve allocation ({non_reserve}) exceeds 0.5"
            )

        # Check all bucket keys are valid
        for bucket in s.bucket_allocation:
            if bucket not in VALID_BUCKETS:
                raise ValueError(
                    f"State {s.state}: unknown bucket '{bucket}'"
                )

        # Check min < max
        if s.min_bankroll >= s.max_bankroll:
            raise ValueError(
                f"State {s.state}: min_bankroll ({s.min_bankroll}) must be "
                f"less than max_bankroll ({s.max_bankroll})"
            )


def classify_bankroll_state(
    current_bankroll: float,
    states: list[BankrollState],
    target_bankroll: float,
) -> BankrollStateResult:
    """Classify current bankroll into a state (S0-S7) or TARGET_REACHED."""
    if current_bankroll < 0:
        raise ValueError("current_bankroll cannot be negative")

    # Check if target reached
    if current_bankroll >= target_bankroll:
        return BankrollStateResult(
            state="TARGET_REACHED",
            attack_level="target_achieved",
            description="Target bankroll reached or exceeded",
            bucket_allocation={
                "reserve": 1.0,
                "core": 0.0,
                "edge": 0.0,
                "attack": 0.0,
                "futures": 0.0,
            },
            is_target_reached=True,
        )

    # Boundary: [min_bankroll, max_bankroll)
    # 0 -> S0, 50 -> S1, 100 -> S2, etc.
    for s in states:
        if s.min_bankroll <= current_bankroll < s.max_bankroll:
            return BankrollStateResult(
                state=s.state,
                attack_level=s.attack_level,
                description=s.description,
                bucket_allocation=s.bucket_allocation,
                is_target_reached=False,
            )

    # Fallback: if above all state maxes but below target, use last state
    raise ValueError(
        f"Could not classify bankroll {current_bankroll}. "
        f"Target: {target_bankroll}"
    )


def get_bucket_allocation_amounts(
    current_bankroll: float, state: BankrollStateResult
) -> dict[str, float]:
    """Calculate actual dollar amounts per bucket given current bankroll."""
    amounts = {}
    for bucket, ratio in state.bucket_allocation.items():
        amounts[bucket] = round(current_bankroll * ratio, 2)
    return amounts
