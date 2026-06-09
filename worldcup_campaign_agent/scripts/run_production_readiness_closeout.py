#!/usr/bin/env python3
"""CLI for Production Readiness Closeout."""
import argparse, sys, json as j
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.production_readiness_closeout import (
    ProductionReadinessCloseoutRunner, render_closeout_json,
    write_closeout_outputs, validate_closeout_no_forbidden, _d
)

def root(): return Path(__file__).resolve().parent.parent

def main():
    p = argparse.ArgumentParser(description="Production Readiness Closeout")
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-write", action="store_true")
    args = p.parse_args()
    r = root()
    runner = ProductionReadinessCloseoutRunner(str(r / "config"))
    result = runner.run()
    forbidden = validate_closeout_no_forbidden(result)
    if forbidden:
        result.warnings.append(f"FORBIDDEN: {forbidden}")
        print(f"WARNING: Forbidden fields: {forbidden}", file=sys.stderr)
    if not args.no_write:
        paths = write_closeout_outputs(result)
        print(f"Closeout: score={result.readiness_score} level={result.readiness_level} status={result.overall_status}", file=sys.stderr)
        for k, vp in paths.items():
            print(f"  {k}: {vp}", file=sys.stderr)
    if args.json:
        print(j.dumps(render_closeout_json(result), indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    main()
