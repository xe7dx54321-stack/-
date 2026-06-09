#!/usr/bin/env python3
"""CLI for Pre-Tournament Patch Window."""
import argparse, sys, json as j
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.pre_tournament_patch_core import (
    build_manual_input_pack, validate_all_manual_inputs,
    run_pre_tournament_smoke_tests, run_review_rehearsal, build_readiness_delta,
    _load_json, _d
)
from worldcup_campaign.pre_tournament_patch import (
    PreTournamentPatch, build_pre_tournament_patch,
    render_pre_tournament_patch_json, render_pre_tournament_patch_markdown,
    write_pre_tournament_patch_outputs,
    validate_no_forbidden_pre_tournament_patch_fields
)

ROOT = Path(__file__).resolve().parent.parent

def main():
    p = argparse.ArgumentParser(description="Pre-Tournament Patch Window")
    p.add_argument("--json", action="store_true", help="Output JSON to stdout")
    p.add_argument("--format", choices=["json","markdown"], default="json")
    p.add_argument("--validate-manual-inputs", action="store_true")
    p.add_argument("--run-smoke-tests", action="store_true")
    p.add_argument("--run-review-rehearsal", action="store_true")
    p.add_argument("--readiness-delta", action="store_true")
    p.add_argument("--no-write", action="store_true")
    args = p.parse_args()

    # Load configs
    manual_cfg = _load_json(ROOT / "config" / "manual_input_pack_config.json") or {}
    smoke_cfg = _load_json(ROOT / "config" / "pre_tournament_smoke_test_config.json") or {}
    rehearsal_cfg = _load_json(ROOT / "config" / "review_rehearsal_config.json") or {}
    delta_cfg = _load_json(ROOT / "config" / "readiness_delta_config.json") or {}

    # Build full patch
    patch = build_pre_tournament_patch({})

    # Validate
    payload = render_pre_tournament_patch_json(patch)
    forbidden = validate_no_forbidden_pre_tournament_patch_fields(payload)
    if forbidden:
        patch.warnings.append(f"FORBIDDEN_FIELDS: {forbidden}")
        print(f"WARNING: Forbidden fields: {forbidden}", file=sys.stderr)

    # Write outputs
    if not args.no_write:
        paths = write_pre_tournament_patch_outputs(patch)
        print(f"Patch: status={patch.patch_status}", file=sys.stderr)
        for k, vp in paths.items():
            print(f"  {k}: {vp}", file=sys.stderr)

    # Output
    if args.format == "markdown":
        print(render_pre_tournament_patch_markdown(patch))
    elif args.json or args.format == "json":
        print(j.dumps(render_pre_tournament_patch_json(patch), indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    main()
