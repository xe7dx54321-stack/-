"""Target contribution preview: estimates how much a candidate helps reach the target."""

from dataclasses import dataclass


@dataclass
class TargetContributionPreview:
    candidate_id: str
    required_multiplier: float
    candidate_multiplier: float
    contribution_ratio: float
    difficulty_label: str
    note: str


class TargetContributionCalculator:
    """Calculates how much a single bet contributes toward the target."""

    def __init__(self, target_bankroll: float = 1000000.0):
        self.target = target_bankroll

    def calculate(
        self, current_bankroll: float, candidate_odds: float, windows_left: int
    ) -> TargetContributionPreview:
        """Calculate target contribution for a candidate."""
        gap = self.target / current_bankroll
        candidate_mult = candidate_odds - 1.0  # profit multiplier
        ratio = candidate_mult / gap if gap > 0 else 0.0

        if ratio >= 1.0:
            diff = "single_hit_reaches_target"
        elif ratio >= 0.1:
            diff = "meaningful_contribution"
        elif ratio >= 0.01:
            diff = "small_step"
        else:
            diff = "negligible"

        note = f"Odds {candidate_odds:.2f}: profit multiplier {candidate_mult:.2f}x "
        note += f"vs required {gap:.1f}x. Contribution ratio: {ratio:.4f}"

        return TargetContributionPreview(
            candidate_id="",
            required_multiplier=round(gap, 2),
            candidate_multiplier=round(candidate_mult, 2),
            contribution_ratio=round(ratio, 4),
            difficulty_label=diff,
            note=note,
        )