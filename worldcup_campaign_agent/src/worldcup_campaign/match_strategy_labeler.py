"""Match strategy labeler: assign strategy labels to matches based on stage context."""

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from worldcup_campaign.match_registry import MatchEntry


@dataclass
class MatchLabel:
    match_id: str
    match_number: int
    home_team: str
    away_team: str
    stage: str
    group: Optional[str]
    is_knockout: bool
    labels: list[str] = field(default_factory=list)
    eligible_buckets: list[str] = field(default_factory=list)
    risk_level: str = "skip"
    is_today: bool = False


class MatchStrategyLabeler:
    """Assigns strategy labels to matches based on rules and stage context."""

    def __init__(self, rules_path: str):
        self.rules = json.loads(Path(rules_path).read_text(encoding="utf-8-sig"))
        self._label_map = {}
        for label in self.rules["labels"]:
            self._label_map[label["label"]] = label

    def label_matches(
        self, matches: list[MatchEntry], today: date
    ) -> list[MatchLabel]:
        """Label all given matches with strategy tags."""
        results = []
        stage_mapping = self.rules.get("stage_label_mapping", {})

        for m in matches:
            # Get labels for this stage
            stage_labels = stage_mapping.get(m.stage, [])
            
            # Determine which labels actually apply to this match
            applicable = []
            eligible_buckets = set()
            risk_level = "skip"

            for label_name in stage_labels:
                label_def = self._label_map.get(label_name)
                if label_def is None:
                    continue
                applicable.append(label_name)
                for b in label_def.get("suitable_buckets", []):
                    eligible_buckets.add(b)
                if label_def.get("risk_level", "skip") != "skip":
                    risk_level = label_def["risk_level"]

            # If no labels matched, mark as skip
            if not applicable:
                applicable = ["skip"]
                risk_level = "skip"

            results.append(MatchLabel(
                match_id=m.match_id,
                match_number=m.match_number,
                home_team=m.home_team,
                away_team=m.away_team,
                stage=m.stage,
                group=m.group,
                is_knockout=m.is_knockout,
                labels=applicable,
                eligible_buckets=sorted(eligible_buckets),
                risk_level=risk_level,
                is_today=(m.date == today),
            ))

        return results

    def get_label_definition(self, label_name: str) -> Optional[dict]:
        """Get the definition for a specific label."""
        return self._label_map.get(label_name)