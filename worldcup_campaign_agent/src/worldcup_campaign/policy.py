"""Campaign policy management and validation."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CampaignPolicy:
    campaign_name: str
    initial_bankroll: float
    target_bankroll: float
    daily_max_deploy_ratio: float
    reserve_min_ratio: float
    campaign_analysis_only: bool
    real_bet_execution: bool
    auto_betting: bool
    external_betting_api_allowed: bool
    real_money_instruction_allowed: bool
    allow_empty_strategy: bool
    allow_not_full_deployment: bool
    currency: str


def load_campaign_policy(path: str) -> CampaignPolicy:
    """Load campaign policy from JSON file."""
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    policy = CampaignPolicy(
        campaign_name=raw["campaign_name"],
        initial_bankroll=float(raw["initial_bankroll"]),
        target_bankroll=float(raw["target_bankroll"]),
        daily_max_deploy_ratio=float(raw["daily_max_deploy_ratio"]),
        reserve_min_ratio=float(raw["reserve_min_ratio"]),
        campaign_analysis_only=bool(raw["campaign_analysis_only"]),
        real_bet_execution=bool(raw["real_bet_execution"]),
        auto_betting=bool(raw["auto_betting"]),
        external_betting_api_allowed=bool(raw["external_betting_api_allowed"]),
        real_money_instruction_allowed=bool(raw["real_money_instruction_allowed"]),
        allow_empty_strategy=bool(raw["allow_empty_strategy"]),
        allow_not_full_deployment=bool(raw["allow_not_full_deployment"]),
        currency=raw.get("currency", "CNY"),
    )
    validate_campaign_policy(policy)
    return policy


def validate_campaign_policy(policy: CampaignPolicy) -> None:
    """Validate campaign policy meets all safety boundaries."""
    # Safety boundaries - must fail if any real betting flag is true
    if policy.real_bet_execution:
        raise ValueError(
            "SAFETY VIOLATION: real_bet_execution is true. "
            "This system does not support real bet execution."
        )
    if policy.auto_betting:
        raise ValueError(
            "SAFETY VIOLATION: auto_betting is true. "
            "This system does not support automatic betting."
        )
    if policy.external_betting_api_allowed:
        raise ValueError(
            "SAFETY VIOLATION: external_betting_api_allowed is true. "
            "This system does not support external betting APIs."
        )
    if policy.real_money_instruction_allowed:
        raise ValueError(
            "SAFETY VIOLATION: real_money_instruction_allowed is true. "
            "This system does not support real money instructions."
        )
    # Deployment ratio must not exceed 0.5
    if policy.daily_max_deploy_ratio > 0.5:
        raise ValueError(
            f"SAFETY VIOLATION: daily_max_deploy_ratio ({policy.daily_max_deploy_ratio}) "
            "exceeds maximum of 0.5"
        )
    # Reserve ratio must be at least 0.5
    if policy.reserve_min_ratio < 0.5:
        raise ValueError(
            f"SAFETY VIOLATION: reserve_min_ratio ({policy.reserve_min_ratio}) "
            "is below minimum of 0.5"
        )


def get_max_deployable_bankroll(current_bankroll: float, policy: CampaignPolicy) -> float:
    """Calculate the maximum deployable amount given current bankroll."""
    if current_bankroll <= 0:
        raise ValueError("current_bankroll must be positive")
    return current_bankroll * policy.daily_max_deploy_ratio


def get_required_multiplier(current_bankroll: float, policy: CampaignPolicy) -> float:
    """Calculate how many times the current bankroll must grow to reach target."""
    if current_bankroll <= 0:
        raise ValueError("current_bankroll must be positive")
    return policy.target_bankroll / current_bankroll
