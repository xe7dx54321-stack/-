"""Bucket candidate policy: rules for which candidates go in which buckets."""

import json
from dataclasses import dataclass, field
from pathlib import Path


VALID_BUCKETS = ["reserve", "core", "edge", "attack", "futures"]


@dataclass
class BucketEligibilityResult:
    bucket: str
    allowed: bool
    reason_codes: list[str]
    blocked_reasons: list[str] = field(default_factory=list)


class BucketCandidatePolicy:
    def __init__(self, policy_path: str, market_registry_path: str):
        self.policy = json.loads(Path(policy_path).read_text(encoding="utf-8-sig"))
        self.markets = json.loads(Path(market_registry_path).read_text(encoding="utf-8-sig"))
        self.market_types = {m["market_type"] for m in self.markets}

    def is_allowed(self, candidate: dict, bucket: str) -> BucketEligibilityResult:
        if bucket == "reserve":
            return BucketEligibilityResult("reserve", False, ["reserve_no_candidates"], ["Reserve never receives candidates"])
        if bucket not in VALID_BUCKETS:
            raise ValueError(f"Unknown bucket: {bucket}")
        bp = self.policy["buckets"].get(bucket)
        if not bp:
            raise ValueError(f"No policy for bucket: {bucket}")
        reasons = []
        blocked = []

        market_type = candidate.get("market_type", "")
        if market_type not in self.market_types:
            return BucketEligibilityResult(bucket, False, [], [f"Unknown market_type: {market_type}"])

        # Check market type allowed
        if market_type in bp["blocked_market_types"]:
            blocked.append(f"Market type {market_type} blocked in {bucket}")
        elif market_type not in bp["allowed_market_types"]:
            blocked.append(f"Market type {market_type} not allowed in {bucket}")

        # Check odds band
        odds = candidate.get("mock_odds", 2.0)
        band = self._odds_band(odds)
        if band not in bp["allowed_odds_bands"]:
            blocked.append(f"Odds band {band} not allowed in {bucket}")
        else:
            reasons.append(f"odds_band={band}")

        # Check model probability
        prob = candidate.get("model_probability", 0)
        if prob < bp["min_model_probability"]:
            blocked.append(f"Probability {prob:.4f} < min {bp['min_model_probability']}")

        # Check negative EV
        ev = candidate.get("ev", 0)
        if ev < 0 and not bp["allow_negative_ev"]:
            blocked.append(f"Negative EV ({ev:.4f}) not allowed in {bucket}")

        # Also check eligible_buckets from candidate
        eligible = candidate.get("bucket_eligibility", [])
        if eligible and bucket not in eligible and bucket not in ["reserve"]:
            blocked.append(f"Bucket {bucket} not in candidate eligible_buckets")

        allowed = len(blocked) == 0
        return BucketEligibilityResult(bucket, allowed, reasons, blocked)

    def get_allowed_buckets(self, candidate: dict) -> list[str]:
        result = []
        for b in ["core", "edge", "attack", "futures"]:
            r = self.is_allowed(candidate, b)
            if r.allowed:
                result.append(b)
        return result

    def get_max_candidates(self, bucket: str) -> int:
        if bucket == "reserve":
            return 0
        bp = self.policy["buckets"].get(bucket, {})
        return bp.get("max_candidates", 0)

    def get_role(self, bucket: str) -> str:
        if bucket == "reserve":
            return self.policy.get("reserve", {}).get("role", "")
        bp = self.policy["buckets"].get(bucket, {})
        return bp.get("role", "")

    @staticmethod
    def _odds_band(odds: float) -> str:
        if odds < 1.5: return "low"
        if odds < 3.0: return "medium"
        if odds < 10.0: return "high"
        if odds < 30.0: return "very_high"
        return "lottery"