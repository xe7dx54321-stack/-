"""Daily unified strategy: main orchestrator connecting all Round 1-3 modules."""

from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import Optional

from worldcup_campaign.policy import (
    CampaignPolicy, load_campaign_policy, get_max_deployable_bankroll,
    get_required_multiplier,
)
from worldcup_campaign.bankroll_state import (
    BankrollState, load_bankroll_states, classify_bankroll_state,
    get_bucket_allocation_amounts,
)
from worldcup_campaign.stage_mapper import (
    StageDefinition, load_stage_map, classify_date,
)
from worldcup_campaign.match_registry import (
    MatchEntry, load_match_registry, get_matches_by_date,
    get_remaining_matches,
)
from worldcup_campaign.opportunity_window import (
    count_effective_windows,
)
from worldcup_campaign.strategy_profile import (
    StrategyProfileSelector, StrategyProfile,
)
from worldcup_campaign.match_strategy_labeler import (
    MatchStrategyLabeler, MatchLabel,
)
from worldcup_campaign.strategy_allocator import (
    StrategyAllocator, AllocationPlan, BucketAllocation,
)
from worldcup_campaign.scenario_preview import (
    ScenarioPreview, ScenarioOutcome,
)


@dataclass
class DailyUnifiedStrategy:
    # Basic info
    current_date: str
    current_stage: str
    strategy_profile: str
    
    # Bankroll
    current_bankroll: float
    target_bankroll: float
    state: str
    attack_level: str
    max_deployable: float
    deployed_total: float
    
    # Buckets
    bucket_amounts: dict[str, float]
    adjusted_bucket_amounts: dict[str, float]
    
    # Matches
    today_matches_count: int
    matches_remaining_count: int
    effective_windows_left: int
    
    # Strategy details
    strategy_profile_details: dict = field(default_factory=dict)
    allocation_plan: list[dict] = field(default_factory=list)
    match_labels: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    # Scenarios
    scenario_previews: list[dict] = field(default_factory=list)
    
    # Safety
    safety: dict = field(default_factory=dict)
    
    # Meta
    can_deploy: bool = True
    deploy_reason: str = ""


class DailyStrategyEngine:
    """Orchestrates all modules to produce a daily unified strategy."""

    def __init__(
        self,
        policy_path: str,
        states_path: str,
        stage_map_path: str,
        match_registry_path: str,
        strategy_rules_path: str,
        tagging_rules_path: str,
        scenario_rules_path: str,
    ):
        self.policy = load_campaign_policy(policy_path)
        self.states = load_bankroll_states(states_path)
        self.stages = load_stage_map(stage_map_path)
        self.matches = load_match_registry(match_registry_path)
        self.profile_selector = StrategyProfileSelector(strategy_rules_path)
        self.labeler = MatchStrategyLabeler(tagging_rules_path)
        self.allocator = StrategyAllocator()
        self.scenario_preview = ScenarioPreview(
            scenario_rules_path, states_path
        )

    def generate(self, target_date: date, current_bankroll: float) -> DailyUnifiedStrategy:
        """Generate the daily unified strategy for a given date and bankroll."""
        warnings = []
        
        # 1. Stage classification
        stage_def = classify_date(target_date, self.stages)
        
        # 2. Bankroll state
        state_result = classify_bankroll_state(
            current_bankroll, self.states, self.policy.target_bankroll
        )
        
        # 3. Bucket amounts (standard)
        bucket_amounts = get_bucket_allocation_amounts(
            current_bankroll, state_result
        )
        
        # 4. Max deployable
        max_deployable = get_max_deployable_bankroll(
            current_bankroll, self.policy
        )
        
        # 5. Select strategy profile
        profile = self.profile_selector.select_profile(
            stage_def.stage, state_result.state
        )
        
        # 6. Adjust bucket amounts based on profile
        # Only deployable buckets get their full amount
        adjusted = {}
        for bucket in ["reserve", "core", "edge", "attack", "futures"]:
            adjusted[bucket] = bucket_amounts.get(bucket, 0)
        
        # 7. Get today's matches
        today_matches = get_matches_by_date(target_date, self.matches)
        remaining = get_remaining_matches(target_date, self.matches)
        windows = count_effective_windows(target_date, self.matches)
        
        # 8. Label matches
        # Label all matches for today
        all_labeled = self.labeler.label_matches(today_matches, target_date)
        
        # 9. Allocation plan
        allocation = self.allocator.allocate(
            adjusted, profile, all_labeled
        )
        
        # Adjust deployed_total to respect max_deployable
        if allocation.total_deployed > max_deployable:
            warnings.append(
                f"Deployed ({allocation.total_deployed}) exceeds max ({max_deployable}), "
                f"capped at {max_deployable}"
            )
            # Scale down non-reserve buckets proportionally
            if allocation.total_deployed > 0:
                scale = max_deployable / allocation.total_deployed
                for b in allocation.buckets:
                    if b.is_active:
                        b.amount = round(b.amount * scale, 2)
        
        # Recalculate deployed total after adjustment
        deployed_total = sum(b.amount for b in allocation.buckets if b.is_active)
        
        # 10. Scenario previews
        scenarios = self.scenario_preview.generate_previews(
            current_bankroll, allocation, self.policy.target_bankroll
        )
        
        # 11. Format match labels
        match_label_dicts = []
        for ml in all_labeled:
            match_label_dicts.append({
                "match_id": ml.match_id,
                "match_number": ml.match_number,
                "home_team": ml.home_team,
                "away_team": ml.away_team,
                "stage": ml.stage,
                "group": ml.group,
                "is_knockout": ml.is_knockout,
                "labels": ml.labels,
                "eligible_buckets": ml.eligible_buckets,
                "risk_level": ml.risk_level,
            })
        
        # 12. Format allocation plan
        alloc_dicts = []
        for b in allocation.buckets:
            alloc_dicts.append({
                "bucket": b.bucket,
                "amount": b.amount,
                "eligible_match_count": b.eligible_match_count,
                "profile_weight": b.profile_weight,
                "is_active": b.is_active,
                "notes": b.notes,
            })
        
        # 13. Scenario dicts
        scenario_dicts = []
        for s in scenarios:
            scenario_dicts.append({
                "scenario_name": s.scenario_name,
                "description": s.description,
                "projected_bankroll": s.projected_bankroll,
                "projected_state": s.projected_state,
                "projected_attack_level": s.projected_attack_level,
                "projected_multiplier_remaining": s.projected_multiplier_remaining,
                "state_transition": s.state_transition,
                "urgency_impact": s.urgency_impact,
                "deployed_lost": s.deployed_lost,
                "deployed_won": s.deployed_won,
            })
        
        # 14. Safety flags
        safety = {
            "campaign_analysis_only": self.policy.campaign_analysis_only,
            "real_bet_execution": self.policy.real_bet_execution,
            "auto_betting": self.policy.auto_betting,
            "external_betting_api_allowed": self.policy.external_betting_api_allowed,
            "real_money_instruction_allowed": self.policy.real_money_instruction_allowed,
            "allow_empty_strategy": self.policy.allow_empty_strategy,
            "allow_not_full_deployment": self.policy.allow_not_full_deployment,
        }
        
        return DailyUnifiedStrategy(
            current_date=target_date.isoformat(),
            current_stage=stage_def.stage,
            strategy_profile=profile.name,
            current_bankroll=current_bankroll,
            target_bankroll=self.policy.target_bankroll,
            state=state_result.state,
            attack_level=state_result.attack_level,
            max_deployable=max_deployable,
            deployed_total=deployed_total,
            bucket_amounts=bucket_amounts,
            adjusted_bucket_amounts=adjusted,
            today_matches_count=len(today_matches),
            matches_remaining_count=len(remaining),
            effective_windows_left=windows,
            strategy_profile_details=self.profile_selector.get_profile_details(profile),
            allocation_plan=alloc_dicts,
            match_labels=match_label_dicts,
            warnings=warnings,
            scenario_previews=scenario_dicts,
            safety=safety,
            can_deploy=allocation.can_deploy and deployed_total > 0,
            deploy_reason=allocation.reason,
        )