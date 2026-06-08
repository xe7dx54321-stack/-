"""Daily strategy runner: generates daily strategy reports."""

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from worldcup_campaign.daily_strategy import DailyStrategyEngine, DailyUnifiedStrategy


class DailyStrategyRunner:
    """Runs daily strategy generation and report output."""

    def __init__(
        self,
        policy_path: str,
        states_path: str,
        stage_map_path: str,
        match_registry_path: str,
        strategy_rules_path: str,
        tagging_rules_path: str,
        scenario_rules_path: str,
    ):
        self.engine = DailyStrategyEngine(
            policy_path=policy_path,
            states_path=states_path,
            stage_map_path=stage_map_path,
            match_registry_path=match_registry_path,
            strategy_rules_path=strategy_rules_path,
            tagging_rules_path=tagging_rules_path,
            scenario_rules_path=scenario_rules_path,
        )

    def run(self, target_date: str, bankroll: float) -> DailyUnifiedStrategy:
        """Generate daily strategy."""
        dt = date.fromisoformat(target_date)
        return self.engine.generate(dt, bankroll)

    def write_json(self, strategy: DailyUnifiedStrategy, path: str) -> None:
        """Write strategy as JSON."""
        data = asdict(strategy)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def write_markdown(self, strategy: DailyUnifiedStrategy, path: str) -> None:
        """Write strategy as Markdown report."""
        lines = []
        lines.append("# Daily Unified Strategy")
        lines.append("")
        lines.append("## Overview")
        lines.append("")
        lines.append(f"- **Date:** {strategy.current_date}")
        lines.append(f"- **Stage:** {strategy.current_stage}")
        lines.append(f"- **Strategy Profile:** {strategy.strategy_profile}")
        lines.append(f"- **Bankroll:** {strategy.current_bankroll} CNY")
        lines.append(f"- **Target:** {strategy.target_bankroll} CNY")
        lines.append(f"- **State:** {strategy.state} ({strategy.attack_level})")
        lines.append("")
        
        lines.append("## Deployment")
        lines.append("")
        lines.append(f"- **Max Deployable:** {strategy.max_deployable} CNY")
        lines.append(f"- **Deployed Today:** {strategy.deployed_total} CNY")
        lines.append(f"- **Can Deploy:** {strategy.can_deploy}")
        lines.append("")
        
        lines.append("## Bucket Allocation")
        lines.append("")
        lines.append("| Bucket | Amount | Active | Eligible Matches | Notes |")
        lines.append("|--------|--------|--------|------------------|-------|")
        for b in strategy.allocation_plan:
            lines.append(
                f"| {b['bucket']} | {b['amount']} CNY | {'YES' if b['is_active'] else 'NO'} "
                f"| {b['eligible_match_count']} | {b['notes']} |"
            )
        lines.append(f"| **Reserve** | **{strategy.bucket_amounts.get('reserve', 0)} CNY** | N/A | N/A | Held in reserve |")
        lines.append("")

        if strategy.match_labels:
            lines.append("## Today's Match Labels")
            lines.append("")
            lines.append("| # | Match | Home | Away | Stage | Labels | Eligible Buckets | Risk |")
            lines.append("|---|-------|------|------|-------|--------|------------------|------|")
            for ml in strategy.match_labels:
                lines.append(
                    f"| {ml['match_number']} | {ml['match_id']} | {ml['home_team']} "
                    f"| {ml['away_team']} | {ml['stage']} | {', '.join(ml['labels'])} "
                    f"| {', '.join(ml['eligible_buckets'])} | {ml['risk_level']} |"
                )
            lines.append("")

        lines.append("## Match Counts")
        lines.append("")
        lines.append(f"- **Today:** {strategy.today_matches_count}")
        lines.append(f"- **Remaining:** {strategy.matches_remaining_count}")
        lines.append(f"- **Windows Left:** {strategy.effective_windows_left}")
        lines.append("")

        if strategy.scenario_previews:
            lines.append("## Scenario Preview")
            lines.append("")
            lines.append("| Scenario | Projected Bankroll | Projected State | Remaining x | Transition |")
            lines.append("|----------|-------------------|-----------------|-------------|------------|")
            for s in strategy.scenario_previews:
                lines.append(
                    f"| {s['scenario_name']} | {s['projected_bankroll']} CNY "
                    f"| {s['projected_state']} | {s['projected_multiplier_remaining']}x "
                    f"| {s['state_transition']} |"
                )
            lines.append("")

        if strategy.warnings:
            lines.append("## Warnings")
            lines.append("")
            for w in strategy.warnings:
                lines.append(f"- ⚠ {w}")
            lines.append("")

        lines.append("## Safety Boundary")
        lines.append("")
        lines.append("| Flag | Value |")
        lines.append("|------|-------|")
        for key, value in strategy.safety.items():
            lines.append(f"| {key} | {value} |")
        lines.append("")
        lines.append("---")
        lines.append("*Generated by Daily Unified Strategy Engine v1*")
        lines.append("")
        lines.append("> ⚠ **Disclaimer:** This is a strategy skeleton for campaign analysis only. "
                     "No specific team recommendations. No real betting instructions. "
                     "All labels are strategy categories, not predictions or betting advice.")

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("\n".join(lines), encoding="utf-8")