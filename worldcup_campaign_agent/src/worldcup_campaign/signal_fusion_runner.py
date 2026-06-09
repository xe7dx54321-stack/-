"""Signal fusion runner: loads all sources, fuses signals, outputs upgraded strategy."""
import json, sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from worldcup_campaign.signal_fusion_engine import fuse_signals, FusionSummary


@dataclass
class SignalFusionPreview:
    campaign_name: str = "worldcup_2026_high_odds_campaign"
    current_date: str = ""; current_bankroll: float = 100.0
    source_summary: dict = field(default_factory=dict)
    fusion_summary: dict = field(default_factory=dict)
    support_summary: dict = field(default_factory=dict)
    score_summary: dict = field(default_factory=dict)
    safety: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    generated_at: str = ""
    analysis_only: bool = True; simulation_only: bool = True; not_betting_advice: bool = True


def _d(obj):
    if hasattr(obj, '__dataclass_fields__'): return {k: _d(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list): return [_d(i) for i in obj]
    return obj


class SignalFusionRunner:
    def __init__(self, config_paths: dict): self.paths = config_paths

    def run(self, date: str, bankroll: float):
        config = json.loads(Path(self.paths["fusion_config"]).read_text(encoding="utf-8-sig"))
        reports_dir = str(Path(self.paths["fusion_config"]).parent.parent / "reports" / "generated")
        rp = Path(reports_dir)

        preview = SignalFusionPreview(current_date=date, current_bankroll=bankroll,
                                      generated_at=datetime.now().isoformat())
        src = {}

        # Load sources
        def _load(fname, key):
            path = rp / fname
            if path.exists():
                src[key] = json.loads(path.read_text(encoding="utf-8"))
                return True
            src[key] = {}
            return False

        ev_ok = _load("ev_ranking_preview.json", "ev_ranking")
        int_ok = _load("integrated_daily_strategy.json", "integrated_strategy")
        me_ok = _load("market_expectation.json", "market_expectation")
        tn_ok = _load("team_news_preview.json", "team_news")
        preview.source_summary = {
            "ev_ranking_available": ev_ok, "integrated_strategy_available": int_ok,
            "market_expectation_available": me_ok, "team_news_available": tn_ok,
            "source_warning_count": sum(1 for v in [ev_ok, int_ok, me_ok, tn_ok] if not v),
        }

        # Extract candidates from EV ranking
        candidates = src.get("ev_ranking", {}).get("candidates",
                    src.get("ev_ranking", {}).get("ranked_candidates", []))
        if not candidates:
            candidates = src.get("integrated_strategy", {}).get("pool_candidates",
                         src.get("integrated_strategy", {}).get("candidates", []))

        # Extract signal data
        alignment_records = src.get("market_expectation", {}).get("alignment_summary", {}).get("records", [])
        quality_scores = src.get("market_expectation", {}).get("signal_quality_summary", {}).get("scores", [])
        context_signals = src.get("team_news", {}).get("context_summary", {}).get("signals", [])

        # Fuse
        fusion = fuse_signals(candidates, alignment_records, context_signals, quality_scores, config)
        preview.fusion_summary = _d(fusion)
        preview.warnings.extend(fusion.warnings)

        # Support summary
        preview.support_summary = {
            "market_supported_count": fusion.market_supported_count,
            "team_context_supported_count": fusion.team_context_supported_count,
            "low_quality_warning_count": fusion.low_quality_warning_count,
            "unexplained_disagreement_count": fusion.unexplained_disagreement_count,
        }

        # Score summary
        if fusion.candidates:
            base_avg = sum(c.base_campaign_score for c in fusion.candidates) / len(fusion.candidates)
            upg_avg = sum(c.upgraded_campaign_score for c in fusion.candidates) / len(fusion.candidates)
        else:
            base_avg = upg_avg = 0
        preview.score_summary = {
            "average_base_campaign_score": round(base_avg, 4),
            "average_upgraded_campaign_score": round(upg_avg, 4),
            "average_score_adjustment": round(upg_avg - base_avg, 4),
            "core_eligible_count": sum(1 for c in fusion.candidates if c.upgraded_bucket == "core"),
            "edge_eligible_count": sum(1 for c in fusion.candidates if c.upgraded_bucket in ("edge", "core")),
            "attack_eligible_count": sum(1 for c in fusion.candidates if c.upgraded_bucket in ("attack", "edge", "core")),
            "futures_eligible_count": sum(1 for c in fusion.candidates if c.upgraded_bucket in ("futures", "attack")),
        }

        preview.safety = {
            "campaign_analysis_only": True, "real_bet_execution": False, "auto_betting": False,
            "network_fetch_default_enabled": False, "analysis_only": True,
            "simulation_only": True, "not_betting_advice": True,
        }

        out_dir = rp; out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "signal_fusion_preview.json").write_text(json.dumps(_d(preview), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        (out_dir / "signal_fusion_preview.md").write_text(self._render_md(preview), encoding="utf-8")
        return preview

    def _render_md(self, p) -> str:
        fu = p.fusion_summary; sc = p.score_summary; su = p.support_summary
        lines = [
            "# Signal Fusion & Strategy Upgrade", "",
            f"**Date:** {p.current_date} | **Bankroll:** {p.current_bankroll}", "",
            "## 1. Sources",
            f"- EV Ranking: {p.source_summary.get('ev_ranking_available')}",
            f"- Integrated Strategy: {p.source_summary.get('integrated_strategy_available')}",
            f"- Market Expectation: {p.source_summary.get('market_expectation_available')}",
            f"- Team News: {p.source_summary.get('team_news_available')}", "",
            "## 2. Fusion Results",
            f"- Candidates: {fu.get('candidate_count',0)} | Fused: {fu.get('fused_signal_count',0)}",
            f"- Upgraded: {fu.get('upgraded_candidate_count',0)}",
            f"- Promoted: {fu.get('promoted_count',0)} | Demoted: {fu.get('demoted_count',0)}",
            f"- Review required: {fu.get('review_required_count',0)} | Watch only: {fu.get('watch_only_count',0)}", "",
            "## 3. Support Signals",
            f"- Market supported: {su.get('market_supported_count',0)}",
            f"- Team context supported: {su.get('team_context_supported_count',0)}",
            f"- Low quality warnings: {su.get('low_quality_warning_count',0)}",
            f"- Unexplained disagreements: {su.get('unexplained_disagreement_count',0)}", "",
            "## 4. Score Upgrade",
            f"- Avg base score: {sc.get('average_base_campaign_score',0):.4f}",
            f"- Avg upgraded score: {sc.get('average_upgraded_campaign_score',0):.4f}",
            f"- Avg adjustment: {sc.get('average_score_adjustment',0):.4f}",
            f"- Core eligible: {sc.get('core_eligible_count',0)}",
            f"- Edge eligible: {sc.get('edge_eligible_count',0)}",
            f"- Attack eligible: {sc.get('attack_eligible_count',0)}",
            f"- Futures eligible: {sc.get('futures_eligible_count',0)}", "",
            "## 5. Warnings",
        ]
        for w in p.warnings: lines.append(f"- {w}")
        lines.extend(["", "## 6. Safety", f"- Analysis only: {p.analysis_only}", f"- Not betting advice: {p.not_betting_advice}", "", "---", "*Signal fusion analysis. Not betting advice.*"])
        return "\n".join(lines)
