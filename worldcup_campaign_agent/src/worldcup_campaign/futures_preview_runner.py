"""Futures preview runner: full pipeline for tournament futures analysis."""
import json, sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from worldcup_campaign.group_simulator import GroupSimulator
from worldcup_campaign.knockout_path_simulator import KnockoutPathSimulator
from worldcup_campaign.futures_odds_generator import (
    FuturesOddsGenerator, FuturesProbabilityAggregator
)
from worldcup_campaign.futures_candidate_builder import (
    FuturesCandidateBuilder, FuturesIntegrator
)


@dataclass
class FuturesPreview:
    campaign_name: str = "worldcup_2026_high_odds_campaign"
    current_date: str = ""
    current_bankroll: float = 100.0
    bankroll_state: str = ""
    groups_simulated: int = 0
    group_qualifiers: list = field(default_factory=list)
    third_place_qualifiers: list = field(default_factory=list)
    path_probabilities_count: int = 0
    winner_probability_sum: float = 0.0
    exact_final_pair_count: int = 0
    futures_odds_count: int = 0
    futures_candidates: list = field(default_factory=list)
    futures_bucket: list = field(default_factory=list)
    attack_longshot: list = field(default_factory=list)
    watch_only: list = field(default_factory=list)
    probability_summary: dict = field(default_factory=dict)
    safety: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    generated_at: str = ""
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


class FuturesPreviewRunner:
    def __init__(self, config_paths: dict):
        self.paths = config_paths

    def run(self, date: str, bankroll: float, target_bankroll: float = 1_000_000.0) -> FuturesPreview:
        sim = GroupSimulator(
            self.paths["groups"], self.paths["match_registry"],
            self.paths["group_sim_config"]
        )
        group_results = sim.simulate_all_groups()
        qualifiers = sim.get_all_qualifiers(group_results)
        thirds = sim.get_best_third_place_qualifiers(group_results, 8)

        ko_sim = KnockoutPathSimulator(
            self.paths["ratings"], self.paths["tournament_path_config"]
        )
        paths = ko_sim.build_paths(group_results)
        pairs = ko_sim.calculate_exact_final_pairs(paths)

        odds_gen = FuturesOddsGenerator(
            self.paths["futures_odds_policy"], self.paths["futures_market_config"]
        )
        futures_odds = odds_gen.generate_from_paths(paths)
        pair_odds = odds_gen.generate_exact_final_pair_odds(pairs)
        all_odds = futures_odds + pair_odds

        builder = FuturesCandidateBuilder(
            self.paths["futures_candidate_policy"], self.paths["campaign_score_config"],
            self.paths["futures_odds_policy"], self.paths["futures_market_config"]
        )
        candidates = builder.build_candidates(all_odds, bankroll, target_bankroll)

        integrator = FuturesIntegrator(self.paths["futures_candidate_policy"])
        buckets = integrator.assign_to_buckets(candidates)

        agg = FuturesProbabilityAggregator(self.paths["futures_market_config"])
        summary = agg.build_summary(paths, pairs, all_odds)

        safety = {
            "campaign_analysis_only": True,
            "real_bet_execution": False,
            "auto_betting": False,
            "external_betting_api_allowed": False,
            "simulation_only": True,
            "not_betting_advice": True,
            "uses_real_bookmaker_odds": False,
        }

        return FuturesPreview(
            current_date=date,
            current_bankroll=bankroll,
            groups_simulated=len(group_results),
            group_qualifiers=qualifiers,
            third_place_qualifiers=thirds,
            path_probabilities_count=len(paths),
            winner_probability_sum=summary["winner_probability_sum"],
            exact_final_pair_count=len(pairs),
            futures_odds_count=len(all_odds),
            futures_candidates=[asdict(c) for c in candidates[:30]],
            futures_bucket=[asdict(c) for c in buckets["futures"]],
            attack_longshot=[asdict(c) for c in buckets["attack_longshot"]],
            watch_only=[asdict(c) for c in buckets["watch_only"]],
            probability_summary=summary,
            safety=safety,
            generated_at=datetime.now().isoformat(),
        )

    def write_json(self, preview: FuturesPreview, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(asdict(preview), indent=2, ensure_ascii=False, default=str)
        Path(path).write_text(text, encoding="utf-8")

    def write_markdown(self, preview: FuturesPreview, path: str) -> None:
        lines = []
        lines.append("# Tournament Futures Preview")
        lines.append("")
        lines.append(f"- **Date:** {preview.current_date} | **Bankroll:** {preview.current_bankroll}")
        lines.append(f"- **Groups Simulated:** {preview.groups_simulated}")
        lines.append(f"- **Group Qualifiers:** {len(preview.group_qualifiers)}")
        lines.append(f"- **Third-Place Qualifiers:** {len(preview.third_place_qualifiers)}")
        lines.append(f"- **Path Probabilities:** {preview.path_probabilities_count} teams")
        lines.append(f"- **Winner Prob Sum:** {preview.winner_probability_sum:.4f}")
        lines.append(f"- **Exact Final Pairs:** {preview.exact_final_pair_count}")
        lines.append(f"- **Futures Odds:** {preview.futures_odds_count}")
        lines.append("")
        lines.append("## Futures Bucket Candidates")
        lines.append("| Team | Market | Prob | Odds | EV | Tier |")
        lines.append("|------|--------|------|------|-----|------|")
        for c in preview.futures_bucket[:10]:
            lines.append(
                f"| {c.get('team_name','')} | {c.get('market_type','')} | "
                f"{c.get('path_probability',0):.4f} | {c.get('synthetic_odds',0)} | "
                f"{c.get('ev',0):+.3f} | {c.get('candidate_tier','')} |"
            )
        lines.append("")
        lines.append("## Attack Longshot")
        for c in preview.attack_longshot[:5]:
            lines.append(
                f"- {c.get('team_name','')} | {c.get('market_type','')} | "
                f"Odds: {c.get('synthetic_odds',0)}"
            )
        lines.append("")
        lines.append("## Safety")
        for k, v in preview.safety.items():
            lines.append(f"- **{k}:** {v}")
        lines.append("")
        lines.append("*Generated by Futures Path Simulator v1. Simulation only. NOT betting advice.*")

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        out = chr(10).join(lines)
        Path(path).write_text(out, encoding="utf-8")
