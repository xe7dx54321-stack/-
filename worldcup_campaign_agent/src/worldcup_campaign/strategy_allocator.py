"""Strategy allocator: distribute bucket amounts across eligible matches."""

from dataclasses import dataclass, field

from worldcup_campaign.strategy_profile import StrategyProfile
from worldcup_campaign.match_strategy_labeler import MatchLabel


@dataclass
class BucketAllocation:
    bucket: str
    amount: float
    eligible_match_count: int
    profile_weight: float
    is_active: bool
    notes: str


@dataclass
class AllocationPlan:
    buckets: list[BucketAllocation] = field(default_factory=list)
    total_deployed: float = 0.0
    total_reserve: float = 0.0
    matches_eligible: int = 0
    can_deploy: bool = True
    reason: str = ""


class StrategyAllocator:
    """Allocates bucket amounts across eligible matches for the day."""

    def allocate(
        self,
        bucket_amounts: dict[str, float],
        profile: StrategyProfile,
        labeled_matches: list[MatchLabel],
    ) -> AllocationPlan:
        """Create an allocation plan based on bucket amounts and strategy profile."""
        
        # Only consider today's matches
        today_matches = [m for m in labeled_matches if m.is_today]
        
        # Calculate how many matches are eligible for each bucket
        bucket_eligibility = {}
        for bucket in ["core", "edge", "attack", "futures"]:
            eligible = sum(
                1 for m in today_matches if bucket in m.eligible_buckets
            )
            bucket_eligibility[bucket] = eligible

        # Build bucket allocations
        buckets = []
        weight_map = {
            "core": profile.core_allocation_weight,
            "edge": profile.edge_allocation_weight,
            "attack": profile.attack_allocation_weight,
            "futures": profile.futures_allocation_weight,
        }
        allow_map = {
            "core": profile.allow_core,
            "edge": profile.allow_edge,
            "attack": profile.allow_attack,
            "futures": profile.allow_futures,
        }

        total_eligible = sum(bucket_eligibility.values())

        for bucket in ["core", "edge", "attack", "futures"]:
            amount = bucket_amounts.get(bucket, 0)
            eligible_count = bucket_eligibility.get(bucket, 0)
            is_allowed = allow_map.get(bucket, False)
            
            if not is_allowed:
                buckets.append(BucketAllocation(
                    bucket=bucket,
                    amount=0.0,
                    eligible_match_count=eligible_count,
                    profile_weight=weight_map[bucket],
                    is_active=False,
                    notes=f"Disabled by profile '{profile.name}'"
                ))
            elif eligible_count == 0:
                buckets.append(BucketAllocation(
                    bucket=bucket,
                    amount=0.0,
                    eligible_match_count=0,
                    profile_weight=weight_map[bucket],
                    is_active=False,
                    notes="No eligible matches today"
                ))
            else:
                buckets.append(BucketAllocation(
                    bucket=bucket,
                    amount=amount,
                    eligible_match_count=eligible_count,
                    profile_weight=weight_map[bucket],
                    is_active=True,
                    notes=f"Deployable across {eligible_count} match(es)"
                ))

        total_deployed = sum(b.amount for b in buckets if b.is_active)
        reserve = bucket_amounts.get("reserve", 0)

        return AllocationPlan(
            buckets=buckets,
            total_deployed=total_deployed,
            total_reserve=reserve,
            matches_eligible=total_eligible,
            can_deploy=total_deployed > 0,
            reason=f"Profile: {profile.name}, {len(today_matches)} matches today",
        )