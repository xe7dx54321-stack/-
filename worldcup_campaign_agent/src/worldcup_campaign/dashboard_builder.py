"""Dashboard builder: assembles campaign dashboard from loaded sources."""
import json, sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


@dataclass
class CampaignDashboard:
    campaign_name: str = "worldcup_2026_high_odds_campaign"
    current_date: str = ""
    dashboard_mode: str = "current_day"
    campaign_state: dict = field(default_factory=dict)
    bankroll_summary: dict = field(default_factory=dict)
    calendar_summary: dict = field(default_factory=dict)
    execution_schedule_summary: dict = field(default_factory=dict)
    bucket_summary: dict = field(default_factory=dict)
    candidate_summary: dict = field(default_factory=dict)
    parlay_summary: dict = field(default_factory=dict)
    futures_summary: dict = field(default_factory=dict)
    settlement_summary: dict = field(default_factory=dict)
    warnings_summary: list = field(default_factory=list)
    next_day_routing: str = ""
    safety: dict = field(default_factory=dict)
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


class DashboardBuilder:
    def __init__(self, config_path: str):
        self.config = json.loads(Path(config_path).read_text(encoding="utf-8-sig"))
        self.target = self.config.get("target_bankroll", 1_000_000)

    def build(self, date: str, bankroll: float, sources, mode: str = "current_day") -> CampaignDashboard:
        # Campaign state from postmatch settlement -> campaign state history
        settlement = sources.postmatch_settlement
        hist = sources.campaign_state

        # Bankroll summary
        liquid = settlement.get("simulated_bankroll_after", bankroll)
        locked = settlement.get("pending_entries_count", 0) * (bankroll * 0.05)
        # locked estimate based on pending entries
        total_equity = liquid + locked
        state = settlement.get("bankroll_state_after", "S2")
        mult_liquid = self.target / liquid if liquid > 0 else 1000000
        mult_equity = self.target / total_equity if total_equity > 0 else 1000000

        bankroll_summary = {
            "starting_bankroll": 100.0,
            "liquid_simulated_bankroll": round(liquid, 2),
            "locked_pending_units": round(locked, 2),
            "total_campaign_equity": round(total_equity, 2),
            "target_bankroll": self.target,
            "required_multiplier_liquid": round(mult_liquid, 2),
            "required_multiplier_equity": round(mult_equity, 2),
            "bankroll_state": state,
            "state_change": f"S2->{state}" if state != "S2" else "S2 (unchanged)",
            "note": "locked_pending_units is estimated; pending candidates may settle later"
        }

        # Calendar
        sched = sources.campaign_schedule
        today = sched.get("today_schedule", {})
        calendar_summary = {
            "date": date,
            "stage": today.get("stage", ""),
            "daily_mode": today.get("daily_mode", ""),
            "match_count": today.get("match_count", 0),
            "remaining_matches": today.get("remaining_matches", 0),
            "remaining_windows": today.get("remaining_windows", 0),
        }

        # Execution
        exec_summary = {
            "recommended_modules": today.get("recommended_modules", []),
            "bucket_focus": today.get("bucket_focus", []),
            "parlay_enabled": today.get("parlay_enabled", False),
            "futures_enabled": today.get("futures_enabled", False),
        }

        # Bucket summary from integrated strategy
        integrated = sources.integrated_strategy
        pools = integrated.get("integrated_candidate_pools", {}).get("pools", [])
        bucket_summary = {}
        for pool in pools:
            b = pool.get("bucket", "?")
            bucket_summary[b] = {
                "budget": pool.get("bucket_strategy_budget", 0),
                "candidate_count": len(pool.get("candidates", [])),
                "role": pool.get("role", ""),
            }

        # Candidate summary
        total_cands = sum(p.get("candidate_count", 0) for p in bucket_summary.values())
        candidate_summary = {
            "total_candidates": total_cands,
            "value_candidate_note": "synthetic odds; value_candidate=0 expected with 6% vig",
            "by_bucket": bucket_summary,
        }

        # Parlay
        parlay = sources.parlay_preview
        parlay_summary = {
            "source_candidates": parlay.get("source_candidate_count", 0),
            "raw_combinations": parlay.get("raw_combination_count", 0),
            "blocked_count": parlay.get("blocked_combination_count", 0),
            "ranked_count": parlay.get("ranked_parlay_count", 0),
            "edge_parlays": parlay.get("edge_parlay_count", 0),
            "attack_parlays": parlay.get("attack_parlay_count", 0),
            "note": "same_match legs blocked; synthetic odds limit edge parlay generation"
        }

        # Futures
        futures = sources.futures_preview
        futures_summary = {
            "groups_simulated": futures.get("groups_simulated", 0),
            "path_entries": futures.get("path_probabilities_count", 0),
            "futures_odds_count": futures.get("futures_odds_count", 0),
            "futures_bucket": len(futures.get("futures_bucket", [])),
            "exact_final_pairs": futures.get("exact_final_pair_count", 0),
            "winner_prob_sum": futures.get("winner_probability_sum", 0),
            "proxy_warning": "v1 simplified model; winner_prob_sum may be below 1.0"
        }

        # Settlement
        settlement_summary = {
            "ledger_entries": settlement.get("ledger_entries_count", 0),
            "settled": settlement.get("settled_entries_count", 0),
            "pending": settlement.get("pending_entries_count", 0),
            "hit": settlement.get("hit_count", 0),
            "miss": settlement.get("miss_count", 0),
            "bankroll_change": f"{settlement.get('simulated_bankroll_before',0)}->{settlement.get('simulated_bankroll_after',0)}",
            "routing_hint": settlement.get("next_day_routing_hint", ""),
        }

        # Warnings
        warnings_summary = sources.warnings + [
            "Synthetic odds only; not real bookmaker data",
            "Winner probability model is v1 simplified; see path sanity warning",
        ]

        # Safety
        safety = {
            "campaign_analysis_only": True, "real_bet_execution": False,
            "auto_betting": False, "external_betting_api_allowed": False,
            "simulation_only": True, "not_betting_advice": True,
            "no_real_money": True,
        }

        return CampaignDashboard(
            current_date=date, dashboard_mode=mode,
            campaign_state={"state": state, "bankroll": liquid},
            bankroll_summary=bankroll_summary,
            calendar_summary=calendar_summary,
            execution_schedule_summary=exec_summary,
            bucket_summary=bucket_summary,
            candidate_summary=candidate_summary,
            parlay_summary=parlay_summary,
            futures_summary=futures_summary,
            settlement_summary=settlement_summary,
            warnings_summary=warnings_summary,
            next_day_routing=settlement.get("next_day_routing_hint", ""),
            safety=safety,
        )
