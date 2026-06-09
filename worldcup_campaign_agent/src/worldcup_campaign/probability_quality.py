"""Probability quality and confidence assessment."""

from dataclasses import dataclass, field


@dataclass
class QualityAssessment:
    confidence: float
    data_quality: str
    confidence_label: str
    factors: list[str]
    is_seed_data: bool
    warnings: list[str] = field(default_factory=list)


def assess_quality(
    home_is_placeholder: bool,
    away_is_placeholder: bool,
    rating_diff_abs: float,
    is_knockout: bool,
    base_confidence: float,
) -> QualityAssessment:
    """Assess the quality of a probability estimate."""
    factors = []
    warnings = []

    if home_is_placeholder:
        factors.append("home_team_is_placeholder")
        warnings.append(f"_WARNING: home team rating is placeholder")
    if away_is_placeholder:
        factors.append("away_team_is_placeholder")
        warnings.append(f"_WARNING: away team rating is placeholder")
    if rating_diff_abs < 50:
        factors.append("ratings_very_close")
    if is_knockout:
        factors.append("knockout_match")
        warnings.append(f"_NOTE: knockout match, higher inherent uncertainty")

    label = "high" if base_confidence >= 0.6 else ("medium" if base_confidence >= 0.3 else "low")

    return QualityAssessment(
        confidence=round(base_confidence, 4),
        data_quality=("low" if (home_is_placeholder or away_is_placeholder) else "seed"),
        confidence_label=label,
        factors=factors,
        is_seed_data=True,
        warnings=warnings,
    )