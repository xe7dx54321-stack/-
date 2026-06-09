"""Model recommendation: generates calibration-based model/weight adjustment suggestions."""
from dataclasses import dataclass, field


@dataclass
class CalibrationRecommendation:
    recommendation_id: str = ""
    dimension: str = ""
    recommendation_type: str = "no_action"
    target: str = ""
    reason: str = ""
    sample_size: int = 0
    confidence: str = "low"
    expected_effect: str = ""
    not_betting_advice: bool = True


@dataclass
class CalibrationRecommendations:
    recommendations: list = field(default_factory=list)
    summary: str = ""
    warning_count: int = 0
    requires_human_review: bool = True
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


FORBIDDEN_RECOMMENDATIONS = [
    "place_real_bet",
    "increase_real_stake",
    "chase_loss",
    "borrow_money",
    "guaranteed_profit",
]


def build_model_recommendations(
    probability_review,
    bucket_review,
    parlay_review,
    futures_review,
    source_alignment_result,
    policy: dict
) -> CalibrationRecommendations:
    result = CalibrationRecommendations()
    forbidden = policy.get("forbidden_recommendations", FORBIDDEN_RECOMMENDATIONS)
    min_sample = policy.get("min_sample_size_for_recommendation", 10)

    recs = []
    idx = 0

    # 1. Probability calibration recommendations
    if probability_review:
        realized = getattr(probability_review, "realized_count", 0)
        brier = getattr(probability_review, "brier_score", None)
        hit_rate = getattr(probability_review, "hit_rate", None)

        if realized < min_sample:
            idx += 1
            recs.append(CalibrationRecommendation(
                recommendation_id=f"rec_{idx:03d}",
                dimension="probability_calibration",
                recommendation_type="needs_more_sample",
                target="all_probability_models",
                reason=f"Only {realized} realized records; need at least {min_sample} for confident recommendations.",
                sample_size=realized,
                confidence="low",
                expected_effect="Defer model adjustments until sufficient data accumulates.",
            ))
        else:
            # Analyze calibration gaps
            bins = getattr(probability_review, "calibration_bins", [])
            for b in bins if isinstance(bins, list) else []:
                if isinstance(b, dict):
                    gap = abs(b.get("calibration_gap", 0))
                    samples = b.get("sample_count", 0)
                    avg_pred = b.get("average_predicted", 0)
                    obs_rate = b.get("observed_rate", 0)
                    if gap > 0.15 and samples >= 5:
                        idx += 1
                        bias_type = "overconfident" if avg_pred > obs_rate else "underconfident"
                        recs.append(CalibrationRecommendation(
                            recommendation_id=f"rec_{idx:03d}",
                            dimension="probability_calibration",
                            recommendation_type="review_model_bias",
                            target=f"bin_{b.get('bin_lower',0):.2f}_{b.get('bin_upper',1):.2f}",
                            reason=f"Calibration gap={gap:.3f} ({bias_type}); avg_pred={avg_pred:.3f}, obs={obs_rate:.3f} with n={samples}.",
                            sample_size=samples,
                            confidence="medium" if samples >= 20 else "low",
                            expected_effect="Adjust probability estimates in this range to reduce calibration gap.",
                        ))

            # Overall Brier recommendation
            if brier is not None and brier > 0.25:
                idx += 1
                recs.append(CalibrationRecommendation(
                    recommendation_id=f"rec_{idx:03d}",
                    dimension="probability_calibration",
                    recommendation_type="review_model_bias",
                    target="overall_probability_model",
                    reason=f"High Brier score ({brier:.3f}) indicates poor probability calibration.",
                    sample_size=realized,
                    confidence="medium",
                    expected_effect="Review and recalibrate probability estimation; consider model recalibration.",
                ))

            # Overall hit rate
            if hit_rate is not None and hit_rate < 0.3 and realized >= min_sample:
                idx += 1
                recs.append(CalibrationRecommendation(
                    recommendation_id=f"rec_{idx:03d}",
                    dimension="probability_calibration",
                    recommendation_type="review_model_bias",
                    target="probability_thresholds",
                    reason=f"Low hit rate ({hit_rate:.2f}) with adequate sample ({realized}). Review selection thresholds.",
                    sample_size=realized,
                    confidence="medium",
                    expected_effect="Raise probability thresholds or adjust market type weights.",
                ))

    # 2. Bucket performance recommendations
    if bucket_review:
        breakdowns = getattr(bucket_review, "bucket_breakdowns", {})
        for bucket_name, bd in (breakdowns.items() if isinstance(breakdowns, dict) else []):
            if not isinstance(bd, dict):
                continue
            realized = bd.get("realized_count", 0)
            hit_rate_b = bd.get("hit_rate")
            if hit_rate_b is not None and realized >= min_sample:
                if bucket_name == "attack" and hit_rate_b < 0.1:
                    idx += 1
                    recs.append(CalibrationRecommendation(
                        recommendation_id=f"rec_{idx:03d}",
                        dimension="bucket_performance",
                        recommendation_type="keep_weight",
                        target="attack_bucket_score_weight",
                        reason=f"Attack bucket hit_rate={hit_rate_b:.2f} with n={realized}. Low hit rate expected for high-odds path; maintain weight, evaluate over larger sample.",
                        sample_size=realized,
                        confidence="medium",
                        expected_effect="Maintain attack bucket allocation; low hit rate is expected for this strategy profile.",
                    ))
                elif bucket_name == "core" and hit_rate_b < 0.5:
                    idx += 1
                    recs.append(CalibrationRecommendation(
                        recommendation_id=f"rec_{idx:03d}",
                        dimension="bucket_performance",
                        recommendation_type="review_model_bias",
                        target="core_bucket_selection",
                        reason=f"Core bucket hit_rate={hit_rate_b:.2f} below expected floor for high-probability candidates.",
                        sample_size=realized,
                        confidence="medium",
                        expected_effect="Review core bucket probability thresholds and candidate quality.",
                    ))

    # 3. Parlay performance recommendations
    if parlay_review:
        resolved = getattr(parlay_review, "resolved_parlay_count", 0)
        if resolved > 0 and resolved < min_sample:
            idx += 1
            recs.append(CalibrationRecommendation(
                recommendation_id=f"rec_{idx:03d}",
                dimension="parlay_performance",
                recommendation_type="needs_more_sample",
                target="parlay_combination_strategy",
                reason=f"Only {resolved} resolved parlay outcomes; insufficient for statistical conclusions.",
                sample_size=resolved,
                confidence="low",
                expected_effect="Continue generating parlay candidates; defer weight adjustments.",
            ))

        blocked = getattr(parlay_review, "blocked_combination_count", 0)
        if blocked > 0:
            # This is expected behavior, not a problem
            pass

    # 4. Futures performance recommendations
    if futures_review:
        pending = getattr(futures_review, "pending_futures_count", 0)
        if pending > 0:
            idx += 1
            recs.append(CalibrationRecommendation(
                recommendation_id=f"rec_{idx:03d}",
                dimension="futures_performance",
                recommendation_type="needs_more_sample",
                target="futures_path_model",
                reason=f"{pending} futures still pending; tournament-long settlement horizon. Cannot evaluate futures model yet.",
                sample_size=pending,
                confidence="low",
                expected_effect="Maintain current futures model weights; re-evaluate after more futures settle.",
            ))

    # 5. Source alignment recommendations
    if source_alignment_result:
        if not getattr(source_alignment_result, "bankroll_aligned", True):
            idx += 1
            recs.append(CalibrationRecommendation(
                recommendation_id=f"rec_{idx:03d}",
                dimension="source_alignment",
                recommendation_type="review_data_quality",
                target="dashboard_source_refresh",
                reason="CLI bankroll differs from snapshot bankroll. Ensure consistent data source or refresh generated reports.",
                sample_size=0,
                confidence="high",
                expected_effect="Align CLI inputs with generated snapshot or refresh all modules.",
            ))

    # Validate no forbidden recommendations
    for rec in recs:
        if rec.recommendation_type in forbidden:
            recs.remove(rec)

    result.recommendations = [{
        "recommendation_id": r.recommendation_id,
        "dimension": r.dimension,
        "recommendation_type": r.recommendation_type,
        "target": r.target,
        "reason": r.reason,
        "sample_size": r.sample_size,
        "confidence": r.confidence,
        "expected_effect": r.expected_effect,
        "not_betting_advice": r.not_betting_advice,
    } for r in recs]

    result.warning_count = sum(1 for r in recs if r.confidence == "low")
    result.summary = f"{len(recs)} recommendations generated. {sum(1 for r in recs if r.recommendation_type == 'needs_more_sample')} need more samples. {'Requires human review.' if result.requires_human_review else ''}"

    return result
