"""Dashboard loader: reads generated report JSONs for dashboard assembly."""
import json, sys
from dataclasses import dataclass, field
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


@dataclass
class DashboardSources:
    foundation: dict = field(default_factory=dict)
    campaign_state: dict = field(default_factory=dict)
    postmatch_settlement: dict = field(default_factory=dict)
    campaign_schedule: dict = field(default_factory=dict)
    calendar_preview: dict = field(default_factory=dict)
    integrated_strategy: dict = field(default_factory=dict)
    ev_ranking: dict = field(default_factory=dict)
    parlay_preview: dict = field(default_factory=dict)
    futures_preview: dict = field(default_factory=dict)
    match_probability: dict = field(default_factory=dict)
    source_status: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


class DashboardLoader:
    def __init__(self, forbidden_fields: list = None):
        self.forbidden = forbidden_fields or []

    def load_all(self, reports_dir: str) -> DashboardSources:
        sources = DashboardSources()
        p = Path(reports_dir)
        mapping = {
            "foundation": "foundation_preview.json",
            "postmatch_settlement": "postmatch_settlement.json",
            "campaign_schedule": "campaign_schedule_preview.json",
            "calendar_preview": "calendar_preview.json",
            "integrated_strategy": "integrated_daily_strategy.json",
            "ev_ranking": "ev_ranking_preview.json",
            "parlay_preview": "parlay_preview.json",
            "futures_preview": "futures_preview.json",
            "match_probability": "match_probability_preview.json",
        }
        status = {}
        for key, fname in mapping.items():
            fpath = p / fname
            if fpath.exists():
                try:
                    data = json.loads(fpath.read_text(encoding="utf-8"))
                    setattr(sources, key, data)
                    status[key] = "loaded"
                except Exception as e:
                    status[key] = f"error:{e}"
                    sources.warnings.append(f"Failed to load {fname}: {e}")
            else:
                status[key] = "missing"
                sources.warnings.append(f"Source not found: {fname}")

        # Load campaign state history
        history_path = p / "campaign_state_history.json"
        if history_path.exists():
            try:
                sources.campaign_state = json.loads(history_path.read_text(encoding="utf-8"))
                status["campaign_state"] = "loaded"
            except Exception:
                status["campaign_state"] = "missing"

        sources.source_status = status
        return sources

    def validate_forbidden(self, data: dict) -> list[str]:
        warnings = []
        for key in self.forbidden:
            if key in str(data).lower():
                if key in json.dumps(data):
                    warnings.append(f"Forbidden field found: {key}")
        return warnings
