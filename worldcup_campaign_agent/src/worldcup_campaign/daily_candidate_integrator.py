"""Daily candidate integrator: connects EV candidates to bucket plan."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from worldcup_campaign.campaign_score import (
    calculate_campaign_score, CampaignScoreConfig, load_campaign_score_config,
)
from worldcup_campaign.bucket_candidate_policy import BucketCandidatePolicy


@dataclass
class AttachedCandidate:
    candidate_id: str
    match_id: str
    match_number: int
    market_type: str
    selection: str
    mock_odds: float
    model_probability: float
    market_probability: float
    edge: float
    ev: float
    odds_band: str
    value_flag: str
    campaign_score: float
    candidate_tier: str
    target_contribution_preview: float
    bucket_fit_reasons: list[str]
    analysis_only: bool = True
    not_betting_advice: bool = True
    simulation_only: bool = True


@dataclass
class BucketPool:
    bucket: str
    bucket_strategy_budget: float
    role: str
    candidate_count: int
    candidates: list[AttachedCandidate]
    warnings: list[str] = field(default_factory=list)
    empty_reason: str = ""


@dataclass
class IntegratedCandidatePools:
    bucket_pools: list[BucketPool]
    unassigned_candidates: list[AttachedCandidate] = field(default_factory=list)
    watch_only_candidates: list[AttachedCandidate] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class DailyCandidateIntegrator:
    def __init__(
        self,
        score_config_path: str,
        bucket_policy_path: str,
        integration_config_path: str,
        market_registry_path: str,
    ):
        self.score_config = load_campaign_score_config(score_config_path)
        self.bucket_policy = BucketCandidatePolicy(bucket_policy_path, market_registry_path)
        self.integration_config = json.loads(
            Path(integration_config_path).read_text(encoding="utf-8-sig")
        )

    def integrate(
        self,
        ev_candidates: list[dict],
        bucket_amounts: dict,
        current_bankroll: float,
        target_bankroll: float,
        windows_left: int,
    ) -> IntegratedCandidatePools:
        warnings = []

        # Step 1: Score all candidates
        scored = []
        for c in ev_candidates:
            score_result = calculate_campaign_score(
                c, current_bankroll, target_bankroll, windows_left, self.score_config,
            )
            scored.append((c, score_result))

        # Step 2: Assign to buckets
        playable = ["core", "edge", "attack", "futures"]
        pools = {}
        for b in playable:
            pools[b] = []

        unassigned = []
        watch_only_list = []

        for c, sr in scored:
            ac = AttachedCandidate(
                candidate_id=sr.candidate_id,
                match_id=c.get("match_id", ""),
                match_number=c.get("match_number", 0),
                market_type=c.get("market_type", ""),
                selection=c.get("selection", ""),
                mock_odds=c.get("mock_odds", 2.0),
                model_probability=c.get("model_probability", 0.5),
                market_probability=c.get("market_probability", 0.5),
                edge=c.get("edge", 0),
                ev=c.get("ev", 0),
                odds_band=self.bucket_policy._odds_band(c.get("mock_odds", 2.0)),
                value_flag=c.get("value_flag", "no_value"),
                campaign_score=sr.campaign_score,
                candidate_tier=sr.candidate_tier,
                target_contribution_preview=c.get("target_contribution_preview", 0),
                bucket_fit_reasons=[],
            )

            if sr.candidate_tier == "watch_only":
                watch_only_list.append(ac)
                continue

            # Try to assign to a bucket
            assigned = False
            for b in playable:
                eligibility = self.bucket_policy.is_allowed(c, b)
                max_c = self.bucket_policy.get_max_candidates(b)
                if eligibility.allowed and len(pools[b]) < max_c:
                    ac.bucket_fit_reasons = eligibility.reason_codes
                    pools[b].append(ac)
                    assigned = True
                    break

            if not assigned:
                unassigned.append(ac)

        # Build bucket pools
        bucket_pools = []
        for b in playable:
            b_amount = bucket_amounts.get(b, 0)
            role = self.bucket_policy.get_role(b)
            max_c = self.bucket_policy.get_max_candidates(b)
            empty_reason = ""
            if len(pools[b]) == 0:
                empty_reason = f"No eligible candidates for {b} bucket (synthetic odds, vig applied)"
                warnings.append(empty_reason)
            elif len(pools[b]) < max_c:
                warnings.append(f"{b}: {len(pools[b])}/{max_c} candidates")
            bucket_pools.append(BucketPool(
                bucket=b,
                bucket_strategy_budget=b_amount,
                role=role,
                candidate_count=len(pools[b]),
                candidates=pools[b],
                empty_reason=empty_reason,
            ))

        # Summary
        total_attached = sum(p.candidate_count for p in bucket_pools)
        summary = {
            "total_ev_candidates": len(ev_candidates),
            "attached_to_buckets": total_attached,
            "unassigned": len(unassigned),
            "watch_only": len(watch_only_list),
            "allow_zero_value": self.integration_config.get("allow_zero_value_candidate_day", True),
        }

        return IntegratedCandidatePools(
            bucket_pools=bucket_pools,
            unassigned_candidates=unassigned,
            watch_only_candidates=watch_only_list,
            summary=summary,
            warnings=warnings,
        )