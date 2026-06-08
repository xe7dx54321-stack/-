#!/usr/bin/env python3
"""CLI entry point for the WorldCup Calendar Preview."""

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.calendar_runner import CalendarRunner


def get_config_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "config"


def get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "seed"


def get_output_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "reports" / "generated"


def main():
    parser = argparse.ArgumentParser(
        description="WorldCup Calendar Preview Runner"
    )
    parser.add_argument(
        "--date",
        type=str,
        required=True,
        help="Target date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON to stdout",
    )
    args = parser.parse_args()

    config_dir = get_config_dir()
    data_dir = get_data_dir()
    output_dir = get_output_dir()

    runner = CalendarRunner(
        policy_path=str(config_dir / "campaign_policy.json"),
        stage_map_path=str(config_dir / "worldcup_stage_map.json"),
        match_registry_path=str(data_dir / "worldcup_2026_match_registry.json"),
    )

    state = runner.run(args.date)

    # Write JSON
    json_path = output_dir / "calendar_preview.json"
    runner.write_json_report(state, str(json_path))

    # Write Markdown
    md_path = output_dir / "calendar_preview.md"
    runner.write_markdown_report(state, str(md_path))

    # Summary to stderr
    print(f"Date: {state.current_date} | Stage: {state.current_stage}", file=sys.stderr)
    print(f"Today: {state.matches_today_count} matches | Remaining: {state.matches_remaining_count}", file=sys.stderr)
    print(f"Windows left: {state.effective_windows_left}", file=sys.stderr)
    if state.warnings:
        for w in state.warnings:
            print(f"WARNING: {w}", file=sys.stderr)
    print(f"Reports: {json_path}, {md_path}", file=sys.stderr)

    if args.json:
        import json as j
        print(j.dumps(asdict(state), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()