"""Dashboard runner: full pipeline for campaign dashboard generation."""
import json, sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from worldcup_campaign.dashboard_loader import DashboardLoader
from worldcup_campaign.dashboard_builder import DashboardBuilder
from worldcup_campaign.daily_brief_builder import DailyBriefBuilder
from worldcup_campaign.dashboard_renderer import DashboardRenderer


@dataclass
class DashboardPreview:
    campaign_name: str = "worldcup_2026_high_odds_campaign"
    current_date: str = ""
    current_bankroll: float = 100.0
    dashboard_mode: str = "current_day"
    dashboard: dict = field(default_factory=dict)
    daily_brief: dict = field(default_factory=dict)
    source_status: dict = field(default_factory=dict)
    safety: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    generated_at: str = ""
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


class DashboardRunner:
    def __init__(self, config_paths: dict):
        self.paths = config_paths

    def run(self, date: str, bankroll: float, mode: str = "current_day") -> DashboardPreview:
        # Load
        dc = json.loads(Path(self.paths["dashboard_config"]).read_text(encoding="utf-8-sig"))
        forbidden = dc.get("forbidden_fields", [])
        loader = DashboardLoader(forbidden)
        reports_dir = str(Path(self.paths["dashboard_config"]).parent.parent / "reports" / "generated")
        sources = loader.load_all(reports_dir)

        # Build dashboard
        builder = DashboardBuilder(self.paths["dashboard_config"])
        dashboard = builder.build(date, bankroll, sources, mode)

        # Build brief
        brief_builder = DailyBriefBuilder(self.paths["daily_brief_config"])
        brief = brief_builder.build(dashboard)

        # Validate
        renderer = DashboardRenderer(forbidden)
        renderer.validate_no_forbidden(asdict(dashboard))

        # Render
        out_dir = str(Path(reports_dir))
        output_paths = renderer.write_outputs(dashboard, brief, out_dir)

        # Safety
        safety = {
            "campaign_analysis_only": True, "real_bet_execution": False,
            "auto_betting": False, "simulation_only": True,
            "not_betting_advice": True, "no_real_money": True,
        }

        return DashboardPreview(
            current_date=date, current_bankroll=bankroll,
            dashboard_mode=mode,
            dashboard=asdict(dashboard),
            daily_brief=asdict(brief),
            source_status=sources.source_status,
            safety=safety,
            warnings=sources.warnings,
            generated_at=datetime.now().isoformat(),
        )
