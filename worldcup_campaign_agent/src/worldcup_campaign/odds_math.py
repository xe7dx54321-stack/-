"""Odds mathematics: implied probability, no-vig normalization, EV, edge, parlay."""


def decimal_odds_to_implied_probability(odds: float) -> float:
    """Convert decimal odds to implied probability.

    Formula: probability = 1 / odds
    """
    if odds <= 1.0:
        raise ValueError(f"Decimal odds must be > 1.0, got {odds}")
    return 1.0 / odds


def normalize_no_vig_probabilities(
    odds_by_selection: dict[str, float]
) -> dict[str, float]:
    """Remove the vig (overround) from odds to get fair probabilities.

    For each selection: raw_prob = 1/odds
    Total overround = sum(raw_probs)
    Fair probability = raw_prob / total_overround
    """
    if not odds_by_selection:
        raise ValueError("odds_by_selection cannot be empty")
    # Validate all odds > 1
    for sel, odds in odds_by_selection.items():
        if odds <= 1.0:
            raise ValueError(
                f"Selection '{sel}': decimal odds must be > 1.0, got {odds}"
            )
    raw_probs = {sel: 1.0 / odds for sel, odds in odds_by_selection.items()}
    total_overround = sum(raw_probs.values())
    if total_overround <= 0:
        raise ValueError("Total overround must be positive")
    return {sel: prob / total_overround for sel, prob in raw_probs.items()}


def calculate_edge(model_probability: float, market_probability: float) -> float:
    """Calculate edge: difference between model probability and market-implied probability."""
    if not 0.0 <= model_probability <= 1.0:
        raise ValueError(
            f"model_probability must be between 0 and 1, got {model_probability}"
        )
    if not 0.0 <= market_probability <= 1.0:
        raise ValueError(
            f"market_probability must be between 0 and 1, got {market_probability}"
        )
    return model_probability - market_probability


def calculate_ev(model_probability: float, decimal_odds: float) -> float:
    """Calculate expected value for a bet.

    Formula: EV = p * (odds - 1) - (1 - p)
    """
    if not 0.0 <= model_probability <= 1.0:
        raise ValueError(
            f"model_probability must be between 0 and 1, got {model_probability}"
        )
    if decimal_odds <= 1.0:
        raise ValueError(f"Decimal odds must be > 1.0, got {decimal_odds}")
    return model_probability * (decimal_odds - 1.0) - (1.0 - model_probability)


def calculate_parlay_odds(odds_list: list[float]) -> float:
    """Calculate parlay decimal odds (product of individual odds)."""
    if not odds_list:
        raise ValueError("odds_list cannot be empty")
    result = 1.0
    for odds in odds_list:
        if odds <= 1.0:
            raise ValueError(f"Decimal odds must be > 1.0, got {odds}")
        result *= odds
    return result


def calculate_parlay_probability(probability_list: list[float]) -> float:
    """Calculate parlay implied probability (product of individual probabilities)."""
    if not probability_list:
        raise ValueError("probability_list cannot be empty")
    result = 1.0
    for prob in probability_list:
        if not 0.0 <= prob <= 1.0:
            raise ValueError(
                f"Probability must be between 0 and 1, got {prob}"
            )
        result *= prob
    return result


def calculate_parlay_ev(
    probability_list: list[float], odds_list: list[float]
) -> float:
    """Calculate parlay expected value."""
    if len(probability_list) != len(odds_list):
        raise ValueError(
            f"probability_list length ({len(probability_list)}) "
            f"must match odds_list length ({len(odds_list)})"
        )
    joint_prob = calculate_parlay_probability(probability_list)
    parlay_odds = calculate_parlay_odds(odds_list)
    return calculate_ev(joint_prob, parlay_odds)
