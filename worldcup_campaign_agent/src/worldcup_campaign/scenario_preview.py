"""Scenario preview: project bankroll state under different win/loss outcomes."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from worldcup_campaign.bankroll_state import (
    load_bankroll_states,
    classify_bankroll_state,
    BankrollStateResult,
)
from worldcup_campaign.strategy_allocator import AllocationPlan


@dataclass
class ScenarioOutcome:
    scenario_name: str
    description: str
    projected_bankroll: float
    projected_state: str
    projected_attack_level: str
    projected_multiplier_remaining: float
    state_transition: str
    urgency_impact: str
    deployed_lost: float
    deployed_won: float


class ScenarioPreview:
    """Generates what-if projections for different win/loss scenarios."""

    def __init__(self, scenario_rules_path: str, bankroll_states_path: str):
        self.rules = json.loads(
            Path(scenario_rules_path).read_text(encoding="utf-8-sig")
        )
        self.states = load_bankroll_states(bankroll_states_path)
        self.target = 1000000.0  # Default, can be overridden

    def generate_previews(
        self,
        current_bankroll: float,
        allocation_plan: AllocationPlan,
        target_bankroll: float,
    ) -> list[ScenarioOutcome]:
        """Generate scenario previews based on current allocation."""
        if target_bankroll:
            self.target = target_bankroll

        outcomes = []
        for scenario_def in self.rules.get("scenarios", []):
            name = scenario_def["name"]
            desc = scenario_def["description"]
            payback = scenario_def.get("bucket_payback", {})
            multiplier = scenario_def.get("bankroll_impact_multiplier", 1.0)
            transition = scenario_def.get("state_transition", "unknown")
            urgency = scenario_def.get("urgency_impact", "unknown")

            # Calculate projected bankroll
            deployed_lost = 0.0
            deployed_won = 0.0

            for bucket_alloc in allocation_plan.buckets:
                if not bucket_alloc.is_active:
                    continue
                bucket = bucket_alloc.bucket
                pb = payback.get(bucket, 0.0)
                if pb == 0.0:
                    deployed_lost += bucket_alloc.amount
                else:
                    deployed_won += bucket_alloc.amount * pb

            # Reserve is always kept
            reserve = allocation_plan.total_reserve
            projected = reserve + deployed_won

            # Classify projected state
            try:
                state_result = classify_bankroll_state(
                    projected, self.states, self.target
                )
                p_state = state_result.state
                p_attack = state_result.attack_level
            except ValueError:
                p_state = "UNKNOWN"
                p_attack = "unknown"

            # Projected multiplier remaining
            if projected > 0 and projected < self.target:
                p_mult = self.target / projected
            else:
                p_mult = 1.0

            outcomes.append(ScenarioOutcome(
                scenario_name=name,
                description=desc,
                projected_bankroll=round(projected, 2),
                projected_state=p_state,
                projected_attack_level=p_attack,
                projected_multiplier_remaining=round(p_mult, 2),
                state_transition=transition,
                urgency_impact=urgency,
                deployed_lost=round(deployed_lost, 2),
                deployed_won=round(deployed_won, 2),
            ))

        return outcomes