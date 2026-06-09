#!/usr/bin/env python3
"""CLI for Campaign Dashboard."""
import argparse, sys, json as j
from dataclasses import asdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.dashboard_runner import DashboardRunner


def root():
    return Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser(description="Campaign Dashboard")
    p.add_argument("--date", type=str, required=True)
    p.add_argument("--bankroll", type=float, required=True)
    p.add_argument("--mode", type=str, default="current_day",
                   choices=["current_day", "postmatch", "full"])
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    r = root()

    paths = {
        "dashboard_config": str(r / "config" / "dashboard_config.json"),
        "daily_brief_config": str(r / "config" / "daily_brief_config.json"),
        "section_policy": str(r / "config" / "dashboard_section_policy.json"),
    }

    runner = DashboardRunner(paths)
    preview = runner.run(args.date, args.bankroll, args.mode)

    bs = preview.dashboard.get("bankroll_summary", {})
    print(
        f"Dashboard: date={preview.current_date} mode={preview.dashboard_mode} "
        f"liquid={bs.get('liquid_simulated_bankroll','?')} "
        f"locked={bs.get('locked_pending_units','?')} "
        f"equity={bs.get('total_campaign_equity','?')} "
        f"state={bs.get('bankroll_state','?')} "
        f"mult={bs.get('required_multiplier_liquid','?')}x",
        file=sys.stderr
    )
    if args.json:
        print(j.dumps(asdict(preview), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
