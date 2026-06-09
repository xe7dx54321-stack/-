"""Post-match settlement runner: ties ledger, engine, and state tracker together."""
import json, sys, os
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from worldcup_campaign.settlement_ledger import SettlementLedgerBuilder
from worldcup_campaign.settlement_engine import SettlementEngine
from worldcup_campaign.campaign_state_tracker import CampaignStateTracker


@dataclass
class PostmatchSettlementPreview:
    campaign_name: str = "worldcup_2026_high_odds_campaign"
    date: str = ""
    ledger_entries_count: int = 0
    settled_entries_count: int = 0
    pending_entries_count: int = 0
    hit_count: int = 0
    miss_count: int = 0
    push_count: int = 0
    void_count: int = 0
    simulated_bankroll_before: float = 100.0
    simulated_bankroll_after: float = 100.0
    bankroll_state_before: str = ""
    bankroll_state_after: str = ""
    required_multiplier_before: float = 10000.0
    required_multiplier_after: float = 10000.0
    next_day_routing_hint: str = ""
    campaign_snapshot: dict = field(default_factory=dict)
    open_positions_count: int = 0
    pending_positions_count: int = 0
    settlement_result: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    safety: dict = field(default_factory=dict)
    generated_at: str = ""
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


class PostmatchSettlementRunner:
    def __init__(self, config_paths: dict):
        self.paths = config_paths

    def run(self, date: str, bankroll: float = 100.0,
            manual_results_path: str = None,
            target_bankroll: float = 1_000_000.0) -> PostmatchSettlementPreview:
        # 1. Build ledger from integrated strategy
        from worldcup_campaign.integrated_daily_strategy import IntegratedStrategyBuilder
        r6_builder = IntegratedStrategyBuilder(self.paths)
        integrated = r6_builder.build(date, bankroll)

        ledger_builder = SettlementLedgerBuilder(self.paths["settlement_config"])
        ledger = ledger_builder.build_from_integrated_strategy(integrated, date)

        # 2. Load manual results
        engine = SettlementEngine(self.paths["settlement_config"], self.paths["settlement_rules"])
        manual_results = []
        manual_warnings = []
        if manual_results_path and Path(manual_results_path).exists():
            manual_results, manual_warnings = engine.load_manual_results(manual_results_path)

        # 3. Classify current state
        from worldcup_campaign.bankroll_state import load_bankroll_states, classify_bankroll_state
        config_dir = str(Path(__file__).resolve().parent.parent.parent / "config")
        states = load_bankroll_states(os.path.join(config_dir, "bankroll_states.json"))
        state_result = classify_bankroll_state(bankroll, states, target_bankroll)
        current_state = state_result.state if hasattr(state_result, 'state') else state_result.get("state", "S2")
        current_mult = target_bankroll / bankroll if bankroll > 0 else 1_000_000

        # 4. Settle
        result = engine.settle(ledger, manual_results, bankroll, current_state, target_bankroll)
        result.warnings = manual_warnings + ledger_builder.validate_ledger(ledger)

        # 5. Track state
        tracker = CampaignStateTracker()
        history_path = self.paths.get("campaign_history",
            str(Path(__file__).resolve().parent.parent.parent / "reports" / "generated" / "campaign_state_history.json"))
        if Path(history_path).exists():
            tracker.load_history(history_path)
        snapshot = tracker.record_snapshot(result, target_bankroll)
        tracker.save_history(history_path)

        # 6. Safety
        safety = {
            "campaign_analysis_only": True, "real_bet_execution": False,
            "auto_betting": False, "external_betting_api_allowed": False,
            "simulation_only": True, "not_betting_advice": True,
            "no_real_money": True,
        }

        return PostmatchSettlementPreview(
            date=date,
            ledger_entries_count=len(ledger.entries),
            settled_entries_count=len(result.settled_entries),
            pending_entries_count=len(result.pending_entries),
            hit_count=result.hit_count, miss_count=result.miss_count,
            push_count=result.push_count, void_count=result.void_count,
            simulated_bankroll_before=bankroll,
            simulated_bankroll_after=result.simulated_bankroll_after,
            bankroll_state_before=current_state,
            bankroll_state_after=result.bankroll_state_after,
            required_multiplier_before=round(current_mult, 2),
            required_multiplier_after=result.required_multiplier_after,
            next_day_routing_hint=result.next_day_routing_hint,
            campaign_snapshot=asdict(snapshot),
            open_positions_count=snapshot.open_positions,
            pending_positions_count=snapshot.pending_count,
            settlement_result=asdict(result),
            warnings=result.warnings,
            safety=safety,
            generated_at=datetime.now().isoformat(),
        )

    def write_json(self, preview: PostmatchSettlementPreview, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            json.dumps(asdict(preview), indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")

    def write_markdown(self, preview: PostmatchSettlementPreview, path: str) -> None:
        lines = [
            "# Post-Match Settlement Preview",
            "",
            f"**Date:** {preview.date}",
            f"**Bankroll:** {preview.simulated_bankroll_before} -> {preview.simulated_bankroll_after}",
            f"**State:** {preview.bankroll_state_before} -> {preview.bankroll_state_after}",
            f"**Multiplier:** {preview.required_multiplier_before}x -> {preview.required_multiplier_after}x",
            "",
            "## Settlement Summary",
            f"| Hit | Miss | Push | Pending | Void |",
            f"|-----|------|------|---------|------|",
            f"| {preview.hit_count} | {preview.miss_count} | {preview.push_count} | {preview.pending_entries_count} | {preview.void_count} |",
            "",
            f"**Ledger entries:** {preview.ledger_entries_count}",
            f"**Settled:** {preview.settled_entries_count} | **Pending:** {preview.pending_entries_count}",
            "",
            "## Routing Hint",
            f"> {preview.next_day_routing_hint}",
            "",
            "## Campaign Snapshot",
            f"- Open positions: {preview.open_positions_count}",
            f"- Pending positions: {preview.pending_positions_count}",
            "",
            "## Safety",
        ]
        for k, v in preview.safety.items():
            lines.append(f"- **{k}:** {v}")
        lines.append("")
        lines.append("*Simulation settlement only. NOT real money. NOT betting advice.*")

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(chr(10).join(lines), encoding="utf-8")
