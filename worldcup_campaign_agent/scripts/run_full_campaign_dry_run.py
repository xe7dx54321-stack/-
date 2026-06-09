#!/usr/bin/env python3
"""CLI for Full Campaign Dry-Run."""
import argparse, sys, json as j
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.full_campaign_dry_run import (
    FullCampaignDryRunRunner, render_dry_run_json, render_dry_run_markdown,
    write_dry_run_outputs, validate_no_forbidden, _d
)

def root(): return Path(__file__).resolve().parent.parent

def main():
    p = argparse.ArgumentParser(description="Full Campaign Dry-Run")
    p.add_argument("--start-date", type=str, default="2026-06-11")
    p.add_argument("--end-date", type=str, default="2026-07-19")
    p.add_argument("--bankroll", type=float, default=100.0)
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-write", action="store_true", help="Skip writing output files")
    args = p.parse_args()
    r = root()
    runner = FullCampaignDryRunRunner(str(r / "config"))
    result = runner.run(args.start_date, args.end_date, args.bankroll)
    # Validate
    forbidden = validate_no_forbidden(result)
    if forbidden:
        result.errors.append(f"FORBIDDEN_FIELDS_FOUND: {forbidden}")
    # Write outputs
    if not args.no_write:
        paths = write_dry_run_outputs(result)
        print(f"DryRun: days={result.day_count} matchdays={result.matchday_count} blocked={result.blocked_day_count} warn={result.warn_day_count} final_bankroll={result.final_bankroll_preview} target_reached={result.target_reached}", file=sys.stderr)
        for k, vp in paths.items():
            print(f"  {k}: {vp}", file=sys.stderr)
    if args.json:
        print(j.dumps(render_dry_run_json(result), indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    main()
