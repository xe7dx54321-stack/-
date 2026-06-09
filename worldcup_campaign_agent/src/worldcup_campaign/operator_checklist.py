"""Operator checklist: generates daily actionable items for campaign analysis."""
import json, sys
from dataclasses import dataclass, field
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


@dataclass
class ChecklistItem:
    phase: str  # pre_run, during_run, post_run
    action: str
    module: str = ""
    priority: str = "normal"  # high, normal, low
    detail: str = ""


@dataclass
class OperatorChecklist:
    date: str
    items: list[ChecklistItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    not_betting_advice: bool = True
    analysis_only: bool = True
    simulation_only: bool = True


class OperatorChecklistBuilder:
    def __init__(self, rules_path: str):
        self.rules = json.loads(Path(rules_path).read_text(encoding="utf-8-sig"))

    def build(self, daily_schedule, path_sanity_warnings: list = None) -> OperatorChecklist:
        checklist = OperatorChecklist(date=daily_schedule.date)
        template = self.rules.get("checklist_template", {})

        # Pre-run
        for action in template.get("pre_run", []):
            checklist.items.append(ChecklistItem(
                phase="pre_run", action=action, priority="high" if "safety" in action else "normal"
            ))

        # During run - based on recommended modules
        for mod in daily_schedule.recommended_modules:
            checklist.items.append(ChecklistItem(
                phase="during_run", action=f"run_{mod}", module=mod,
                priority="high" if mod == "foundation" else "normal",
                detail=f"Execute {mod} analysis module"
            ))

        # Post-run
        for action in template.get("post_run", []):
            checklist.items.append(ChecklistItem(
                phase="post_run", action=action, priority="normal"
            ))

        # Add warnings
        checklist.warnings = daily_schedule.warnings.copy()
        if path_sanity_warnings:
            checklist.warnings.extend(path_sanity_warnings)

        return checklist

    def get_forbidden_actions(self) -> list[str]:
        return self.rules.get("forbidden_actions", [])

    def get_allowed_actions(self) -> list[str]:
        return self.rules.get("allowed_actions", [])
