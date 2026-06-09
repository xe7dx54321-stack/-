"""Parlay math: combined odds, probability, EV for multi-leg parlays."""

from worldcup_campaign.odds_math import calculate_ev


def calculate_combined_odds(legs: list[dict]) -> float:
    """Combined decimal odds = product of individual odds."""
    result = 1.0
    for leg in legs:
        odds = leg.get("decimal_odds", leg.get("mock_odds", leg.get("odds", 2.0)))
        if odds <= 1.0:
            raise ValueError(f"Leg odds must be > 1.0, got {odds}")
        result *= odds
    return round(result, 2)


def calculate_combined_probability(legs: list[dict]) -> float:
    """Combined model probability = product of individual model probabilities."""
    result = 1.0
    for leg in legs:
        prob = leg.get("model_probability", 0.5)
        if not 0.0 <= prob <= 1.0:
            raise ValueError(f"Leg probability must be 0-1, got {prob}")
        result *= prob
    return round(result, 6)


def calculate_combined_ev(combined_prob: float, combined_odds: float) -> float:
    """Combined EV using standard EV formula."""
    return calculate_ev(combined_prob, combined_odds)


def classify_odds_band(combined_odds: float, config: dict = None) -> str:
    bands = {
        "low": (1.01, 3.0),
        "medium": (3.0, 10.0),
        "high": (10.0, 50.0),
        "very_high": (50.0, 500.0),
        "lottery": (500.0, 10000.0),
    }
    if config and "odds_bands" in config:
        bands = {k: (v["min"], v["max"]) for k, v in config["odds_bands"].items()}
    for name, (lo, hi) in bands.items():
        if lo <= combined_odds < hi:
            return name
    return "lottery"


def calculate_leg_quality_summary(legs: list[dict]) -> dict:
    """Summarize quality of parlay legs."""
    if not legs:
        return {"avg_prob": 0, "avg_odds": 0, "min_prob": 0, "max_odds": 0, "count": 0}
    probs = [l.get("model_probability", 0.5) for l in legs]
    odds = [l.get("decimal_odds", l.get("mock_odds", 2.0)) for l in legs]
    return {
        "avg_prob": round(sum(probs) / len(probs), 4),
        "avg_odds": round(sum(odds) / len(odds), 2),
        "min_prob": round(min(probs), 4),
        "max_odds": round(max(odds), 2),
        "count": len(legs),
    }