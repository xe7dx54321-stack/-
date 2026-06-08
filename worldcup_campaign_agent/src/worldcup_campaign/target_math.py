"""Target mathematics: gap, required growth per window, urgency classification."""


def calculate_target_gap(current_bankroll: float, target_bankroll: float) -> float:
    """Calculate how many x the bankroll must grow to reach target."""
    if current_bankroll <= 0:
        raise ValueError("current_bankroll must be positive")
    if target_bankroll <= 0:
        raise ValueError("target_bankroll must be positive")
    return target_bankroll / current_bankroll


def calculate_required_growth_per_window(
    current_bankroll: float,
    target_bankroll: float,
    windows_left: int,
) -> float:
    """Calculate required growth multiplier per remaining window.

    Uses geometric growth: (target/current)^(1/windows_left)
    """
    if windows_left <= 0:
        raise ValueError("windows_left must be positive")
    if current_bankroll <= 0:
        raise ValueError("current_bankroll must be positive")
    if target_bankroll <= 0:
        raise ValueError("target_bankroll must be positive")

    if current_bankroll >= target_bankroll:
        return 1.0

    gap = target_bankroll / current_bankroll
    return gap ** (1.0 / windows_left)


def classify_target_urgency(required_growth_per_window: float) -> str:
    """Classify the urgency of reaching target based on required growth per window.

    low:       <= 1.1
    medium:    1.1 to 1.3 (exclusive)
    high:      1.3 to 2.0 (exclusive)
    extreme:   > 2.0
    """
    if required_growth_per_window <= 1.0:
        return "target_reached"
    elif required_growth_per_window <= 1.1:
        return "low"
    elif required_growth_per_window <= 1.3:
        return "medium"
    elif required_growth_per_window <= 2.0:
        return "high"
    else:
        return "extreme"
