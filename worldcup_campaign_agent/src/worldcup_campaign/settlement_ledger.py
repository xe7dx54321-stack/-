"""Simulation settlement ledger: tracks analysis candidates for post-match settlement."""
import json, sys, uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


@dataclass
class LedgerEntry:
    entry_id: str
    date: str
    match_id: str = ""
    match_number: int = 0
    market_type: str = ""
    selection_id: str = ""
    selection_label: str = ""
    bucket: str = ""
    simulated_deployment: float = 0.0
    odds: float = 1.0
    model_probability: float = 0.0
    ev: float = 0.0
    candidate_tier: str = ""
    outcome: str = "unknown"
    settlement_stage: str = ""
    is_settled: bool = False
    settled_at: str = ""
    notes: str = ""
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


@dataclass
class SimulationLedger:
    date: str
    entries: list = field(default_factory=list)
    settled_count: int = 0
    pending_count: int = 0
    hit_count: int = 0
    miss_count: int = 0
    push_count: int = 0
    void_count: int = 0
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


class SettlementLedgerBuilder:
    def __init__(self, settlement_config_path: str):
        self.config = json.loads(Path(settlement_config_path).read_text(encoding="utf-8-sig"))
        self.forbidden = self.config.get("ledger_fields", {}).get("forbidden", [])

    def build_from_integrated_strategy(self, integrated_strategy, date: str) -> SimulationLedger:
        entries = []
        pools = integrated_strategy.integrated_candidate_pools.get("pools", [])

        for pool in pools:
            bucket = pool.get("bucket", "unknown")
            budget = pool.get("bucket_strategy_budget", 0)
            candidates = pool.get("candidates", [])

            for c in candidates:
                entry = LedgerEntry(
                    entry_id=f"LEDGER_{uuid.uuid4().hex[:10]}",
                    date=date,
                    match_id=c.get("match_id", ""),
                    match_number=c.get("match_number", 0),
                    market_type=c.get("market_type", ""),
                    selection_id=c.get("selection_id", c.get("candidate_id", "")),
                    selection_label=c.get("selection_label", c.get("selection", "")),
                    bucket=bucket,
                    simulated_deployment=round(budget / max(1, len(candidates)), 2),
                    odds=c.get("mock_odds", c.get("decimal_odds", 1.0)),
                    model_probability=c.get("model_probability", 0.0),
                    ev=c.get("ev", 0.0),
                    candidate_tier=c.get("candidate_tier", ""),
                    outcome="unknown",
                    settlement_stage=c.get("stage", ""),
                )
                entries.append(entry)

        return SimulationLedger(date=date, entries=entries)

    def build_empty_ledger(self, date: str) -> SimulationLedger:
        return SimulationLedger(date=date)

    def validate_ledger(self, ledger: SimulationLedger) -> list[str]:
        warnings = []
        for e in ledger.entries:
            d = e.__dict__
            for f in self.forbidden:
                if f in d:
                    warnings.append(f"Ledger entry {e.entry_id} contains forbidden field: {f}")
        return warnings
