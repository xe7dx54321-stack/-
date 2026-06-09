"""Futures candidate builder: EV, campaign score, tier classification for futures."""
import json, sys, uuid
from dataclasses import dataclass, field
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from worldcup_campaign.odds_math import calculate_ev, decimal_odds_to_implied_probability


@dataclass
class FuturesCandidate:
    candidate_id: str
    team_code: str
    team_name: str
    market_type: str
    selection_id: str
    selection_label: str
    path_probability: float
    synthetic_odds: float
    ev: float
    edge: float
    odds_band: str
    target_contribution: float
    campaign_score: float
    candidate_tier: str
    eligible_bucket: str
    source: str = "synthetic_from_path_probability"
    data_quality: str = "seed_rating_simulation"
    settlement_stage: str = ""
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True
    warnings: list = field(default_factory=list)


class FuturesCandidateBuilder:
    def __init__(self, candidate_policy_path: str, score_config_path: str,
                 odds_policy_path: str, market_config_path: str):
        self.policy = json.loads(Path(candidate_policy_path).read_text(encoding="utf-8-sig"))
        self.score_config = json.loads(Path(score_config_path).read_text(encoding="utf-8-sig"))
        self.odds_policy = json.loads(Path(odds_policy_path).read_text(encoding="utf-8-sig"))
        self.market_config = json.loads(Path(market_config_path).read_text(encoding="utf-8-sig"))

    def build_candidates(self, futures_odds: list, current_bankroll: float,
                         target_bankroll: float) -> list[FuturesCandidate]:
        candidates = []
        for fo in futures_odds:
            ev = calculate_ev(fo.path_probability, fo.synthetic_odds)
            implied = decimal_odds_to_implied_probability(fo.synthetic_odds)
            edge = fo.path_probability - implied

            gap = target_bankroll / current_bankroll if current_bankroll > 0 else 10000
            tc = (fo.synthetic_odds - 1.0) / gap
            tc = min(1.0, max(0.0, tc))

            campaign_score = self._calculate_score(fo, ev, edge, tc)
            tier = self._classify_tier(campaign_score, fo)
            bucket = self._get_eligible_bucket(fo, campaign_score)

            candidates.append(FuturesCandidate(
                candidate_id=f"FUT_{uuid.uuid4().hex[:8]}",
                team_code=fo.team_code,
                team_name=fo.team_name,
                market_type=fo.market_type,
                selection_id=fo.selection_id,
                selection_label=fo.selection_label,
                path_probability=fo.path_probability,
                synthetic_odds=fo.synthetic_odds,
                ev=round(ev, 4),
                edge=round(edge, 4),
                odds_band=fo.odds_band,
                target_contribution=round(tc, 6),
                campaign_score=round(campaign_score, 4),
                candidate_tier=tier,
                eligible_bucket=bucket,
            ))

        candidates.sort(key=lambda c: c.campaign_score, reverse=True)
        return candidates

    def _calculate_score(self, fo, ev, edge, tc):
        # Simple weighted score for futures
        ev_score = max(0, min(1, (ev + 0.2) / 0.5)) * 0.25
        tc_score = tc * 0.35
        prob_score = min(1, fo.path_probability * 20) * 0.15
        band_bonus = 0.3 if fo.odds_band in ("high", "very_high") else 0.15
        band_score = band_bonus * 0.15
        edge_score = max(0, min(1, (edge + 0.1) / 0.3)) * 0.10
        return min(1.0, max(0.0, ev_score + tc_score + prob_score + band_score + edge_score))

    def _classify_tier(self, score: float, fo) -> str:
        if score >= 0.6:
            return "value_candidate"
        elif score >= 0.35:
            return "campaign_candidate"
        elif score >= 0.15:
            return "attack_candidate" if fo.odds_band in ("high", "very_high", "lottery") else "campaign_candidate"
        elif fo.odds_band in ("very_high", "lottery"):
            return "lottery_candidate"
        return "watch_only"

    def _get_eligible_bucket(self, fo, score) -> str:
        buckets = self.policy.get("buckets", {})
        futures_bucket = buckets.get("futures", {})
        attack_bucket = buckets.get("attack", {})

        # Check futures bucket
        allowed_mt = futures_bucket.get("allowed_market_types", [])
        allowed_bands = futures_bucket.get("allowed_odds_bands", [])
        if fo.market_type in allowed_mt and fo.odds_band in allowed_bands:
            return "futures"

        # Check attack bucket for longshots
        attack_mt = attack_bucket.get("allowed_market_types", [])
        attack_bands = attack_bucket.get("allowed_odds_bands", [])
        if fo.market_type in attack_mt and fo.odds_band in attack_bands:
            return "attack"

        return "watch_only"


class FuturesIntegrator:
    def __init__(self, candidate_policy_path: str):
        self.policy = json.loads(Path(candidate_policy_path).read_text(encoding="utf-8-sig"))

    def assign_to_buckets(self, candidates: list[FuturesCandidate]) -> dict:
        buckets = self.policy.get("buckets", {})
        futures_cfg = buckets.get("futures", {})
        attack_cfg = buckets.get("attack", {})

        futures_pool = []
        attack_pool = []
        watch_only = []

        for c in candidates:
            if c.eligible_bucket == "futures" and len(futures_pool) < futures_cfg.get("max_candidates", 5):
                futures_pool.append(c)
            elif c.eligible_bucket == "attack" and len(attack_pool) < attack_cfg.get("max_candidates", 5):
                attack_pool.append(c)
            else:
                watch_only.append(c)

        return {
            "futures": futures_pool,
            "attack_longshot": attack_pool,
            "watch_only": watch_only,
            "total": len(candidates),
            "futures_count": len(futures_pool),
            "attack_count": len(attack_pool),
            "watch_only_count": len(watch_only),
        }
