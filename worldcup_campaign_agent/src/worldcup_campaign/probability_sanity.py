"""Probability sanity guard: detect and repair abnormal probabilities."""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SanityResult:
    is_valid: bool
    repaired: bool
    blocked: bool
    warnings: list[str] = field(default_factory=list)
    repaired_home_prob: float = 0.0
    repaired_draw_prob: float = 0.0
    repaired_away_prob: float = 0.0
    repair_count: int = 0
    block_reason: str = ""


class ProbabilitySanityGuard:
    """Checks and repairs abnormal probabilities before they enter EV ranking."""

    def __init__(self, config_path: str):
        self.config = json.loads(Path(config_path).read_text(encoding="utf-8-sig"))
        self.enabled = self.config.get("enabled", True)
        self.f1x2 = self.config.get("football_1x2", {})
        self.min_draw = self.f1x2.get("min_draw_probability", 0.12)
        self.min_home = self.f1x2.get("min_home_win_probability", 0.03)
        self.min_away = self.f1x2.get("min_away_win_probability", 0.03)
        self.sum_tol = self.f1x2.get("probability_sum_tolerance", 0.0001)
        self.repair_mode = self.f1x2.get("repair_mode", "clamp_and_renormalize")
        self.allow_block = self.config.get("allow_block_on_severe", True)

    def check_1x2(self, home_prob: float, draw_prob: float, away_prob: float) -> SanityResult:
        """Check and repair 1x2 probabilities."""
        warnings = []
        repaired = False
        blocked = False
        block_reason = ""
        rh, rd, ra = home_prob, draw_prob, away_prob

        # Check probability sum
        total = rh + rd + ra
        if abs(total - 1.0) > self.sum_tol:
            warnings.append(f"Probability sum {total:.4f} deviates from 1.0 by {abs(total-1.0):.4f}")
            # Renormalize
            rh /= total
            rd /= total
            ra /= total
            repaired = True

        # Check draw probability floor
        if rd < self.min_draw:
            warnings.append(
                f"Draw probability {rd:.3%} is below minimum {self.min_draw:.0%}. "
                f"Repairing with {self.repair_mode}."
            )
            deficit = self.min_draw - rd
            rd = self.min_draw
            # Redistribute from home/away proportionally
            denom = rh + ra
            if denom > 0:
                rh = rh - deficit * (rh / denom)
                ra = ra - deficit * (ra / denom)
            # Final renormalize
            total2 = rh + rd + ra
            rh /= total2
            rd /= total2
            ra /= total2
            repaired = True

        # Floor for very small probabilities
        if rh < self.min_home:
            warnings.append(f"Home win probability {rh:.3%} below minimum {self.min_home:.0%}")
            rh = self.min_home
            repaired = True
        if ra < self.min_away:
            warnings.append(f"Away win probability {ra:.3%} below minimum {self.min_away:.0%}")
            ra = self.min_away
            repaired = True

        # Final renormalize after all repairs
        total3 = rh + rd + ra
        if abs(total3 - 1.0) > self.sum_tol:
            rh /= total3
            rd /= total3
            ra /= total3

        # Block on severe (e.g., all three at minimum)
        if self.allow_block and rh <= self.min_home + 0.001 and rd <= self.min_draw + 0.001 and ra <= self.min_away + 0.001:
            blocked = True
            block_reason = "All probabilities at minimum, blocking from ranking"

        return SanityResult(
            is_valid=not blocked,
            repaired=repaired,
            blocked=blocked,
            warnings=warnings,
            repaired_home_prob=round(rh, 4),
            repaired_draw_prob=round(rd, 4),
            repaired_away_prob=round(ra, 4),
            repair_count=1 if repaired else 0,
            block_reason=block_reason,
        )

    def get_effective_1x2(self, home_prob: float, draw_prob: float, away_prob: float) -> tuple:
        """Get effective 1x2 probabilities after sanity check."""
        result = self.check_1x2(home_prob, draw_prob, away_prob)
        if result.blocked:
            return None
        return (result.repaired_home_prob, result.repaired_draw_prob, result.repaired_away_prob, result)