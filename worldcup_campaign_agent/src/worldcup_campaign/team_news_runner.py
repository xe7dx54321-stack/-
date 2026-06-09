"""Team news runner: full pipeline for news, injury, lineup, context, and market explanation."""
import json, sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from worldcup_campaign.team_news_loader import load_team_news_fixture, normalize_team_news
from worldcup_campaign.injury_lineup_analyzer import analyze_injuries_and_lineups
from worldcup_campaign.team_context_signal import build_team_context_signals
from worldcup_campaign.market_explanation import build_market_explanations


@dataclass
class TeamNewsPreview:
    campaign_name: str = "worldcup_2026_high_odds_campaign"
    current_date: str = ""; current_bankroll: float = 100.0
    news_summary: dict = field(default_factory=dict)
    injury_summary: dict = field(default_factory=dict)
    context_summary: dict = field(default_factory=dict)
    explanation_summary: dict = field(default_factory=dict)
    safety: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    generated_at: str = ""
    analysis_only: bool = True; simulation_only: bool = True; not_betting_advice: bool = True


def _d(obj):
    if hasattr(obj, '__dataclass_fields__'): return {k: _d(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list): return [_d(i) for i in obj]
    return obj


class TeamNewsRunner:
    def __init__(self, config_paths: dict): self.paths = config_paths

    def run(self, date: str, bankroll: float, fixture_path: str = None):
        config = json.loads(Path(self.paths["team_news_config"]).read_text(encoding="utf-8-sig"))
        reports_dir = str(Path(self.paths["team_news_config"]).parent.parent / "reports" / "generated")
        if not fixture_path:
            fixture_path = str(Path(self.paths["team_news_config"]).parent.parent / "data" / "seed" / "team_news_seed.json")

        preview = TeamNewsPreview(current_date=date, current_bankroll=bankroll,
                                  generated_at=datetime.now().isoformat())
        fixture = load_team_news_fixture(fixture_path)

        news = normalize_team_news(fixture, config, date)
        preview.news_summary = _d(news); preview.warnings.extend(news.warnings)

        injury = analyze_injuries_and_lineups(news, config)
        preview.injury_summary = _d(injury); preview.warnings.extend(injury.warnings)

        context = build_team_context_signals(news, fixture, config)
        preview.context_summary = _d(context); preview.warnings.extend(context.warnings)

        explanation = build_market_explanations(news, context, injury, config)
        preview.explanation_summary = _d(explanation); preview.warnings.extend(explanation.warnings)

        preview.safety = {
            "campaign_analysis_only": True, "real_bet_execution": False, "auto_betting": False,
            "network_fetch_default_enabled": False, "analysis_only": True,
            "simulation_only": True, "not_betting_advice": True,
        }

        out_dir = Path(reports_dir); out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "team_news_preview.json").write_text(json.dumps(_d(preview), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        (out_dir / "team_news_preview.md").write_text(self._render_md(preview), encoding="utf-8")
        return preview

    def _render_md(self, p) -> str:
        ns = p.news_summary; inj = p.injury_summary; ctx = p.context_summary; ex = p.explanation_summary
        lines = [
            "# Team News & Context Report", "",
            f"**Date:** {p.current_date} | **Bankroll:** {p.current_bankroll}", "",
            "## 1. News Summary",
            f"- Items: {ns.get('news_item_count',0)} | Teams: {ns.get('team_count',0)} | Matches: {ns.get('match_count',0)}",
            f"- Reliability warnings: {ns.get('reliability_warning_count',0)}",
            f"- Freshness warnings: {ns.get('freshness_warning_count',0)}", "",
            "## 2. Injury & Lineup",
            f"- Injuries: {inj.get('injury_count',0)} | Suspensions: {inj.get('suspension_count',0)}",
            f"- Key absences: {inj.get('key_absence_count',0)}",
            f"- Lineups: {inj.get('lineup_count',0)} (confirmed: {inj.get('confirmed_lineup_count',0)})", "",
            "## 3. Context Signals",
            f"- Teams analyzed: {ctx.get('team_context_signal_count',0)}",
            f"- Positive: {ctx.get('positive_context_count',0)} | Negative: {ctx.get('negative_context_count',0)} | Mixed: {ctx.get('mixed_context_count',0)}",
            f"- Group pressure: {ctx.get('group_pressure_count',0)}",
            f"- Fatigue: {ctx.get('fatigue_signal_count',0)}", "",
            "## 4. Market Explanations",
            f"- Explanations: {ex.get('market_explanation_count',0)}",
            f"- Explained: {ex.get('explained_signal_count',0)} | Unexplained: {ex.get('unexplained_signal_count',0)}",
            f"- Insufficient news: {ex.get('insufficient_news_count',0)}", "",
            "## 5. Warnings",
        ]
        for w in p.warnings: lines.append(f"- {w}")
        lines.extend(["", "## 6. Safety",
            f"- Analysis only: {p.analysis_only}",
            f"- Not betting advice: {p.not_betting_advice}",
            "", "---", "*Fixture-based analysis. Not betting advice.*"])
        return "\n".join(lines)
