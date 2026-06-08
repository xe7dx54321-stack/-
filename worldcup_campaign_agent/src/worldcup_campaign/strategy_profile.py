"""Strategy profile selector: choose profile based on stage + bankroll state."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class StrategyProfile:
    name: str
    description: str
    attack_allocation_weight: float
    edge_allocation_weight: float
    core_allocation_weight: float
    futures_allocation_weight: float
    allow_attack: bool
    allow_edge: bool
    allow_core: bool
    allow_futures: bool
    max_matches_per_day: int


class StrategyProfileSelector:
    """Selects a strategy profile based on stage and bankroll state."""

    def __init__(self, rules_path: str):
        self.rules = json.loads(Path(rules_path).read_text(encoding="utf-8-sig"))
        self._profiles = {}
        for name, data in self.rules["strategy_profiles"].items():
            self._profiles[name] = StrategyProfile(
                name=name,
                description=data["description"],
                attack_allocation_weight=data["attack_allocation_weight"],
                edge_allocation_weight=data["edge_allocation_weight"],
                core_allocation_weight=data["core_allocation_weight"],
                futures_allocation_weight=data["futures_allocation_weight"],
                allow_attack=data["allow_attack"],
                allow_edge=data["allow_edge"],
                allow_core=data["allow_core"],
                allow_futures=data["allow_futures"],
                max_matches_per_day=data["max_matches_per_day"],
            )

    def select_profile(self, stage: str, bankroll_state: str) -> StrategyProfile:
        """Select strategy profile based on stage and bankroll state.
        
        Bankroll state overrides take precedence over stage defaults.
        """
        # Check bankroll state override first
        overrides = self.rules.get("bankroll_state_profile_override", {})
        if bankroll_state in overrides:
            profile_name = overrides[bankroll_state]
            if profile_name in self._profiles:
                return self._profiles[profile_name]

        # Fall back to stage-based mapping
        stage_mapping = self.rules.get("stage_profile_mapping", {})
        profile_name = stage_mapping.get(stage, "conservative")
        if profile_name in self._profiles:
            return self._profiles[profile_name]

        # Ultimate fallback
        return self._profiles.get("conservative",
            StrategyProfile("conservative", "Fallback", 0, 0, 1, 0, False, False, True, False, 1))

    def get_profile_details(self, profile: StrategyProfile) -> dict:
        """Get profile details as a dict for serialization."""
        return {
            "name": profile.name,
            "description": profile.description,
            "attack_allocation_weight": profile.attack_allocation_weight,
            "edge_allocation_weight": profile.edge_allocation_weight,
            "core_allocation_weight": profile.core_allocation_weight,
            "futures_allocation_weight": profile.futures_allocation_weight,
            "allow_attack": profile.allow_attack,
            "allow_edge": profile.allow_edge,
            "allow_core": profile.allow_core,
            "allow_futures": profile.allow_futures,
            "max_matches_per_day": profile.max_matches_per_day,
        }