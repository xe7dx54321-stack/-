#!/usr/bin/env python3
"""CLI entry point for Match Probability Preview."""

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.match_probability_runner import MatchProbabilityRunner


def get_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description="Match Probability Preview")
    parser.add_argument("--date", type=str, help="Target date in YYYY-MM-DD format")
    parser.add_argument("--match-id", type=str, help="Specific match ID to analyze")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    args = parser.parse_args()

    if not args.date and not args.match_id:
        parser.error("Either --date or --match-id is required")

    root = get_root()

    runner = MatchProbabilityRunner(
        ratings_path=str(root / "data" / "seed" / "worldcup_2026_team_ratings.json"),
        prob_config_path=str(root / "config" / "probability_model_config.json"),
        match_registry_path=str(root / "data" / "seed" / "worldcup_2026_match_registry.json"),
        policy_path=str(root / "config" / "campaign_policy.json"),
    )

    if args.match_id:
        preview = runner.run_for_match_id(args.match_id)
    else:
        preview = runner.run_for_date(args.date)

    # Write reports
    json_path = root / "reports" / "generated" / "match_probability_preview.json"
    md_path = root / "reports" / "generated" / "match_probability_preview.md"
    runner.write_json(preview, str(json_path))
    runner.write_markdown(preview, str(md_path))

    print(f"Date: {preview.current_date} | Matches: {preview.matches_count} | Model: {preview.model_name}", file=sys.stderr)
    for m in preview.matches:
        hwp = m.get("home_win_prob", 0)
        dp = m.get("draw_prob", 0)
        awp = m.get("away_win_prob", 0)
        print(f"  {m['match_id']}: H:{hwp:.1%} D:{dp:.1%} A:{awp:.1%} | Conf:{m.get('confidence',0):.2f}", file=sys.stderr)

    if args.json:
        import json as j
        print(j.dumps(asdict(preview), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()