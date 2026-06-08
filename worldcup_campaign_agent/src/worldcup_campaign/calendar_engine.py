"""Calendar engine: core orchestration that combines stage map, match registry, and campaign policy."""

from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import Optional

from worldcup_campaign.policy import CampaignPolicy, load_campaign_policy
from worldcup_campaign.stage_mapper import (
    StageDefinition,
    load_stage_map,
    classify_date,
    get_stages_summary,
)
from worldcup_campaign.match_registry import (
    MatchEntry,
    load_match_registry,
    get_matches_by_date,
    get_remaining_matches,
    get_match_count_by_stage,
    get_upcoming_matches,
)
from worldcup_campaign.opportunity_window import (
    count_effective_windows,
    count_remaining_matches,
)


@dataclass
class TodayMatch:
    match_id: str
    match_number: int
    stage: str
    group: Optional[str]
    home_team: str
    away_team: str
    is_knockout: bool
    kickoff_slot: Optional[str]
    venue: str


@dataclass
class CalendarState:
    current_date: str
    current_stage: str
    stage_display_name: str
    strategy_focus: str
    matches_today_count: int
    matches_remaining_count: int
    effective_windows_left: int
    stage_summary: dict
    today_matches: list[dict]
    upcoming_matches: list[dict]
    warnings: list[str] = field(default_factory=list)
    safety: dict = field(default_factory=dict)


class CalendarEngine:
    """Combines stage map, match registry, and campaign policy to produce a calendar state."""

    def __init__(
        self,
        policy_path: str,
        stage_map_path: str,
        match_registry_path: str,
    ):
        self.policy = load_campaign_policy(policy_path)
        self.stages = load_stage_map(stage_map_path)
        self.matches = load_match_registry(match_registry_path)

    def get_state(self, target_date: date) -> CalendarState:
        """Get full calendar state for a given date."""
        # Classify the date
        stage_def = classify_date(target_date, self.stages)

        # Get today's matches
        today_matches = get_matches_by_date(target_date, self.matches)

        # Get remaining matches
        remaining = get_remaining_matches(target_date, self.matches)

        # Count effective windows (unique dates with matches remaining)
        windows = count_effective_windows(target_date, self.matches)

        # Stage summary
        stage_summary = get_stages_summary(self.stages)

        # Warnings
        warnings = []
        if len(today_matches) == 0 and stage_def.stage != "pre_tournament" and stage_def.stage != "post_tournament":
            warnings.append(f"No matches scheduled for {target_date} in stage '{stage_def.stage}'")
        if len(today_matches) == 0:
            windows = max(0, windows)

        # Safety flags
        safety = {
            "campaign_analysis_only": self.policy.campaign_analysis_only,
            "real_bet_execution": self.policy.real_bet_execution,
            "auto_betting": self.policy.auto_betting,
            "external_betting_api_allowed": self.policy.external_betting_api_allowed,
            "real_money_instruction_allowed": self.policy.real_money_instruction_allowed,
        }

        # Format today's matches
        today_formatted = []
        for m in today_matches:
            today_formatted.append({
                "match_id": m.match_id,
                "match_number": m.match_number,
                "stage": m.stage,
                "group": m.group,
                "home_team": m.home_team,
                "away_team": m.away_team,
                "is_knockout": m.is_knockout,
                "kickoff_slot": m.kickoff_slot,
                "venue": m.venue,
            })

        # Upcoming (next 10)
        upcoming_raw = get_upcoming_matches(target_date, self.matches, limit=10)
        upcoming_formatted = []
        for m in upcoming_raw:
            upcoming_formatted.append({
                "match_id": m.match_id,
                "match_number": m.match_number,
                "date": m.date.isoformat(),
                "stage": m.stage,
                "group": m.group,
                "home_team": m.home_team,
                "away_team": m.away_team,
                "is_knockout": m.is_knockout,
                "kickoff_slot": m.kickoff_slot,
            })

        return CalendarState(
            current_date=target_date.isoformat(),
            current_stage=stage_def.stage,
            stage_display_name=stage_def.display_name,
            strategy_focus=stage_def.strategy_focus,
            matches_today_count=len(today_matches),
            matches_remaining_count=len(remaining),
            effective_windows_left=windows,
            stage_summary=stage_summary,
            today_matches=today_formatted,
            upcoming_matches=upcoming_formatted,
            warnings=warnings,
            safety=safety,
        )