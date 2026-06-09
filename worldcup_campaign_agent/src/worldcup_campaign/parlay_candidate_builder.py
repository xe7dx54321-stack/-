"""Parlay candidate builder: extract legs from integrated strategy, generate combinations."""

import itertools, json, uuid
from dataclasses import dataclass, field
from pathlib import Path

from worldcup_campaign.parlay_math import (
    calculate_combined_odds, calculate_combined_probability,
    calculate_combined_ev, classify_odds_band, calculate_leg_quality_summary,
)
from worldcup_campaign.parlay_correlation import ParlayCorrelationAnalyzer


@dataclass
class ParlayLeg:
    source_candidate_id: str
    match_id: str
    match_number: int
    date: str = ""
    stage: str = ""
    group: str = ""
    market_type: str = ""
    selection: str = ""
    decimal_odds: float = 2.0
    model_probability: float = 0.5
    ev: float = 0.0
    edge: float = 0.0
    odds_band: str = "medium"
    candidate_tier: str = ""
    source_bucket: str = ""
    leg_role: str = "balanced"
    confidence: float = 0.3
    data_quality: str = "seed"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "source_candidate_id": self.source_candidate_id,
            "match_id": self.match_id, "match_number": self.match_number,
            "date": self.date, "stage": self.stage, "group": self.group,
            "market_type": self.market_type, "selection": self.selection,
            "decimal_odds": self.decimal_odds, "model_probability": self.model_probability,
            "ev": self.ev, "edge": self.edge, "odds_band": self.odds_band,
            "candidate_tier": self.candidate_tier, "source_bucket": self.source_bucket,
            "leg_role": self.leg_role, "confidence": self.confidence,
            "data_quality": self.data_quality,
        }


@dataclass
class ParlayCandidate:
    parlay_id: str
    leg_count: int
    parlay_type: str
    legs: list[dict]
    combined_odds: float
    combined_model_probability: float
    combined_ev: float
    combined_odds_band: str
    target_contribution_preview: float
    correlation_result: dict
    parlay_campaign_score: float
    parlay_tier: str
    eligible_bucket: str
    warnings: list[str] = field(default_factory=list)
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


class ParlayCandidateBuilder:
    def __init__(self, optimizer_config_path: str, correlation_policy_path: str):
        self.config = json.loads(Path(optimizer_config_path).read_text(encoding="utf-8-sig"))
        self.correlation = ParlayCorrelationAnalyzer(correlation_policy_path)
        self.max_raw = self.config["ranking"]["max_raw_combinations"]
        self.leg_counts = self.config["allowed_leg_counts"]

    def extract_legs(self, integrated_strategy) -> list[ParlayLeg]:
        pools = integrated_strategy.integrated_candidate_pools.get("pools", [])
        legs = []
        for pool in pools:
            bucket = pool.get("bucket", "")
            if bucket not in ["core", "edge", "attack"]:
                continue
            for c in pool.get("candidates", []):
                role = self._classify_role(c)
                legs.append(ParlayLeg(
                    source_candidate_id=c.get("candidate_id", ""),
                    match_id=c.get("match_id", ""),
                    match_number=c.get("match_number", 0),
                    stage=c.get("stage", c.get("stage", "")),
                    market_type=c.get("market_type", ""),
                    selection=c.get("selection", ""),
                    decimal_odds=c.get("mock_odds", 2.0),
                    model_probability=c.get("model_probability", 0.5),
                    ev=c.get("ev", 0), edge=c.get("edge", 0),
                    candidate_tier=c.get("candidate_tier", ""),
                    source_bucket=bucket, leg_role=role,
                ))
        return legs

    def _classify_role(self, c: dict) -> str:
        odds = c.get("mock_odds", 2.0)
        prob = c.get("model_probability", 0.5)
        bucket = c.get("source_bucket", "")
        if bucket == "core" or (prob >= 0.35 and odds < 3.0):
            return "base"
        if odds >= 10.0 or prob < 0.05:
            return "attack"
        if odds >= 3.0:
            return "edge"
        return "balanced"

    def generate_combinations(self, legs: list[ParlayLeg]) -> list[list[ParlayLeg]]:
        all_combos = []
        for n in self.leg_counts:
            if n > len(legs):
                continue
            combos = list(itertools.combinations(legs, n))
            all_combos.extend(combos)
            if len(all_combos) >= self.max_raw:
                break
        return all_combos[:self.max_raw]

    def build_candidate(
        self, leg_combo: tuple, current_bankroll: float, target_bankroll: float
    ) -> ParlayCandidate:
        leg_dicts = [l.to_dict() for l in leg_combo]
        leg_list = list(leg_combo)

        combined_odds = calculate_combined_odds(leg_dicts)
        combined_prob = calculate_combined_probability(leg_dicts)
        combined_ev = calculate_combined_ev(combined_prob, combined_odds)
        band = classify_odds_band(combined_odds, self.config.get("odds_bands"))

        # Correlation
        corr = self.correlation.analyze(leg_dicts)
        if corr.is_blocked:
            return None

        # Target contribution
        gap = target_bankroll / current_bankroll if current_bankroll > 0 else 10000
        tc = (combined_odds - 1.0) / gap
        tc = min(1.0, max(0.0, tc))

        # Campaign score
        w = self.config.get("score_weights", {})
        ev_score = max(0, min(1, (combined_ev + 0.1) / 0.5)) * w.get("combined_ev", 0.2)
        tc_score = tc * w.get("target_contribution", 0.3)
        prob_score = combined_prob * 10 * w.get("combined_probability", 0.15)
        band_fit = (0.5 if band in ("medium","high") else 0.3) * w.get("odds_band_fit", 0.15)
        qual = calculate_leg_quality_summary(leg_dicts)
        qual_score = min(1, qual["avg_prob"] * 2) * w.get("leg_quality", 0.1)
        corr_score = (1 - corr.penalty_score) * w.get("correlation", 0.1)
        campaign_score = min(1.0, max(0.0, ev_score + tc_score + prob_score + band_fit + qual_score + corr_score))

        # Tier
        if campaign_score >= 0.5:
            tier = "value_candidate"
        elif campaign_score >= 0.3:
            tier = "campaign_candidate"
        elif campaign_score >= 0.15:
            tier = "attack_candidate"
        else:
            tier = "lottery_candidate"

        # Eligible bucket
        eligible = "attack" if band in ("high","very_high","lottery") else "edge"

        all_warnings = corr.warnings.copy()
        if combined_ev < 0:
            all_warnings.append(f"Negative combined EV: {combined_ev:.4f}")

        pid = f"PARLAY_{uuid.uuid4().hex[:8]}"
        return ParlayCandidate(
            parlay_id=pid, leg_count=len(leg_list),
            parlay_type=self._determine_type(leg_list),
            legs=leg_dicts, combined_odds=combined_odds,
            combined_model_probability=combined_prob, combined_ev=round(combined_ev, 4),
            combined_odds_band=band,
            target_contribution_preview=round(tc, 4),
            correlation_result={"is_blocked":False,"penalty_score":corr.penalty_score,
                "warnings":corr.warnings,"reason_codes":corr.reason_codes},
            parlay_campaign_score=round(campaign_score, 4), parlay_tier=tier,
            eligible_bucket=eligible, warnings=all_warnings,
        )

    def _determine_type(self, legs: list) -> str:
        roles = set(l.leg_role for l in legs)
        if len(legs) == 2 and "base" in roles:
            return "base_plus_edge"
        if "attack" in roles:
            return "high_odds_attack" if len(legs) >= 3 else "balanced_attack"
        return "balanced_attack"