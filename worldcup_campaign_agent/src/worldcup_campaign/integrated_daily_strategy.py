"""Integrated daily strategy: combines R3 Daily Strategy + R5 EV Ranking + candidate pools."""

import json
from dataclasses import dataclass, asdict, field
from datetime import date, datetime
from pathlib import Path

from worldcup_campaign.daily_strategy import DailyStrategyEngine
from worldcup_campaign.ev_ranking_runner import EVRankingRunner
from worldcup_campaign.daily_candidate_integrator import (
    DailyCandidateIntegrator, IntegratedCandidatePools, BucketPool, AttachedCandidate,
)


@dataclass
class IntegratedDailyStrategy:
    campaign_name: str
    current_date: str
    current_stage: str
    current_bankroll: float
    target_bankroll: float
    bankroll_state: str
    strategy_profile: str
    required_multiplier: float
    required_growth_per_window: float
    target_urgency: str
    daily_strategy_summary: dict
    ev_ranking_summary: dict
    probability_sanity_summary: dict
    integrated_candidate_pools: dict
    scenario_previews: list[dict]
    safety: dict
    warnings: list[str]
    generated_at: str
    analysis_only: bool = True
    not_betting_advice: bool = True
    simulation_only: bool = True


class IntegratedStrategyBuilder:
    def __init__(self, config_paths: dict):
        self.paths = config_paths
        self.r3_engine = DailyStrategyEngine(
            config_paths["policy"],
            config_paths["states"],
            config_paths["stage_map"],
            config_paths["match_registry"],
            config_paths["strategy_rules"],
            config_paths["tagging_rules"],
            config_paths["scenario_rules"],
        )
        self.r5_runner = EVRankingRunner(
            config_paths["ratings"],
            config_paths["prob_config"],
            config_paths["match_registry"],
            config_paths["policy"],
            config_paths["sanity_config"],
            config_paths["odds_policy"],
            config_paths["ev_config"],
        )
        self.integrator = DailyCandidateIntegrator(
            config_paths["score_config"],
            config_paths["bucket_policy"],
            config_paths["integration_config"],
            config_paths["market_registry"],
        )

    def build(self, target_date: str, bankroll: float, windows_left: int = None) -> IntegratedDailyStrategy:
        dt = date.fromisoformat(target_date)
        warnings = []

        # R3: Daily Strategy
        r3 = self.r3_engine.generate(dt, bankroll)
        if windows_left is None:
            windows_left = r3.effective_windows_left

        # R5: EV Ranking
        r5 = self.r5_runner.run(target_date, bankroll, windows_left)

        # Integrate
        buckets = r3.adjusted_bucket_amounts
        pools = self.integrator.integrate(
            r5.candidates, buckets, bankroll, r3.target_bankroll, windows_left,
        )
        warnings.extend(pools.warnings)

        # Format pools for serialization
        pool_dicts = []
        for bp in pools.bucket_pools:
            pool_dicts.append({
                "bucket": bp.bucket,
                "bucket_strategy_budget": bp.bucket_strategy_budget,
                "role": bp.role,
                "candidate_count": bp.candidate_count,
                "empty_reason": bp.empty_reason,
                "candidates": [asdict(c) for c in bp.candidates],
            })

        # Safety
        safety = {
            "campaign_analysis_only": True,
            "real_bet_execution": False,
            "auto_betting": False,
            "external_betting_api_allowed": False,
            "real_money_instruction_allowed": False,
            "simulation_only": True,
            "not_betting_advice": True,
        }

        return IntegratedDailyStrategy(
            campaign_name="worldcup_2026_high_odds_campaign",
            current_date=target_date,
            current_stage=r3.current_stage,
            current_bankroll=bankroll,
            target_bankroll=r3.target_bankroll,
            bankroll_state=r3.state,
            strategy_profile=r3.strategy_profile,
            required_multiplier=r3.target_bankroll / bankroll,
            required_growth_per_window=(r3.target_bankroll / bankroll) ** (1.0 / windows_left) if windows_left > 0 else 1,
            target_urgency=r5.sanity_summary.get("total_checked", 0),
            daily_strategy_summary={
                "state": r3.state,
                "profile": r3.strategy_profile,
                "max_deployable": r3.max_deployable,
                "deployed_total": r3.deployed_total,
                "matches_today": r3.today_matches_count,
                "windows_left": windows_left,
                "bucket_amounts": r3.bucket_amounts,
            },
            ev_ranking_summary={
                "candidate_count": r5.candidate_count,
                "value_candidate_count": r5.value_candidate_count,
                "odds_source_mode": r5.odds_source_mode,
                "uses_real_bookmaker_odds": r5.uses_real_bookmaker_odds,
            },
            probability_sanity_summary=r5.sanity_summary,
            integrated_candidate_pools={
                "pools": pool_dicts,
                "unassigned": [asdict(c) for c in pools.unassigned_candidates],
                "watch_only": [asdict(c) for c in pools.watch_only_candidates],
                "summary": pools.summary,
            },
            scenario_previews=[],
            safety=safety,
            warnings=warnings,
            generated_at=datetime.now().isoformat(),
        )