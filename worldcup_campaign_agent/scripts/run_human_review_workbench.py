#!/usr/bin/env python3
"""CLI for Human Review Workbench."""
import argparse, sys, json as j
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.human_review_workbench import (
    HumanReviewWorkbenchRunner, render_workbench_json,
    write_workbench_outputs, validate_workbench_no_forbidden, _d
)

def root(): return Path(__file__).resolve().parent.parent

def main():
    p = argparse.ArgumentParser(description="Human Review Workbench")
    p.add_argument("--date", type=str, default="2026-06-11")
    p.add_argument("--bankroll", type=float, default=100.0)
    p.add_argument("--json", action="store_true")
    p.add_argument("--decision-file", type=str, default=None, help="JSON file with manual decisions")
    p.add_argument("--no-write", action="store_true")
    args = p.parse_args()
    r = root()
    decisions = None
    if args.decision_file:
        dp = Path(args.decision_file)
        if dp.exists():
            decisions = j.loads(dp.read_text(encoding="utf-8"))
            if isinstance(decisions, dict):
                decisions = [decisions]
    runner = HumanReviewWorkbenchRunner(str(r / "config"))
    result = runner.run(args.date, args.bankroll, decisions)
    forbidden = validate_workbench_no_forbidden(result)
    if forbidden:
        result.warnings.append(f"FORBIDDEN_FIELDS_FOUND: {forbidden}")
        print(f"WARNING: Forbidden fields: {forbidden}", file=sys.stderr)
    if not args.no_write:
        paths = write_workbench_outputs(result)
        print(f"Workbench: items={result.review_item_count} open={result.open_count} critical={result.critical_count} high={result.high_count}", file=sys.stderr)
        for k, vp in paths.items():
            print(f"  {k}: {vp}", file=sys.stderr)
    if args.json:
        print(j.dumps(render_workbench_json(result), indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    main()
