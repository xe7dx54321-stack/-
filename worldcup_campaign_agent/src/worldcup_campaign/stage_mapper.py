"""Stage mapper: classify dates into tournament stages."""

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional


@dataclass
class StageDefinition:
    stage: str
    display_name: str
    start_date: date
    end_date: date
    stage_order: int
    match_count_expected: int
    strategy_focus: str
    description: str


def load_stage_map(path: str) -> list[StageDefinition]:
    """Load stage map from JSON config."""
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    stages = []
    stage_names = set()
    stage_orders = set()
    for entry in raw:
        s = StageDefinition(
            stage=entry["stage"],
            display_name=entry["display_name"],
            start_date=date.fromisoformat(entry["start_date"]),
            end_date=date.fromisoformat(entry["end_date"]),
            stage_order=int(entry["stage_order"]),
            match_count_expected=int(entry["match_count_expected"]),
            strategy_focus=entry.get("strategy_focus", ""),
            description=entry.get("description", ""),
        )
        stages.append(s)
        stage_names.add(s.stage)
        stage_orders.add(s.stage_order)
    validate_stage_map(stages)
    return stages


def validate_stage_map(stages: list[StageDefinition]) -> None:
    """Validate stage map integrity."""
    # Unique stage names
    seen = set()
    for s in stages:
        if s.stage in seen:
            raise ValueError(f"Duplicate stage: {s.stage}")
        seen.add(s.stage)
    # Unique stage orders
    orders = set()
    for s in stages:
        if s.stage_order in orders:
            raise ValueError(f"Duplicate stage_order: {s.stage_order}")
        orders.add(s.stage_order)
    # Non-overlapping date ranges
    sorted_stages = sorted(stages, key=lambda x: x.start_date)
    for i in range(len(sorted_stages) - 1):
        if sorted_stages[i].end_date >= sorted_stages[i + 1].start_date:
            # Allow consecutive stages (pre->group, group_r3->r32, etc.)
            # Only error if truly overlapping
            if sorted_stages[i].end_date > sorted_stages[i + 1].start_date:
                raise ValueError(
                    f"Overlapping stages: {sorted_stages[i].stage} ends "
                    f"{sorted_stages[i].end_date} but {sorted_stages[i+1].stage} "
                    f"starts {sorted_stages[i+1].start_date}"
                )
    # Total expected matches should be 104
    total = sum(s.match_count_expected for s in stages)
    if total != 104:
        raise ValueError(
            f"Total expected matches across all stages is {total}, must be 104"
        )


def classify_date(
    target_date: date, stages: list[StageDefinition]
) -> StageDefinition:
    """Find which stage a given date falls into."""
    for s in sorted(stages, key=lambda x: x.start_date):
        if s.start_date <= target_date <= s.end_date:
            return s
    raise ValueError(
        f"Date {target_date} does not fall within any defined stage "
        f"(range: {stages[0].start_date} to {stages[-1].end_date})"
    )


def get_stages_summary(stages: list[StageDefinition]) -> dict:
    """Get a summary of all stages and their match counts."""
    return {
        "total_stages": len(stages),
        "total_matches_expected": sum(s.match_count_expected for s in stages),
        "stages": [
            {
                "stage": s.stage,
                "display_name": s.display_name,
                "dates": f"{s.start_date} to {s.end_date}",
                "matches": s.match_count_expected,
                "strategy_focus": s.strategy_focus,
            }
            for s in sorted(stages, key=lambda x: x.stage_order)
        ],
    }