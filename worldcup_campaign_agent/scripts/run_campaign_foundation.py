#!/usr/bin/env python3
"""CLI entry point for the WorldCup Campaign Foundation runner."""

import argparse
import json
import sys
from pathlib import Path

# Add parent src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.runner import FoundationRunner


def get_config_dir() -> Path:
    """Get the config directory relative to this script."""
    return Path(__file__).resolve().parent.parent / "config"


def get_output_dir() -> Path:
    """Get the reports output directory."""
    return Path(__file__).resolve().parent.parent / "reports" / "generated"


def main():
    parser = argparse.ArgumentParser(
        description="WorldCup Campaign Foundation Runner"
    )
    parser.add_argument(
        "--bankroll",
        type=float,
        default=100.0,
        help="Current bankroll (default: 100)",
    )
    parser.add_argument(
        "--windows-left",
        type=int,
        default=40,
        help="Remaining betting windows (default: 40)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON to stdout",
    )
    args = parser.parse_args()

    config_dir = get_config_dir()
    output_dir = get_output_dir()

    runner = FoundationRunner(
        policy_path=str(config_dir / "campaign_policy.json"),
        states_path=str(config_dir / "bankroll_states.json"),
        market_path=str(config_dir / "market_universe.json"),
        current_bankroll=args.bankroll,
        windows_left=args.windows_left,
    )

    report = runner.run()

    # Write JSON report
    json_path = output_dir / "foundation_preview.json"
    runner.write_json_report(report, str(json_path))

    # Write Markdown report
    md_path = output_dir / "foundation_preview.md"
    runner.write_markdown_report(report, str(md_path))

    # Print summary to stderr
    print(f"State: {report.state} | Attack: {report.attack_level}", file=sys.stderr)
    print(f"Max deployable: {report.max_deployable} CNY", file=sys.stderr)
    print(f"Multiplier needed: {report.required_multiplier}x", file=sys.stderr)
    print(f"Reports written to:", file=sys.stderr)
    print(f"  {json_path}", file=sys.stderr)
    print(f"  {md_path}", file=sys.stderr)

    # Output JSON to stdout if requested
    if args.json:
        import dataclasses
        print(json.dumps(dataclasses.asdict(report), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
