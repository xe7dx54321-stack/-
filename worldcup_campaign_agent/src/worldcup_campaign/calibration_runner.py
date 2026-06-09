"""Calibration runner: full pipeline for model calibration and review."""
import json, sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from worldcup_campaign.source_alignment import (
    load_source_alignment_policy, check_source_alignment, load_dashboard_sources_for_alignment
)
from worldcup_campaign.calibration_metrics import CalibrationBins
from worldcup_campaign.probability_calibration import (
    build_probability_calibration_records, review_probability_calibration, ProbabilityCalibrationReview
)
from worldcup_campaign.bucket_performance_review import review_bucket_performance, BucketPerformanceReview
from worldcup_campaign.parlay_performance_review import review_parlay_performance, ParlayPerformanceReview
from worldcup_campaign.futures_performance_review import review_futures_performance, FuturesPerformanceReview
from worldcup_campaign.model_recommendation import build_model_recommendations, CalibrationRecommendations


@dataclass
class ModelCalibrationReview:
    campaign_name: str = "worldcup_2026_high_odds_campaign"
    current_date: str = ""
    current_bankroll: float = 100.0
    source_alignment_result: dict = field(default_factory=dict)
    probability_calibration_review: dict = field(default_factory=dict)
    bucket_performance_review: dict = field(default_factory=dict)
    parlay_performance_review: dict = field(default_factory=dict)
    futures_performance_review: dict = field(default_factory=dict)
    calibration_recommendations: dict = field(default_factory=dict)
    safety: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    generated_at: str = ""
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


def _dataclass_to_dict(obj):
    """Convert dataclass or object to dict, handling nested dataclasses."""
    if hasattr(obj, '__dataclass_fields__'):
        return {k: _dataclass_to_dict(v) for k, v in asdict(obj).items()}
    return obj


class CalibrationRunner:
    def __init__(self, config_paths: dict):
        self.paths = config_paths

    def run(self, date: str, bankroll: float) -> ModelCalibrationReview:
        reports_dir = str(Path(self.paths["calibration_config"]).parent.parent / "reports" / "generated")

        # Load configs
        alignment_policy = load_source_alignment_policy(self.paths["source_alignment_policy"])
        calibration_config = json.loads(Path(self.paths["calibration_config"]).read_text(encoding="utf-8-sig"))
        review_policy = json.loads(Path(self.paths["model_review_policy"]).read_text(encoding="utf-8-sig"))
        review_policy.setdefault("min_sample_size_for_recommendation", calibration_config.get("min_sample_size_for_recommendation", 10))

        review = ModelCalibrationReview(
            current_date=date,
            current_bankroll=bankroll,
            generated_at=datetime.now().isoformat(),
        )

        # 1. Source alignment
        dashboard_sources = load_dashboard_sources_for_alignment(reports_dir)
        source_result = check_source_alignment(date, bankroll, dashboard_sources, alignment_policy)
        review.source_alignment_result = _dataclass_to_dict(source_result)
        review.warnings.extend(source_result.warnings)

        # 2. Probability calibration
        settlement = dashboard_sources.get("postmatch_settlement", {})
        match_prob = dashboard_sources.get("match_probability", {})
        ledger = settlement.get("simulation_ledger", settlement.get("ledger", []))
        manual_results = settlement.get("manual_results", None)

        prob_records = build_probability_calibration_records(ledger, match_prob, manual_results)
        prob_review = review_probability_calibration(prob_records, calibration_config)
        review.probability_calibration_review = _dataclass_to_dict(prob_review)
        review.warnings.extend(prob_review.warnings)

        # 3. Bucket performance
        bucket_review = review_bucket_performance(settlement, ledger, calibration_config)
        review.bucket_performance_review = _dataclass_to_dict(bucket_review)
        review.warnings.extend(bucket_review.warnings)

        # 4. Parlay performance
        parlay_preview = dashboard_sources.get("parlay_preview", {})
        parlay_review = review_parlay_performance(parlay_preview, settlement, calibration_config)
        review.parlay_performance_review = _dataclass_to_dict(parlay_review)
        review.warnings.extend(parlay_review.warnings)

        # 5. Futures performance
        futures_preview = dashboard_sources.get("futures_preview", {})
        futures_review = review_futures_performance(futures_preview, settlement, calibration_config)
        review.futures_performance_review = _dataclass_to_dict(futures_review)
        review.warnings.extend(futures_review.warnings)

        # 6. Recommendations
        recs = build_model_recommendations(
            prob_review, bucket_review, parlay_review, futures_review,
            source_result, review_policy
        )
        review.calibration_recommendations = _dataclass_to_dict(recs)

        # 7. Safety
        review.safety = {
            "campaign_analysis_only": True,
            "real_bet_execution": False,
            "auto_betting": False,
            "external_betting_api_allowed": False,
            "real_money_instruction_allowed": False,
            "analysis_only": True,
            "simulation_only": True,
            "not_betting_advice": True,
        }

        # 8. Write outputs
        self._write_outputs(review, reports_dir)

        return review

    def _write_outputs(self, review: ModelCalibrationReview, reports_dir: str):
        out_dir = Path(reports_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # JSON
        json_path = out_dir / "model_calibration_review.json"
        json_path.write_text(json.dumps(_dataclass_to_dict(review), indent=2, ensure_ascii=False, default=str), encoding="utf-8")

        # Recommendations JSON
        rec_path = out_dir / "calibration_recommendations.json"
        rec_path.write_text(json.dumps(review.calibration_recommendations, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

        # Markdown
        md_path = out_dir / "model_calibration_review.md"
        md_path.write_text(self._render_markdown(review), encoding="utf-8")

    def _render_markdown(self, review: ModelCalibrationReview) -> str:
        sa = review.source_alignment_result
        pc = review.probability_calibration_review
        bp = review.bucket_performance_review
        pp = review.parlay_performance_review
        fp = review.futures_performance_review
        recs = review.calibration_recommendations

        lines = [
            "# Model Calibration & Review",
            "",
            "## 1. Campaign Context",
            "",
            f"* Date: {review.current_date}",
            f"* Input bankroll: {review.current_bankroll}",
            f"* Snapshot bankroll: {sa.get('snapshot_bankroll', 'N/A')}",
            f"* Display bankroll: {sa.get('display_bankroll', 'N/A')}",
            f"* Source alignment: {'OK' if sa.get('date_aligned') and sa.get('bankroll_aligned') else 'MISMATCH'}",
            "",
            "## 2. Source Alignment & Freshness",
            "",
            "| Source | Date | Bankroll | Freshness | Warning |",
            "|--------|------|----------|-----------|---------|",
        ]
        freshness = sa.get("source_freshness_summary", {})
        source_details = freshness.get("source_details", {}) if isinstance(freshness, dict) else {}
        for src_name, status in source_details.items():
            lines.append(f"| {src_name} | {sa.get('snapshot_date', '-')} | - | {status} | |")

        lines.extend([
            "",
            "## 3. Probability Calibration Review",
            "",
            f"* Records: {pc.get('record_count', 0)}",
            f"* Realized: {pc.get('realized_count', 0)}",
            f"* Pending: {pc.get('pending_count', 0)}",
            f"* Brier score: {pc.get('brier_score', 'N/A')}",
            f"* Log loss: {pc.get('log_loss', 'N/A')}",
            f"* Hit rate: {pc.get('hit_rate', 'N/A')}",
            f"* Small sample warning: {'Yes' if pc.get('warnings') else 'No'}",
            "",
            "## 4. Calibration Buckets",
            "",
            "| Probability Bin | Samples | Avg Predicted | Observed Rate | Gap |",
            "|----------------|---------|---------------|---------------|-----|",
        ])
        bins = pc.get("calibration_bins", [])
        if isinstance(bins, list):
            for b in bins:
                if isinstance(b, dict):
                    lines.append(
                        f"| [{b.get('bin_lower', 0):.1f}, {b.get('bin_upper', 1):.1f}) "
                        f"| {b.get('sample_count', 0)} "
                        f"| {b.get('average_predicted', 0):.3f} "
                        f"| {b.get('observed_rate', 0):.3f} "
                        f"| {b.get('calibration_gap', 0):.3f} |"
                    )

        lines.extend([
            "",
            "## 5. Bucket Performance",
            "",
            "| Bucket | Candidates | Realized | Pending | Hit Rate | Simulated P/L | Notes |",
            "|--------|-----------|----------|---------|----------|---------------|-------|",
        ])
        bds = bp.get("bucket_breakdowns", {})
        if isinstance(bds, dict):
            for bn, bd in bds.items():
                if isinstance(bd, dict):
                    hr = f"{bd.get('hit_rate', 0):.2f}" if bd.get('hit_rate') is not None else "N/A"
                    lines.append(
                        f"| {bn} | {bd.get('candidate_count', 0)} | {bd.get('realized_count', 0)} "
                        f"| {bd.get('pending_count', 0)} | {hr} "
                        f"| {bd.get('simulated_pl', 0):+.2f} | {bd.get('notes', '')[:60]} |"
                    )

        lines.extend([
            "",
            "## 6. Parlay Performance",
            "",
            f"* Raw combinations: {pp.get('raw_combination_count', 0)}",
            f"* Blocked: {pp.get('blocked_combination_count', 0)}",
            f"* Ranked: {pp.get('ranked_parlay_count', 0)}",
            f"* Resolved: {pp.get('resolved_parlay_count', 0)}",
            f"* Pending: {pp.get('pending_parlay_count', 0)}",
            f"* Same-match blocks: {pp.get('correlation_warning_summary', {}).get('same_match_blocked', 0)}",
            f"* Same-group warnings: {pp.get('correlation_warning_summary', {}).get('same_group_warnings', 0)}",
            "",
            "## 7. Futures Performance",
            "",
            f"* Futures candidates: {fp.get('futures_candidate_count', 0)}",
            f"* Pending: {fp.get('pending_futures_count', 0)}",
            f"* Settled: {fp.get('settled_futures_count', 0)}",
            f"* Winner probability sum warning: {fp.get('winner_probability_sum_warning', 'N/A')}",
            f"* Golden boot deferred: {fp.get('path_model_warning_summary', {}).get('golden_boot_deferred', True)}",
            f"* Path model warning: {fp.get('path_model_warning_summary', {}).get('path_simulation_note', '')}",
            "",
            "## 8. Recommendations",
            "",
            "| Dimension | Recommendation | Target | Reason | Sample Size | Confidence |",
            "|-----------|---------------|--------|--------|-------------|------------|",
        ])
        rec_list = recs.get("recommendations", [])
        if isinstance(rec_list, list):
            for r in rec_list:
                if isinstance(r, dict):
                    lines.append(
                        f"| {r.get('dimension', '')} | {r.get('recommendation_type', '')} "
                        f"| {r.get('target', '')} | {r.get('reason', '')[:80]} "
                        f"| {r.get('sample_size', 0)} | {r.get('confidence', '')} |"
                    )

        lines.extend([
            "",
            "## 9. Safety Boundary",
            "",
            f"* Analysis only: {review.analysis_only}",
            f"* Simulation only: {review.simulation_only}",
            f"* Not betting advice: {review.not_betting_advice}",
            f"* Real bet execution: {review.safety.get('real_bet_execution', False)}",
            f"* Auto betting: {review.safety.get('auto_betting', False)}",
            f"* External betting API: {review.safety.get('external_betting_api_allowed', False)}",
            "",
            "## 10. Warnings / Data Gaps",
            "",
        ])
        for w in review.warnings:
            lines.append(f"* {w}")

        lines.extend([
            "",
            "---",
            "",
            "*This is model review only. Not betting advice. No real bookmaker account used.*",
            "*No real-money settlement performed. Pending is not realized loss.*",
            "*Small sample does not justify aggressive model changes.*",
        ])

        return "\n".join(lines)
