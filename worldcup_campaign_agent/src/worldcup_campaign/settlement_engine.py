"""Settlement engine: processes manual results against ledger entries."""
import json, sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


@dataclass
class SettlementResult:
    date: str
    ledger_entries: list = field(default_factory=list)
    settled_entries: list = field(default_factory=list)
    pending_entries: list = field(default_factory=list)
    hit_count: int = 0
    miss_count: int = 0
    push_count: int = 0
    pending_count: int = 0
    void_count: int = 0
    simulated_bankroll_before: float = 100.0
    simulated_bankroll_after: float = 100.0
    bankroll_state_before: str = ""
    bankroll_state_after: str = ""
    required_multiplier_after: float = 10000.0
    next_day_routing_hint: str = ""
    warnings: list = field(default_factory=list)
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


class SettlementEngine:
    def __init__(self, settlement_config_path: str, settlement_rules_path: str):
        self.config = json.loads(Path(settlement_config_path).read_text(encoding="utf-8-sig"))
        self.rules = json.loads(Path(settlement_rules_path).read_text(encoding="utf-8-sig"))

    def settle(self, ledger, manual_results: list, current_bankroll: float,
               current_state: str, target_bankroll: float = 1_000_000.0) -> SettlementResult:
        # Build result lookup
        result_map = {}
        for r in manual_results:
            mid = r.get("match_id", "")
            if mid:
                result_map[mid] = r

        settled = []
        pending = []
        hit = miss = push = void = 0
        total_return = 0.0
        total_deployed = 0.0

        for entry in ledger.entries:
            total_deployed += entry.simulated_deployment
            match_result = result_map.get(entry.match_id)

            if not match_result:
                entry.outcome = "unknown"
                entry.is_settled = False
                pending.append(entry)
                continue

            # Check if futures/pending
            if entry.market_type in ("winner", "runner_up", "exact_final_pair", "golden_boot",
                                      "group_qualification", "group_winner",
                                      "reach_round_of_32", "reach_round_of_16",
                                      "reach_quarter_final", "reach_semi_final", "reach_final"):
                entry.outcome = "pending"
                entry.is_settled = False
                pending.append(entry)
                continue

            # Determine outcome from match result
            outcome = self._determine_outcome(entry, match_result)
            entry.outcome = outcome
            entry.is_settled = True
            entry.settled_at = datetime.now().isoformat()

            if outcome == "hit":
                hit += 1
                total_return += entry.simulated_deployment * entry.odds
            elif outcome == "miss":
                miss += 1
            elif outcome == "push":
                push += 1
                total_return += entry.simulated_deployment
            elif outcome == "void":
                void += 1
                total_return += entry.simulated_deployment
            else:
                pending.append(entry)
                continue

            settled.append(entry)

        # Calculate new bankroll
        reserve_amount = current_bankroll * 0.5
        deployed = min(current_bankroll * 0.5, total_deployed)
        new_bankroll = reserve_amount + total_return + max(0, current_bankroll * 0.5 - deployed)

        # Classify state
        from worldcup_campaign.bankroll_state import load_bankroll_states, classify_bankroll_state
        states = load_bankroll_states(
            str(Path(self.config.get("_dummy","")).parent.parent / "config" / "bankroll_states.json")
            if hasattr(self, '_states_path') else
            Path(__file__).resolve().parent.parent.parent / "config" / "bankroll_states.json"
        )
        # Use hardcoded path resolution
        import os
        config_dir = str(Path(__file__).resolve().parent.parent.parent / "config")
        states = load_bankroll_states(os.path.join(config_dir, "bankroll_states.json"))
        state_result = classify_bankroll_state(new_bankroll, states, target_bankroll)
        new_state = state_result.state if hasattr(state_result, 'state') else state_result.get("state", "S2")

        # Required multiplier
        new_mult = target_bankroll / new_bankroll if new_bankroll > 0 else 1_000_000

        # Routing hint
        routing = self._generate_routing_hint(hit, miss, pending, new_state, new_mult)

        return SettlementResult(
            date=ledger.date,
            ledger_entries=[e.__dict__ for e in ledger.entries],
            settled_entries=[e.__dict__ for e in settled],
            pending_entries=[e.__dict__ for e in pending],
            hit_count=hit, miss_count=miss, push_count=push,
            pending_count=len(pending), void_count=void,
            simulated_bankroll_before=current_bankroll,
            simulated_bankroll_after=round(new_bankroll, 2),
            bankroll_state_before=current_state,
            bankroll_state_after=new_state,
            required_multiplier_after=round(new_mult, 2),
            next_day_routing_hint=routing,
        )

    def _determine_outcome(self, entry, match_result) -> str:
        mt = entry.market_type
        result_1x2 = match_result.get("result_1x2", "")
        total_goals = match_result.get("total_goals")
        sel = entry.selection_label.lower() + entry.selection_id.lower()

        if mt == "1x2":
            if result_1x2 == entry.selection_id.lower():
                return "hit"
            return "miss"

        if mt == "double_chance":
            if result_1x2 and result_1x2 in entry.selection_id.lower():
                return "hit"
            return "miss"

        if mt == "over_under":
            if total_goals is not None:
                # Parse threshold from selection
                threshold = 2.5  # default
                import re
                nums = re.findall(r'[\d.]+', entry.selection_label)
                if nums:
                    threshold = float(nums[0])
                over_under = "over" if total_goals > threshold else "under"
                if over_under in entry.selection_label.lower():
                    return "hit"
                return "miss"
            return "unknown"

        if mt == "correct_score":
            home = match_result.get("actual_home_score")
            away = match_result.get("actual_away_score")
            if home is not None and away is not None:
                expected = f"{home}-{away}"
                if expected in sel or f"{home}{away}" in sel.replace("-","").replace(":",""):
                    return "hit"
                return "miss"
            return "unknown"

        if mt == "asian_handicap":
            # Simplified: check 1X2 direction
            home_score = match_result.get("actual_home_score", 0)
            away_score = match_result.get("actual_away_score", 0)
            diff = home_score - away_score
            if "home" in sel and diff > 0:
                return "hit"
            if "away" in sel and diff < 0:
                return "hit"
            return "miss"

        # Default
        return "unknown"

    def _generate_routing_hint(self, hit: int, miss: int, pending: list,
                               state: str, multiplier: float) -> str:
        if pending:
            return f"pending_futures:{len(pending)}|state:{state}|mult:{multiplier:.0f}x"
        if hit > miss:
            return f"positive_day|state:{state}|mult:{multiplier:.0f}x"
        if miss > hit:
            return f"negative_day|state:{state}|stay_disciplined|mult:{multiplier:.0f}x"
        return f"neutral|state:{state}|mult:{multiplier:.0f}x"


    def load_manual_results(self, path: str) -> tuple[list, list[str]]:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        results = data.get("results", [])
        warnings = []

        # Validate no forbidden fields
        forbidden = ["bookmaker", "bookmaker_account", "real_money_balance",
                    "stake", "bet_instruction"]
        for r in results:
            for f in forbidden:
                if f in r:
                    warnings.append(f"Manual result contains forbidden field: {f}")

        return results, warnings
