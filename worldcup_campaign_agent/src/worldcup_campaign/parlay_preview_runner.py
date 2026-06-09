"""Parlay preview runner: full pipeline from integrated strategy to parlay preview."""

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path

from worldcup_campaign.integrated_daily_strategy import IntegratedStrategyBuilder
from worldcup_campaign.parlay_candidate_builder import ParlayCandidateBuilder
from worldcup_campaign.parlay_optimizer import ParlayOptimizer


@dataclass
class ParlayPreview:
    campaign_name: str = "worldcup_2026_high_odds_campaign"
    current_date: str = ""
    current_stage: str = ""
    current_bankroll: float = 100.0
    bankroll_state: str = ""
    strategy_profile: str = ""
    source_candidate_count: int = 0
    raw_combination_count: int = 0
    blocked_combination_count: int = 0
    ranked_parlay_count: int = 0
    edge_parlay_count: int = 0
    attack_parlay_count: int = 0
    watch_only_parlay_count: int = 0
    top_parlays: list[dict] = field(default_factory=list)
    bucket_pools: dict = field(default_factory=dict)
    safety: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    generated_at: str = ""
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


class ParlayPreviewRunner:
    def __init__(self, config_paths: dict):
        self.paths = config_paths
        self.r6_builder = IntegratedStrategyBuilder(config_paths)

    def run(self, date: str, bankroll: float, windows_left: int = None) -> ParlayPreview:
        # R6 integrated
        integrated = self.r6_builder.build(date, bankroll, windows_left)

        # Build parlay candidates
        builder = ParlayCandidateBuilder(
            self.paths["parlay_optimizer_config"],
            self.paths["parlay_correlation_policy"],
        )
        legs = builder.extract_legs(integrated)
        combos = builder.generate_combinations(legs)

        # Build and filter
        blocked = 0
        candidates = []
        for combo in combos:
            c = builder.build_candidate(combo, bankroll, integrated.target_bankroll)
            if c is None:
                blocked += 1
            else:
                candidates.append(c)

        # Rank
        optimizer = ParlayOptimizer(
            self.paths["parlay_optimizer_config"],
            self.paths["parlay_bucket_policy"],
        )
        ranked = optimizer.rank(candidates)
        pools = optimizer.assign_to_buckets(ranked[:optimizer.config["ranking"]["top_n_report"]])

        safety = {
            "campaign_analysis_only": True, "real_bet_execution": False,
            "auto_betting": False, "external_betting_api_allowed": False,
            "simulation_only": True, "not_betting_advice": True,
        }

        return ParlayPreview(
            current_date=date, current_stage=integrated.current_stage,
            current_bankroll=bankroll, bankroll_state=integrated.bankroll_state,
            strategy_profile=integrated.strategy_profile,
            source_candidate_count=len(legs),
            raw_combination_count=len(combos),
            blocked_combination_count=blocked,
            ranked_parlay_count=len(ranked),
            edge_parlay_count=len(pools.edge_parlays),
            attack_parlay_count=len(pools.attack_parlays),
            watch_only_parlay_count=len(pools.watch_only_parlays),
            top_parlays=ranked[:10],
            bucket_pools={"edge": pools.edge_parlays, "attack": pools.attack_parlays, "watch_only": pools.watch_only_parlays},
            safety=safety,
            warnings=[], generated_at=datetime.now().isoformat(),
        )

    def write_json(self, preview: ParlayPreview, path: str) -> None:
        data = asdict(preview)
        # Convert ParlayCandidate objects to dicts
        top = []
        for c in preview.top_parlays:
            top.append(asdict(c) if hasattr(c, '__dict__') else c)
        data["top_parlays"] = top
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    def write_markdown(self, preview: ParlayPreview, path: str) -> None:
        lines = []
        lines.append("# Parlay Optimizer Preview")
        lines.append("")
        lines.append(f"- **Date:** {preview.current_date} | **Stage:** {preview.current_stage}")
        lines.append(f"- **Bankroll:** {preview.current_bankroll} | **State:** {preview.bankroll_state}")
        lines.append(f"- **Profile:** {preview.strategy_profile}")
        lines.append("")
        lines.append("## Optimizer Summary")
        lines.append(f"- Source candidates: {preview.source_candidate_count}")
        lines.append(f"- Raw combinations: {preview.raw_combination_count}")
        lines.append(f"- Blocked: {preview.blocked_combination_count}")
        lines.append(f"- Ranked: {preview.ranked_parlay_count}")
        lines.append(f"- Edge: {preview.edge_parlay_count} | Attack: {preview.attack_parlay_count} | Watch: {preview.watch_only_parlay_count}")
        lines.append("")

        top = preview.top_parlays[:10]
        if top:
            lines.append("## Top Parlay Candidates")
            lines.append("| Rank | Type | Legs | Combined Odds | Prob | EV | Band | Score | Bucket |")
            lines.append("|------|------|------|---------------|------|-----|------|-------|--------|")
            for i, c in enumerate(top):
                cd = asdict(c) if hasattr(c, '__dict__') else c
                lines.append(f"| {i+1} | {cd.get('parlay_type','')} | {cd.get('leg_count','')} | {cd.get('combined_odds','')} | {cd.get('combined_model_probability',''):.4f} | {cd.get('combined_ev',''):+.3f} | {cd.get('combined_odds_band','')} | {cd.get('parlay_campaign_score',''):.2f} | {cd.get('eligible_bucket','')} |")
            lines.append("")

        lines.append("## Safety")
        for k, v in preview.safety.items():
            lines.append(f"- **{k}:** {v}")
        lines.append("")
        lines.append("*Generated by Parlay Optimizer v1*")
        lines.append("> Parlay analysis only. Mock/synthetic odds. NOT betting advice.")

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("\n".join(lines), encoding="utf-8")