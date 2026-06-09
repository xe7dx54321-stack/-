"""Parlay optimizer: ranks parlays and assigns to edge/attack buckets."""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class ParlayBucketPools:
    edge_parlays: list[dict] = field(default_factory=list)
    attack_parlays: list[dict] = field(default_factory=list)
    watch_only_parlays: list[dict] = field(default_factory=list)
    blocked_count: int = 0
    warnings: list[str] = field(default_factory=list)


class ParlayOptimizer:
    def __init__(self, optimizer_config_path: str, bucket_policy_path: str):
        self.config = json.loads(Path(optimizer_config_path).read_text(encoding="utf-8-sig"))
        self.bucket_policy = json.loads(Path(bucket_policy_path).read_text(encoding="utf-8-sig"))

    def rank(self, candidates: list) -> list:
        valid = [c for c in candidates if c is not None]
        valid.sort(key=lambda c: c.parlay_campaign_score, reverse=True)
        return valid[:self.config["ranking"]["max_ranked_parlays"]]

    def assign_to_buckets(self, ranked: list) -> ParlayBucketPools:
        pools = ParlayBucketPools()
        edge_policy = self.bucket_policy.get("edge", {})
        attack_policy = self.bucket_policy.get("attack", {})

        for c in ranked:
            cd = asdict(c) if hasattr(c, '__dict__') else c
            band = cd.get("combined_odds_band", "")
            leg_count = cd.get("leg_count", 0)
            tier = cd.get("parlay_tier", "")

            # Edge: 2-leg, medium band
            if leg_count == 2 and band in ("medium", "high") and len(pools.edge_parlays) < edge_policy.get("max_candidates", 5):
                pools.edge_parlays.append(cd)
            # Attack: 2/3/4-leg, high+ band
            elif band in ("high", "very_high", "lottery") and len(pools.attack_parlays) < attack_policy.get("max_candidates", 10):
                pools.attack_parlays.append(cd)
            else:
                pools.watch_only_parlays.append(cd)

        return pools