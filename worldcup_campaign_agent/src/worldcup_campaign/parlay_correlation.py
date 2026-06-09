"""Parlay correlation: detect and penalize dependent legs."""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CorrelationResult:
    is_blocked: bool
    penalty_score: float
    warnings: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    dependency_flags: list[str] = field(default_factory=list)


class ParlayCorrelationAnalyzer:
    def __init__(self, policy_path: str):
        self.policy = json.loads(Path(policy_path).read_text(encoding="utf-8-sig"))

    def analyze(self, legs: list[dict]) -> CorrelationResult:
        penalties = 0.0
        warnings = []
        reasons = []
        flags = []
        dp = self.policy.get("dependency_penalties", {})

        # Extract leg info
        matches = [l.get("match_id", "") for l in legs]
        groups = [l.get("group", "") for l in legs if l.get("group")]
        markets = [l.get("market_type", "") for l in legs]
        stages = [l.get("stage", "") for l in legs]

        # Same match check (block)
        match_counts = {}
        for m in matches:
            match_counts[m] = match_counts.get(m, 0) + 1
        for m, cnt in match_counts.items():
            if cnt > 1:
                flags.append(f"same_match:{m}")
                reasons.append(f"Blocked: {cnt} legs from same match {m}")
                penalties += dp.get("same_match", 1.0)
                return CorrelationResult(
                    is_blocked=True, penalty_score=penalties,
                    warnings=warnings, reason_codes=reasons, dependency_flags=flags,
                )

        # Same group check
        group_counts = {}
        for g in groups:
            if g:
                group_counts[g] = group_counts.get(g, 0) + 1
        max_group = self.policy.get("max_legs_from_same_group", 2)
        for g, cnt in group_counts.items():
            if cnt > max_group:
                flags.append(f"same_group:{g}")
                warnings.append(f"Warning: {cnt} legs from same group {g} (max {max_group})")
                penalties += dp.get("same_group", 0.15)
                reasons.append(f"same_group_over_limit:{g}")

        # Same market type
        market_counts = {}
        for mt in markets:
            market_counts[mt] = market_counts.get(mt, 0) + 1
        for mt, cnt in market_counts.items():
            if cnt > 1:
                flags.append(f"same_market:{mt}")
                warnings.append(f"Warning: {cnt} legs with same market type {mt}")
                penalties += dp.get("same_market_type", 0.05)
                reasons.append(f"same_market_type:{mt}")

        # Same stage same day
        stage_day = {}
        for l in legs:
            key = f"{l.get('stage', '')}_{l.get('date', '')}"
            stage_day[key] = stage_day.get(key, 0) + 1
        for k, cnt in stage_day.items():
            if cnt > 1:
                flags.append(f"same_stage_day:{k}")
                penalties += dp.get("same_stage_same_day", 0.03)
                reasons.append(f"same_stage_same_day:{k}")

        penalty_score = min(1.0, penalties)
        return CorrelationResult(
            is_blocked=False, penalty_score=round(penalty_score, 4),
            warnings=warnings, reason_codes=reasons, dependency_flags=flags,
        )