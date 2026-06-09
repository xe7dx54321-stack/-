"""Campaign score: multi-factor candidate scoring for campaign strategy."""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CampaignScoreConfig:
    weights: dict
    penalties: dict
    tiers: dict
    analysis_only: bool
    not_betting_advice: bool


@dataclass
class CampaignScoreResult:
    candidate_id: str
    campaign_score: float
    score_components: dict
    penalties_applied: list[str]
    candidate_tier: str
    reason_codes: list[str]
    not_betting_advice: bool = True


def load_campaign_score_config(path: str) -> CampaignScoreConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return CampaignScoreConfig(
        weights=raw["score_components"],
        penalties=raw["penalties"],
        tiers=raw["candidate_tiers"],
        analysis_only=raw["analysis_only"],
        not_betting_advice=raw["not_betting_advice"],
    )


def calculate_campaign_score(
    candidate: dict,
    current_bankroll: float,
    target_bankroll: float,
    windows_left: int,
    config: CampaignScoreConfig,
    was_repaired: bool = False,
    data_quality: str = "seed",
) -> CampaignScoreResult:
    """Calculate campaign score for a candidate."""
    penalties = []
    reasons = []
    w = config.weights

    # Extract candidate fields
    ev = candidate.get("ev", 0)
    edge = candidate.get("edge", 0)
    odds = candidate.get("mock_odds", 2.0)
    model_prob = candidate.get("model_probability", 0.5)
    confidence = candidate.get("confidence", 0.3) if "confidence" in candidate else 0.3
    value_flag = candidate.get("value_flag", "no_value")
    
    # Target contribution
    gap = target_bankroll / current_bankroll if current_bankroll > 0 else 10000
    tc = (odds - 1.0) / gap if gap > 0 else 0
    tc = min(1.0, max(0.0, tc))

    # EV score: normalize to 0-1 range (map -0.1 to 0, 0.2 to 1)
    ev_score = max(0.0, min(1.0, (ev + 0.1) / 0.3))
    ev_score *= w["ev_weight"]
    if ev < 0:
        penalties.append("negative_ev_penalty")
        ev_score = max(0.0, ev_score - config.penalties["negative_ev_penalty"])

    # Edge score
    edge_score = max(0.0, min(1.0, (edge + 0.05) / 0.2)) * w["edge_weight"]

    # Target contribution score
    tc_score = tc * w["target_contribution_weight"]

    # Odds band fit score
    odds_score = 0.5 * w["odds_band_fit_weight"]
    if odds >= 5.0:
        odds_score = 0.8 * w["odds_band_fit_weight"]
    elif odds >= 2.0:
        odds_score = 0.6 * w["odds_band_fit_weight"]

    # Model probability score
    prob_score = model_prob * w["model_probability_weight"]

    # Confidence score
    conf_score = confidence * w["confidence_weight"]
    if confidence < 0.2:
        penalties.append("very_low_confidence_penalty")
        conf_score = max(0, conf_score - config.penalties["very_low_confidence_penalty"])

    # Data quality score
    dq_map = {"high": 1.0, "medium_high": 0.8, "medium": 0.6, "low": 0.3, "seed": 0.5}
    dq_score = dq_map.get(data_quality, 0.5) * w["data_quality_weight"]

    if was_repaired:
        penalties.append("probability_repaired_penalty")
        dq_score = max(0, dq_score - config.penalties["probability_repaired_penalty"])

    # Compose
    components = {
        "ev_score": round(ev_score, 4),
        "edge_score": round(edge_score, 4),
        "target_contribution_score": round(tc_score, 4),
        "odds_band_fit_score": round(odds_score, 4),
        "model_probability_score": round(prob_score, 4),
        "confidence_score": round(conf_score, 4),
        "data_quality_score": round(dq_score, 4),
    }

    total = sum(components.values())
    total = max(0.0, min(1.0, total))

    # Classify tier
    tier = classify_candidate_tier(candidate, total, value_flag, odds, config)
    reasons.append(f"tier={tier}")
    reasons.append(f"score={total:.3f}")

    cid = candidate.get("match_id", "unknown") + "_" + candidate.get("market_type", "?")
    return CampaignScoreResult(
        candidate_id=cid,
        campaign_score=round(total, 4),
        score_components=components,
        penalties_applied=penalties,
        candidate_tier=tier,
        reason_codes=reasons,
        not_betting_advice=True,
    )


def classify_candidate_tier(
    candidate: dict, score: float, value_flag: str, odds: float, config: CampaignScoreConfig
) -> str:
    tiers = config.tiers
    # value_candidate requires value_flag=true
    if score >= tiers["value_candidate"]["min_campaign_score"] and value_flag in ("value", "strong_value"):
        return "value_candidate"
    if score >= tiers["campaign_candidate"]["min_campaign_score"]:
        return "campaign_candidate"
    if score >= tiers["attack_candidate"]["min_campaign_score"]:
        return "attack_candidate"
    if score >= tiers["lottery_candidate"]["min_campaign_score"] and odds >= 10.0:
        return "lottery_candidate"
    return "watch_only"