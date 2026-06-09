#!/usr/bin/env python3
"""CLI entry point for EV Ranking Preview."""
import argparse, sys
from dataclasses import asdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent/"src"))
from worldcup_campaign.ev_ranking_runner import EVRankingRunner

def root(): return Path(__file__).resolve().parent.parent

def main():
    p = argparse.ArgumentParser(description="EV Ranking Preview")
    p.add_argument("--date", type=str, required=True)
    p.add_argument("--bankroll", type=float, required=True)
    p.add_argument("--windows-left", type=int, default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument("--synthetic-odds", action="store_true", help="Use synthetic odds (default)")
    args = p.parse_args()

    r = EVRankingRunner(
        ratings_path=str(root()/"data"/"seed"/"worldcup_2026_team_ratings.json"),
        prob_config_path=str(root()/"config"/"probability_model_config.json"),
        match_registry_path=str(root()/"data"/"seed"/"worldcup_2026_match_registry.json"),
        policy_path=str(root()/"config"/"campaign_policy.json"),
        sanity_config_path=str(root()/"config"/"probability_sanity_config.json"),
        odds_policy_path=str(root()/"config"/"odds_snapshot_policy.json"),
        ev_config_path=str(root()/"config"/"ev_ranking_config.json"),
    )

    preview = r.run(args.date, args.bankroll, args.windows_left)
    r.write_json(preview, str(root()/"reports"/"generated"/"ev_ranking_preview.json"))
    r.write_markdown(preview, str(root()/"reports"/"generated"/"ev_ranking_preview.md"))

    print(f"Date: {preview.date} | Candidates: {preview.candidate_count} | Value: {preview.value_candidate_count}", file=sys.stderr)
    print(f"Sanity: repaired={preview.sanity_summary.get('repaired',0)} blocked={preview.sanity_summary.get('blocked',0)}", file=sys.stderr)
    if args.json:
        import json as j
        print(j.dumps(asdict(preview), indent=2, ensure_ascii=False))

if __name__ == "__main__": main()