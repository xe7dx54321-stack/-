"""Campaign state tracker: maintains history of simulated bankroll and state transitions."""
import json, sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


@dataclass
class CampaignStateSnapshot:
    date: str
    simulated_bankroll: float
    bankroll_state: str
    required_multiplier: float
    target_bankroll: float = 1_000_000.0
    hit_count: int = 0
    miss_count: int = 0
    pending_count: int = 0
    open_positions: int = 0
    next_day_routing_hint: str = ""
    notes: str = ""
    generated_at: str = ""
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


class CampaignStateTracker:
    def __init__(self, history_path: str = None):
        self.history_path = history_path
        self.history: list[CampaignStateSnapshot] = []

    def load_history(self, path: str):
        if Path(path).exists():
            raw = Path(path).read_bytes()
            text = raw.decode("utf-8-sig")
            data = None
            try:
                data = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                depth = 0
                end = 0
                for i, ch in enumerate(text):
                    if ch == '{': depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                if end > 0:
                    try:
                        data = json.loads(text[:end])
                    except (json.JSONDecodeError, ValueError):
                        data = None
            if data and isinstance(data, dict):
                self.history = [CampaignStateSnapshot(**s) for s in data.get("snapshots", [])]

    def record_snapshot(self, settlement_result, target_bankroll: float = 1_000_000.0) -> CampaignStateSnapshot:
        snapshot = CampaignStateSnapshot(
            date=settlement_result.date,
            simulated_bankroll=settlement_result.simulated_bankroll_after,
            bankroll_state=settlement_result.bankroll_state_after,
            required_multiplier=settlement_result.required_multiplier_after,
            target_bankroll=target_bankroll,
            hit_count=settlement_result.hit_count,
            miss_count=settlement_result.miss_count,
            pending_count=settlement_result.pending_count,
            open_positions=settlement_result.hit_count + settlement_result.pending_count,
            next_day_routing_hint=settlement_result.next_day_routing_hint,
            generated_at=datetime.now().isoformat(),
        )
        self.history.append(snapshot)
        return snapshot

    def save_history(self, path: str):
        data = {
            "snapshots": [asdict(s) for s in self.history],
            "total_snapshots": len(self.history),
            "analysis_only": True,
            "simulation_only": True,
            "not_betting_advice": True,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    def get_current_positions(self) -> dict:
        return {
            "open_positions": sum(s.hit_count for s in self.history) if self.history else 0,
            "pending_positions": sum(s.pending_count for s in self.history) if self.history else 0,
            "total_snapshots": len(self.history),
        }
