"""Daily execution planner: determines what to run and focus on each day."""
import json, sys
from dataclasses import dataclass
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


@dataclass
class DailyExecutionPlan:
    date: str
    daily_mode: str
    stage: str
    match_count: int
    recommended_modules: list
    bucket_focus: list
    parlay_enabled: bool
    futures_enabled: bool
    integrated_strategy_enabled: bool
    operator_checklist: list
    path_sanity_warnings: list
    warnings: list
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


class DailyExecutionPlanner:
    def __init__(self, schedule_config_path: str, execution_rules_path: str,
                 stage_map_path: str, match_registry_path: str):
        self.config = json.loads(Path(schedule_config_path).read_text(encoding="utf-8-sig"))
        self.rules = json.loads(Path(execution_rules_path).read_text(encoding="utf-8-sig"))
        self.stages = json.loads(Path(stage_map_path).read_text(encoding="utf-8-sig"))
        self.match_registry_path = match_registry_path

    def plan_day(self, date_str: str, current_bankroll: float = 100.0,
                 winner_prob_sum: float = None) -> DailyExecutionPlan:
        from worldcup_campaign.campaign_schedule import CampaignScheduleBuilder
        builder = CampaignScheduleBuilder(
            str(Path(self.match_registry_path).parent.parent.parent / "config" / "campaign_schedule_config.json"),
            str(Path(self.match_registry_path).parent.parent.parent / "config" / "worldcup_stage_map.json"),
            self.match_registry_path
        )
        schedule = builder.build_today_schedule(date_str, current_bankroll)

        # Path sanity
        path_warnings = []
        path_cfg = self.config.get("path_sanity", {})
        if winner_prob_sum is not None:
            if winner_prob_sum < path_cfg.get("winner_probability_min_sum", 0.85):
                path_warnings.append(
                    f"Path sanity: winner_prob_sum={winner_prob_sum:.4f} below threshold "
                    f"({path_cfg['winner_probability_min_sum']}). v1 simplified model. "
                    f"Do not use as calibrated probability distribution."
                )

        from worldcup_campaign.operator_checklist import OperatorChecklistBuilder
        oc_builder = OperatorChecklistBuilder(
            str(Path(self.match_registry_path).parent.parent.parent / "config" / "daily_execution_rules.json")
        )
        checklist = oc_builder.build(schedule, path_warnings)

        return DailyExecutionPlan(
            date=date_str,
            daily_mode=schedule.daily_mode,
            stage=schedule.stage,
            match_count=schedule.match_count,
            recommended_modules=schedule.recommended_modules,
            bucket_focus=schedule.bucket_focus,
            parlay_enabled=schedule.parlay_enabled,
            futures_enabled=schedule.futures_enabled,
            integrated_strategy_enabled=schedule.integrated_strategy_enabled,
            operator_checklist=[{
                "phase": i.phase, "action": i.action,
                "module": i.module, "priority": i.priority
            } for i in checklist.items],
            path_sanity_warnings=path_warnings,
            warnings=schedule.warnings,
        )
