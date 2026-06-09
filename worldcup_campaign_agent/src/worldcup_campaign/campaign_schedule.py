"""Campaign schedule: generates daily timeline from pre-tournament to post."""
import json, sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


@dataclass
class DailySchedule:
    date: str
    stage: str
    stage_display: str
    daily_mode: str
    match_count: int
    remaining_matches: int
    remaining_windows: int
    recommended_modules: list[str] = field(default_factory=list)
    bucket_focus: list[str] = field(default_factory=list)
    parlay_enabled: bool = False
    futures_enabled: bool = False
    integrated_strategy_enabled: bool = False
    is_matchday: bool = False
    warnings: list[str] = field(default_factory=list)
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


class CampaignScheduleBuilder:
    def __init__(self, schedule_config_path: str, stage_map_path: str,
                 match_registry_path: str = None):
        self.config = json.loads(Path(schedule_config_path).read_text(encoding="utf-8-sig"))
        self.stages = json.loads(Path(stage_map_path).read_text(encoding="utf-8-sig"))
        self.match_registry_path = match_registry_path
        self._match_counts = None

    def _get_match_counts_by_date(self) -> dict[str, int]:
        if self._match_counts is not None:
            return self._match_counts
        if not self.match_registry_path:
            return {}
        from worldcup_campaign.match_registry import load_match_registry
        matches = load_match_registry(self.match_registry_path)
        counts = {}
        for m in matches:
            d = str(m.date) if hasattr(m, 'date') else m.get('date', '')
            if d:
                counts[d] = counts.get(d, 0) + 1
        self._match_counts = counts
        return counts

    def build_full_timeline(self) -> list[DailySchedule]:
        start = date.fromisoformat(self.config["tournament_dates"]["start"])
        end = date.fromisoformat(self.config["tournament_dates"]["end"])
        match_counts = self._get_match_counts_by_date()

        timeline = []
        current = start
        while current <= end:
            dstr = current.isoformat()
            stage_info = self._get_stage_for_date(dstr)
            mc = match_counts.get(dstr, 0)
            daily_mode = self._determine_mode(mc, stage_info)
            remaining = self._count_remaining(current, match_counts)
            windows = self._count_windows(current, match_counts)

            schedule = DailySchedule(
                date=dstr,
                stage=stage_info.get("stage", ""),
                stage_display=stage_info.get("display_name", ""),
                daily_mode=daily_mode,
                match_count=mc,
                remaining_matches=remaining,
                remaining_windows=windows,
                is_matchday=(mc > 0),
            )
            # Enrich with module/bucket decisions
            self._enrich_schedule(schedule, stage_info)
            timeline.append(schedule)
            current += timedelta(days=1)

        return timeline

    def build_today_schedule(self, date_str: str, current_bankroll: float = 100.0) -> DailySchedule:
        match_counts = self._get_match_counts_by_date()
        stage_info = self._get_stage_for_date(date_str)
        mc = match_counts.get(date_str, 0)
        daily_mode = self._determine_mode(mc, stage_info)
        remaining = self._count_remaining(date.fromisoformat(date_str), match_counts)
        windows = self._count_windows(date.fromisoformat(date_str), match_counts)

        schedule = DailySchedule(
            date=date_str,
            stage=stage_info.get("stage", ""),
            stage_display=stage_info.get("display_name", ""),
            daily_mode=daily_mode,
            match_count=mc,
            remaining_matches=remaining,
            remaining_windows=windows,
            is_matchday=(mc > 0),
        )
        self._enrich_schedule(schedule, stage_info)
        return schedule

    def _get_stage_for_date(self, date_str: str) -> dict:
        for s in self.stages:
            if s.get("start_date", "") <= date_str <= s.get("end_date", ""):
                return s
        return {"stage": "unknown", "display_name": "Unknown"}

    def _determine_mode(self, match_count: int, stage_info: dict) -> str:
        stage = stage_info.get("stage", "")
        if stage == "post_tournament":
            return "post_tournament"
        if stage == "pre_tournament":
            return "pre_matchday"
        if match_count > 0:
            return "matchday"
        # Check if there are upcoming matches soon
        return "rest_day"

    def _count_remaining(self, current: date, match_counts: dict) -> int:
        return sum(c for d, c in match_counts.items() if d >= current.isoformat())

    def _count_windows(self, current: date, match_counts: dict) -> int:
        days_with_matches = set(d for d, c in match_counts.items() if c > 0 and d >= current.isoformat())
        return len(days_with_matches)

    def _enrich_schedule(self, schedule: DailySchedule, stage_info: dict):
        stage = schedule.stage
        modes = self.config.get("daily_modes", {})
        mode_info = modes.get(schedule.daily_mode, {})

        schedule.recommended_modules = mode_info.get("run_modules", [])
        schedule.parlay_enabled = mode_info.get("parlay_enabled", False)
        schedule.integrated_strategy_enabled = mode_info.get("integrated_strategy_enabled", False)

        # Futures enabled based on stage frequency
        freq = self.config.get("futures_refresh_frequency", {}).get(stage, "never")
        schedule.futures_enabled = freq != "never"

        # Bucket focus
        schedule.bucket_focus = self.config.get("bucket_focus_by_stage", {}).get(stage, [])

        # Path sanity warning
        path_sanity = self.config.get("path_sanity", {})
        if path_sanity.get("warn_below_sum", False):
            schedule.warnings.append(path_sanity.get("warn_message", "Path sanity warning"))

        # Parlay minimum check
        if schedule.parlay_enabled and schedule.match_count < self.config.get("parlay_min_candidates", 6):
            schedule.parlay_enabled = False
            if "parlay_preview" in schedule.recommended_modules:
                schedule.recommended_modules.remove("parlay_preview")

    def get_upcoming_schedule(self, timeline: list[DailySchedule], days: int = 7) -> list[DailySchedule]:
        return [s for s in timeline if s.date >= date.today().isoformat()][:days]
