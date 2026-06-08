"""Tests for campaign policy module."""

import json
import tempfile
from pathlib import Path

import pytest

from worldcup_campaign.policy import (
    CampaignPolicy,
    load_campaign_policy,
    validate_campaign_policy,
    get_max_deployable_bankroll,
    get_required_multiplier,
)


# Helper: get path to config file
def _config_path(filename: str) -> str:
    return str(
        Path(__file__).resolve().parent.parent / "config" / filename
    )


class TestLoadCampaignPolicy:
    """Tests for loading and validating campaign policy."""

    def test_load_valid_policy(self):
        """Policy should load successfully from the real config."""
        policy = load_campaign_policy(_config_path("campaign_policy.json"))
        assert policy.campaign_name == "worldcup_2026_high_odds_campaign"
        assert policy.initial_bankroll == 100.0
        assert policy.target_bankroll == 1000000.0
        assert policy.daily_max_deploy_ratio == 0.5
        assert policy.reserve_min_ratio == 0.5
        assert policy.campaign_analysis_only is True
        assert policy.real_bet_execution is False
        assert policy.auto_betting is False
        assert policy.external_betting_api_allowed is False
        assert policy.real_money_instruction_allowed is False

    def test_real_bet_execution_true_fails(self):
        """real_bet_execution=true must fail."""
        policy = CampaignPolicy(
            campaign_name="test", initial_bankroll=100, target_bankroll=1000000,
            daily_max_deploy_ratio=0.5, reserve_min_ratio=0.5,
            campaign_analysis_only=True, real_bet_execution=True,
            auto_betting=False, external_betting_api_allowed=False,
            real_money_instruction_allowed=False,
            allow_empty_strategy=True, allow_not_full_deployment=True,
            currency="CNY",
        )
        with pytest.raises(ValueError, match="real_bet_execution"):
            validate_campaign_policy(policy)

    def test_auto_betting_true_fails(self):
        """auto_betting=true must fail."""
        policy = CampaignPolicy(
            campaign_name="test", initial_bankroll=100, target_bankroll=1000000,
            daily_max_deploy_ratio=0.5, reserve_min_ratio=0.5,
            campaign_analysis_only=True, real_bet_execution=False,
            auto_betting=True, external_betting_api_allowed=False,
            real_money_instruction_allowed=False,
            allow_empty_strategy=True, allow_not_full_deployment=True,
            currency="CNY",
        )
        with pytest.raises(ValueError, match="auto_betting"):
            validate_campaign_policy(policy)

    def test_external_betting_api_allowed_true_fails(self):
        """external_betting_api_allowed=true must fail."""
        policy = CampaignPolicy(
            campaign_name="test", initial_bankroll=100, target_bankroll=1000000,
            daily_max_deploy_ratio=0.5, reserve_min_ratio=0.5,
            campaign_analysis_only=True, real_bet_execution=False,
            auto_betting=False, external_betting_api_allowed=True,
            real_money_instruction_allowed=False,
            allow_empty_strategy=True, allow_not_full_deployment=True,
            currency="CNY",
        )
        with pytest.raises(ValueError, match="external_betting_api"):
            validate_campaign_policy(policy)

    def test_real_money_instruction_allowed_true_fails(self):
        """real_money_instruction_allowed=true must fail."""
        policy = CampaignPolicy(
            campaign_name="test", initial_bankroll=100, target_bankroll=1000000,
            daily_max_deploy_ratio=0.5, reserve_min_ratio=0.5,
            campaign_analysis_only=True, real_bet_execution=False,
            auto_betting=False, external_betting_api_allowed=False,
            real_money_instruction_allowed=True,
            allow_empty_strategy=True, allow_not_full_deployment=True,
            currency="CNY",
        )
        with pytest.raises(ValueError, match="real_money_instruction"):
            validate_campaign_policy(policy)

    def test_daily_max_deploy_ratio_too_high_fails(self):
        """daily_max_deploy_ratio > 0.5 must fail."""
        policy = CampaignPolicy(
            campaign_name="test", initial_bankroll=100, target_bankroll=1000000,
            daily_max_deploy_ratio=0.6, reserve_min_ratio=0.5,
            campaign_analysis_only=True, real_bet_execution=False,
            auto_betting=False, external_betting_api_allowed=False,
            real_money_instruction_allowed=False,
            allow_empty_strategy=True, allow_not_full_deployment=True,
            currency="CNY",
        )
        with pytest.raises(ValueError, match="daily_max_deploy_ratio"):
            validate_campaign_policy(policy)

    def test_reserve_min_ratio_too_low_fails(self):
        """reserve_min_ratio < 0.5 must fail."""
        policy = CampaignPolicy(
            campaign_name="test", initial_bankroll=100, target_bankroll=1000000,
            daily_max_deploy_ratio=0.5, reserve_min_ratio=0.3,
            campaign_analysis_only=True, real_bet_execution=False,
            auto_betting=False, external_betting_api_allowed=False,
            real_money_instruction_allowed=False,
            allow_empty_strategy=True, allow_not_full_deployment=True,
            currency="CNY",
        )
        with pytest.raises(ValueError, match="reserve_min_ratio"):
            validate_campaign_policy(policy)


class TestMaxDeployable:
    """Tests for max deployable bankroll calculation."""

    def test_bankroll_100_max_deployable_50(self):
        """With bankroll=100 and ratio=0.5, max deployable should be 50."""
        policy = load_campaign_policy(_config_path("campaign_policy.json"))
        result = get_max_deployable_bankroll(100.0, policy)
        assert result == 50.0

    def test_bankroll_zero_fails(self):
        """current_bankroll=0 must fail."""
        policy = load_campaign_policy(_config_path("campaign_policy.json"))
        with pytest.raises(ValueError):
            get_max_deployable_bankroll(0.0, policy)

    def test_bankroll_negative_fails(self):
        """current_bankroll negative must fail."""
        policy = load_campaign_policy(_config_path("campaign_policy.json"))
        with pytest.raises(ValueError):
            get_max_deployable_bankroll(-50.0, policy)


class TestRequiredMultiplier:
    """Tests for required multiplier calculation."""

    def test_bankroll_100_multiplier_10000(self):
        """100 -> 1,000,000 requires 10000x."""
        policy = load_campaign_policy(_config_path("campaign_policy.json"))
        result = get_required_multiplier(100.0, policy)
        assert result == 10000.0

    def test_bankroll_1000000_multiplier_1(self):
        """When already at target, multiplier should be 1."""
        policy = load_campaign_policy(_config_path("campaign_policy.json"))
        result = get_required_multiplier(1000000.0, policy)
        assert result == 1.0

    def test_bankroll_zero_fails(self):
        """current_bankroll=0 must fail."""
        policy = load_campaign_policy(_config_path("campaign_policy.json"))
        with pytest.raises(ValueError):
            get_required_multiplier(0.0, policy)
