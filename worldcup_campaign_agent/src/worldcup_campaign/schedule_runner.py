"""Schedule runner: full pipeline for campaign timeline and daily execution plans."""
import json, sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from worldcup_campaign.campaign_schedule import CampaignScheduleBuilder
from worldcup_campaign.operator_checklist import OperatorChecklistBuilder
from worldcup_campaign.daily_execution_planner import DailyExecutionPlanner


@dataclass
class CampaignTimelinePreview:
    campaign_name: str = "worldcup_2026_high_odds_campaign"
    generated_at: str = ""
    day_count: int = 0
    matchday_count: int = 0
    non_matchday_count: int = 0
    stage_counts: dict = field(default_factory=dict)
    upcoming_schedule: list = field(default_factory=list)
    today_schedule: dict = field(default_factory=dict)
    operator_checklist: list = field(default_factory=list)
    path_sanity_warnings: list = field(default_factory=list)
    safety: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


class ScheduleRunner:
    def __init__(self, config_paths: dict):
        self.paths = config_paths

    def run(self, date_str: str, bankroll: float = 100.0,
            winner_prob_sum: float = None, full_timeline: bool = False) -> CampaignTimelinePreview:
        # Build schedule
        builder = CampaignScheduleBuilder(
            self.paths["schedule_config"], self.paths["stage_map"],
            self.paths.get("match_registry")
        )

        today = builder.build_today_schedule(date_str, bankroll)

        # Build full timeline for stats
        timeline = builder.build_full_timeline()
        matchdays = [s for s in timeline if s.is_matchday]
        stage_counts = {}
        for s in timeline:
            stage = s.stage or "unknown"
            stage_counts[stage] = stage_counts.get(stage, 0) + 1

        # Checklist
        oc_builder = OperatorChecklistBuilder(self.paths["execution_rules"])
        path_warnings = []
        path_cfg = json.loads(Path(self.paths["schedule_config"]).read_text(encoding="utf-8-sig")).get("path_sanity", {})
        if winner_prob_sum is not None and winner_prob_sum < path_cfg.get("winner_probability_min_sum", 0.85):
            path_warnings.append(
                f"Path sanity: winner_prob_sum={winner_prob_sum:.4f} below {path_cfg['winner_probability_min_sum']}. "
                f"v1 simplified model. Do not use as calibrated probability distribution."
            )

        checklist = oc_builder.build(today, path_warnings)

        # Upcoming
        upcoming = builder.get_upcoming_schedule(timeline, 7)

        safety = {
            "campaign_analysis_only": True,
            "real_bet_execution": False,
            "auto_betting": False,
            "external_betting_api_allowed": False,
            "simulation_only": True,
            "not_betting_advice": True,
        }

        schedule_dict = {
            "date": today.date, "stage": today.stage, "daily_mode": today.daily_mode,
            "match_count": today.match_count, "remaining_matches": today.remaining_matches,
            "remaining_windows": today.remaining_windows, "is_matchday": today.is_matchday,
            "recommended_modules": today.recommended_modules,
            "bucket_focus": today.bucket_focus,
            "parlay_enabled": today.parlay_enabled,
            "futures_enabled": today.futures_enabled,
            "integrated_strategy_enabled": today.integrated_strategy_enabled,
        }

        return CampaignTimelinePreview(
            generated_at=datetime.now().isoformat(),
            day_count=len(timeline),
            matchday_count=len(matchdays),
            non_matchday_count=len(timeline) - len(matchdays),
            stage_counts=stage_counts,
            upcoming_schedule=[{
                "date": s.date, "stage": s.stage, "daily_mode": s.daily_mode,
                "match_count": s.match_count, "is_matchday": s.is_matchday
            } for s in upcoming],
            today_schedule=schedule_dict,
            operator_checklist=[{
                "phase": i.phase, "action": i.action,
                "module": i.module, "priority": i.priority
            } for i in checklist.items],
            path_sanity_warnings=path_warnings,
            safety=safety,
            warnings=today.warnings,
        )

    def write_json(self, preview: CampaignTimelinePreview, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            json.dumps(asdict(preview), indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")

    def write_markdown(self, preview: CampaignTimelinePreview, path: str) -> None:
        t = preview.today_schedule
        lines = [
            "# Campaign Schedule Preview",
            "",
            f"**Date:** {t.get('date','')} | **Stage:** {t.get('stage','')}",
            f"**Daily Mode:** {t.get('daily_mode','')} | **Matches Today:** {t.get('match_count',0)}",
            f"**Total Days:** {preview.day_count} | **Matchdays:** {preview.matchday_count}",
            "",
            "## Today's Plan",
            f"- **Modules:** {', '.join(t.get('recommended_modules',[]))}",
            f"- **Bucket Focus:** {', '.join(t.get('bucket_focus',[]))}",
            f"- **Parlay:** {t.get('parlay_enabled',False)} | **Futures:** {t.get('futures_enabled',False)}",
            "",
            "## Operator Checklist",
        ]
        for c in preview.operator_checklist[:15]:
            lines.append(f"- [{c['phase']}] [{c['priority']}] {c['action']}")
        lines.append("")
        lines.append("## Path Sanity")
        for w in preview.path_sanity_warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")
        lines.append("## Safety")
        for k, v in preview.safety.items():
            lines.append(f"- **{k}:** {v}")
        lines.append("")
        lines.append("*Analysis schedule only. NOT betting instructions.*")

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(chr(10).join(lines), encoding="utf-8")

    def run_full_timeline(self, bankroll: float = 100.0) -> list[dict]:
        builder = CampaignScheduleBuilder(
            self.paths["schedule_config"], self.paths["stage_map"],
            self.paths.get("match_registry")
        )
        timeline = builder.build_full_timeline()
        return [{
            "date": s.date, "stage": s.stage, "daily_mode": s.daily_mode,
            "match_count": s.match_count, "remaining_matches": s.remaining_matches,
            "remaining_windows": s.remaining_windows, "is_matchday": s.is_matchday,
            "recommended_modules": s.recommended_modules,
            "bucket_focus": s.bucket_focus,
        } for s in timeline]
