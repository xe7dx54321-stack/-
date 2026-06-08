"""Foundation dry-run runner for campaign preview."""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from worldcup_campaign.policy import (
    CampaignPolicy,
    load_campaign_policy,
    get_max_deployable_bankroll,
    get_required_multiplier,
)
from worldcup_campaign.bankroll_state import (
    BankrollState,
    load_bankroll_states,
    classify_bankroll_state,
    get_bucket_allocation_amounts,
)
from worldcup_campaign.market_registry import (
    MarketDefinition,
    load_market_universe,
    get_markets_for_bucket,
)
from worldcup_campaign.target_math import (
    calculate_target_gap,
    calculate_required_growth_per_window,
    classify_target_urgency,
)


VALID_BUCKETS = ["reserve", "core", "edge", "attack", "futures"]
PLAYABLE_BUCKETS = ["core", "edge", "attack", "futures"]


@dataclass
class FoundationReport:
    campaign_name: str
    current_bankroll: float
    target_bankroll: float
    required_multiplier: float
    windows_left: int
    required_growth_per_window: float
    target_urgency: str
    state: str
    attack_level: str
    max_deployable: float
    bucket_amounts: dict[str, float]
    safety: dict
    market_counts_by_bucket: dict[str, int]


class FoundationRunner:
    """Runs a foundation dry-run of the campaign strategy system."""

    def __init__(
        self,
        policy_path: str,
        states_path: str,
        market_path: str,
        current_bankroll: float,
        windows_left: int,
    ):
        self.policy = load_campaign_policy(policy_path)
        self.states = load_bankroll_states(states_path)
        self.markets = load_market_universe(market_path)
        self.current_bankroll = current_bankroll
        self.windows_left = windows_left

    def run(self) -> FoundationReport:
        """Execute the foundation dry-run and return a report."""
        # Basic calculations
        max_deployable = get_max_deployable_bankroll(
            self.current_bankroll, self.policy
        )
        required_multiplier = get_required_multiplier(
            self.current_bankroll, self.policy
        )

        # Bankroll state
        state_result = classify_bankroll_state(
            self.current_bankroll, self.states, self.policy.target_bankroll
        )

        # Bucket amounts
        bucket_amounts = get_bucket_allocation_amounts(
            self.current_bankroll, state_result
        )

        # Target math
        required_growth = calculate_required_growth_per_window(
            self.current_bankroll,
            self.policy.target_bankroll,
            self.windows_left,
        )
        urgency = classify_target_urgency(required_growth)

        # Market counts by bucket
        market_counts = {}
        for bucket in PLAYABLE_BUCKETS:
            count = len(get_markets_for_bucket(bucket, self.markets))
            market_counts[bucket] = count

        # Safety flags
        safety = {
            "campaign_analysis_only": self.policy.campaign_analysis_only,
            "real_bet_execution": self.policy.real_bet_execution,
            "auto_betting": self.policy.auto_betting,
            "external_betting_api_allowed": self.policy.external_betting_api_allowed,
            "real_money_instruction_allowed": self.policy.real_money_instruction_allowed,
        }

        return FoundationReport(
            campaign_name=self.policy.campaign_name,
            current_bankroll=self.current_bankroll,
            target_bankroll=self.policy.target_bankroll,
            required_multiplier=required_multiplier,
            windows_left=self.windows_left,
            required_growth_per_window=round(required_growth, 4),
            target_urgency=urgency,
            state=state_result.state,
            attack_level=state_result.attack_level,
            max_deployable=round(max_deployable, 2),
            bucket_amounts=bucket_amounts,
            safety=safety,
            market_counts_by_bucket=market_counts,
        )

    def write_json_report(self, report: FoundationReport, path: str) -> None:
        """Write the report as JSON."""
        data = asdict(report)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def write_markdown_report(self, report: FoundationReport, path: str) -> None:
        """Write the report as Markdown."""
        lines = []
        lines.append("# WorldCup Campaign Foundation Preview")
        lines.append("")
        lines.append("## Campaign Policy")
        lines.append("")
        lines.append(f"- **Campaign Name:** {report.campaign_name}")
        lines.append(f"- **Initial Bankroll:** {self.policy.initial_bankroll} {self.policy.currency}")
        lines.append(f"- **Target Bankroll:** {self.policy.target_bankroll} {self.policy.currency}")
        lines.append(f"- **Currency:** {self.policy.currency}")
        lines.append(f"- **Daily Max Deploy Ratio:** {self.policy.daily_max_deploy_ratio}")
        lines.append(f"- **Reserve Min Ratio:** {self.policy.reserve_min_ratio}")
        lines.append(f"- **Allow Empty Strategy:** {self.policy.allow_empty_strategy}")
        lines.append(f"- **Allow Not Full Deployment:** {self.policy.allow_not_full_deployment}")
        lines.append("")
        lines.append("## Bankroll State")
        lines.append("")
        lines.append(f"- **Current Bankroll:** {report.current_bankroll} {self.policy.currency}")
        lines.append(f"- **State:** {report.state}")
        lines.append(f"- **Attack Level:** {report.attack_level}")
        lines.append(f"- **Max Deployable:** {report.max_deployable} {self.policy.currency}")
        lines.append("")
        lines.append("## Bucket Allocation")
        lines.append("")
        lines.append("| Bucket | Ratio | Amount |")
        lines.append("|--------|-------|--------|")
        ratio_by_bucket = {}
        for s in self.states:
            if s.state == report.state:
                ratio_by_bucket = s.bucket_allocation
                break
        if report.state == "TARGET_REACHED":
            ratio_by_bucket = {
                "reserve": 1.0, "core": 0.0,
                "edge": 0.0, "attack": 0.0, "futures": 0.0,
            }
        for bucket in VALID_BUCKETS:
            ratio = ratio_by_bucket.get(bucket, 0)
            amount = report.bucket_amounts.get(bucket, 0)
            lines.append(
                f"| {bucket} | {ratio:.0%} | {amount:.2f} {self.policy.currency} |"
            )
        lines.append("")
        lines.append("## Target Gap")
        lines.append("")
        lines.append(f"- **Required Multiplier:** {report.required_multiplier}x")
        lines.append(f"- **Windows Left:** {report.windows_left}")
        lines.append(f"- **Required Growth Per Window:** {report.required_growth_per_window}x")
        lines.append(f"- **Target Urgency:** {report.target_urgency}")
        lines.append("")
        lines.append("## Market Universe Summary")
        lines.append("")
        lines.append("| Bucket | Available Markets |")
        lines.append("|--------|-------------------|")
        for bucket in PLAYABLE_BUCKETS:
            count = report.market_counts_by_bucket.get(bucket, 0)
            lines.append(f"| {bucket} | {count} |")
        lines.append("")
        lines.append(f"**Total enabled markets:** {len([m for m in self.markets if m.enabled])}")
        lines.append("")
        lines.append("## Safety Boundary")
        lines.append("")
        lines.append("| Flag | Value |")
        lines.append("|------|-------|")
        for key, value in report.safety.items():
            lines.append(f"| {key} | {value} |")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*Generated by WorldCup Campaign Foundation Runner v1*")

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("\n".join(lines), encoding="utf-8")
