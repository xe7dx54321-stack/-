"""Market expectation runner: fuses model, sportsbook, and polymarket expectations."""
import json, sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from worldcup_campaign.market_expectation_loader import (
    load_market_expectation_sources, extract_model_probabilities,
    extract_sportsbook_probabilities, extract_polymarket_probabilities
)
from worldcup_campaign.signal_quality import assess_signal_quality
from worldcup_campaign.market_alignment import assess_market_alignment
from worldcup_campaign.blended_probability import compute_blended_probability


@dataclass
class MarketExpectationPreview:
    campaign_name: str = "worldcup_2026_high_odds_campaign"
    current_date: str = ""
    current_bankroll: float = 100.0
    source_summary: dict = field(default_factory=dict)
    signal_quality_summary: dict = field(default_factory=dict)
    alignment_summary: dict = field(default_factory=dict)
    blended_summary: dict = field(default_factory=dict)
    safety: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    generated_at: str = ""
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


def _d(obj):
    if hasattr(obj, '__dataclass_fields__'):
        return {k: _d(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_d(i) for i in obj]
    return obj


class MarketExpectationRunner:
    def __init__(self, config_paths: dict):
        self.paths = config_paths

    def run(self, date: str, bankroll: float):
        config = json.loads(Path(self.paths["expectation_config"]).read_text(encoding="utf-8-sig"))
        reports_dir = str(Path(self.paths["expectation_config"]).parent.parent / "reports" / "generated")

        preview = MarketExpectationPreview(current_date=date, current_bankroll=bankroll,
                                           generated_at=datetime.now().isoformat())

        # Load sources
        sources = load_market_expectation_sources(reports_dir)
        preview.source_summary = {
            "model_available": sources.model_available,
            "sportsbook_available": sources.sportsbook_available,
            "polymarket_available": sources.polymarket_available,
            "source_warnings": sources.source_warnings,
        }
        preview.warnings.extend(sources.source_warnings)

        # Extract probabilities
        model_probs = extract_model_probabilities(sources.model_data)
        sportsbook_probs = extract_sportsbook_probabilities(sources.sportsbook_data)
        polymarket_probs = extract_polymarket_probabilities(sources.polymarket_data)

        src = {
            "model_probs": model_probs, "sportsbook_probs": sportsbook_probs, "polymarket_probs": polymarket_probs,
            "model_data": sources.model_data, "sportsbook_data": sources.sportsbook_data,
            "polymarket_data": sources.polymarket_data,
        }

        # Signal quality
        quality = assess_signal_quality(src, config)
        preview.signal_quality_summary = _d(quality)
        preview.warnings.extend(quality.warnings)

        # Market alignment
        alignment = assess_market_alignment(src, config)
        preview.alignment_summary = _d(alignment)
        preview.warnings.extend(alignment.warnings)

        # Blended probability
        blended = compute_blended_probability(src, quality, config)
        preview.blended_summary = _d(blended)
        preview.warnings.extend(blended.warnings)

        # Safety
        preview.safety = {
            "campaign_analysis_only": True, "real_bet_execution": False, "auto_betting": False,
            "external_betting_api_allowed": False, "network_fetch_default_enabled": False,
            "order_submission_allowed": False, "wallet_connection_allowed": False,
            "analysis_only": True, "simulation_only": True, "not_betting_advice": True,
        }

        out_dir = Path(reports_dir); out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "market_expectation.json").write_text(json.dumps(_d(preview), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        (out_dir / "market_expectation.md").write_text(self._render_md(preview), encoding="utf-8")
        return preview

    def _render_md(self, p) -> str:
        sq = p.signal_quality_summary; al = p.alignment_summary; bl = p.blended_summary
        lines = [
            "# Market Expectation Report", "",
            f"**Date:** {p.current_date} | **Bankroll:** {p.current_bankroll}", "",
            "## 1. Sources",
            f"- Model: {p.source_summary.get('model_available')}",
            f"- Sportsbook: {p.source_summary.get('sportsbook_available')}",
            f"- Polymarket: {p.source_summary.get('polymarket_available')}", "",
            "## 2. Signal Quality",
            f"- High: {sq.get('high_quality_count',0)} | Medium: {sq.get('medium_quality_count',0)} | Low: {sq.get('low_quality_count',0)}",
            f"- Average score: {sq.get('average_quality_score',0):.3f}",
            f"- Penalties: {sq.get('penalty_count',0)}", "",
            "## 3. Market Alignment",
            f"- Records: {al.get('record_count',0)}",
            f"- Aligned: {al.get('market_aligned_count',0)}",
            f"- Model above: {al.get('model_above_market_count',0)} | Below: {al.get('model_below_market_count',0)}",
            f"- SB-PM disagree: {al.get('sportsbook_polymarket_disagree_count',0)}",
            f"- Major disagreements: {al.get('major_disagreement_count',0)}",
            f"- Insufficient data: {al.get('insufficient_data_count',0)}", "",
            "## 4. Blended Probability",
            f"- Records: {bl.get('blended_record_count',0)}",
            f"- Avg model weight: {bl.get('average_model_weight',0):.3f}",
            f"- Avg sportsbook weight: {bl.get('average_sportsbook_weight',0):.3f}",
            f"- Avg polymarket weight: {bl.get('average_polymarket_weight',0):.3f}", "",
            "## 5. Warnings",
        ]
        for w in p.warnings: lines.append(f"- {w}")
        lines.extend(["", "## 6. Safety",
            f"- Analysis only: {p.analysis_only}",
            f"- Not betting advice: {p.not_betting_advice}",
            "", "---", "*Market expectation analysis. Not betting advice.*"])
        return "\n".join(lines)
