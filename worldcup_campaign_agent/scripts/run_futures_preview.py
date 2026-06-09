#!/usr/bin/env python3
"""CLI for Tournament Futures Preview."""
import argparse, sys, json as j
from dataclasses import asdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.futures_preview_runner import FuturesPreviewRunner


def root():
    return Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser(description="Tournament Futures Preview")
    p.add_argument("--date", type=str, required=True)
    p.add_argument("--bankroll", type=float, required=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--synthetic-futures-odds", action="store_true")
    args = p.parse_args()
    r = root()

    paths = {
        "groups": str(r / "data" / "seed" / "worldcup_2026_groups.json"),
        "match_registry": str(r / "data" / "seed" / "worldcup_2026_match_registry.json"),
        "ratings": str(r / "data" / "seed" / "worldcup_2026_team_ratings.json"),
        "group_sim_config": str(r / "config" / "group_simulation_config.json"),
        "tournament_path_config": str(r / "config" / "tournament_path_config.json"),
        "futures_odds_policy": str(r / "config" / "futures_odds_policy.json"),
        "futures_market_config": str(r / "config" / "futures_market_config.json"),
        "futures_candidate_policy": str(r / "config" / "futures_candidate_policy.json"),
        "campaign_score_config": str(r / "config" / "campaign_score_config.json"),
    }

    runner = FuturesPreviewRunner(paths)
    preview = runner.run(args.date, args.bankroll)
    out = r / "reports" / "generated"
    runner.write_json(preview, str(out / "futures_preview.json"))
    runner.write_markdown(preview, str(out / "futures_preview.md"))

    summary = (
        f"Futures: groups={preview.groups_simulated} "
        f"paths={preview.path_probabilities_count} "
        f"odds={preview.futures_odds_count} "
        f"candidates={len(preview.futures_candidates)} "
        f"bucket={len(preview.futures_bucket)} "
        f"attack={len(preview.attack_longshot)} "
        f"watch={len(preview.watch_only)}"
    )
    print(summary, file=sys.stderr)
    if args.json:
        print(j.dumps(asdict(preview), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
