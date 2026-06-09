#!/usr/bin/env python3
"""CLI for Final Operational Freeze."""
import argparse, sys, json as j
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.final_operational_freeze import (
    FinalOperationalFreezeRunner, build_final_operational_freeze,
    render_freeze_json, render_freeze_markdown, write_freeze_outputs,
    validate_freeze_no_forbidden
)

def main():
    p = argparse.ArgumentParser(description="Final Operational Freeze")
    p.add_argument("--json", action="store_true")
    p.add_argument("--format", choices=["json","markdown"], default="json")
    p.add_argument("--no-write", action="store_true")
    args = p.parse_args()

    freeze = build_final_operational_freeze()
    payload = render_freeze_json(freeze)
    forbidden = validate_freeze_no_forbidden(payload)
    if forbidden:
        freeze.warnings.append(f"FORBIDDEN: {forbidden}")
        print(f"WARNING: Forbidden fields: {forbidden}", file=sys.stderr)

    if not args.no_write:
        paths = write_freeze_outputs(freeze)
        print(f"Freeze: status={freeze.overall_freeze_status} gate={freeze.go_no_go_gate.gate_status if freeze.go_no_go_gate else '?'}", file=sys.stderr)
        for k, vp in paths.items():
            print(f"  {k}: {vp}", file=sys.stderr)

    if args.format == "markdown":
        print(render_freeze_markdown(freeze))
    elif args.json or args.format == "json":
        print(j.dumps(render_freeze_json(freeze), indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    main()
