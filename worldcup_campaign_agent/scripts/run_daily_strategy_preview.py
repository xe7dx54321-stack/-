#!/usr/bin/env python3
"""CLI entry point for Daily Unified Strategy Preview."""

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.daily_strategy_runner import DailyStrategyRunner


def get_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(
        description="Daily Unified Strategy Preview"
    )
    parser.add_argument(
        "--date", type=str, required=True,
        help="Target date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--bankroll", type=float, required=True,
        help="Current bankroll amount",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output JSON to stdout",
    )
    args = parser.parse_args()

    root = get_root()

    runner = DailyStrategyRunner(
        policy_path=str(root / "config" / "campaign_policy.json"),
        states_path=str(root / "config" / "bankroll_states.json"),
        stage_map_path=str(root / "config" / "worldcup_stage_map.json"),
        match_registry_path=str(root / "data" / "seed" / "worldcup_2026_match_registry.json"),
        strategy_rules_path=str(root / "config" / "daily_strategy_rules.json"),
        tagging_rules_path=str(root / "config" / "match_tagging_rules.json"),
        scenario_rules_path=str(root / "config" / "scenario_rules.json"),
    )

    strategy = runner.run(args.date, args.bankroll)

    # Write reports
    json_path = root / "reports" / "generated" / "daily_strategy_preview.json"
    md_path = root / "reports" / "generated" / "daily_strategy_preview.md"
    runner.write_json(strategy, str(json_path))
    runner.write_markdown(strategy, str(md_path))

    # Summary
    print(f"Date: {strategy.current_date} | Stage: {strategy.current_stage}", file=sys.stderr)
    print(f"Bankroll: {strategy.current_bankroll} | State: {strategy.state} | Profile: {strategy.strategy_profile}", file=sys.stderr)
    print(f"Deployed: {strategy.deployed_total} / Max: {strategy.max_deployable}", file=sys.stderr)
    if strategy.warnings:
        for w in strategy.warnings:
            print(f"WARNING: {w}", file=sys.stderr)

    if args.json:
        import json as j
        print(j.dumps(asdict(strategy), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()