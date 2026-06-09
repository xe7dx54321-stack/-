#!/usr/bin/env python3
"""CLI for Parlay Preview."""
import argparse, sys, json as j
from dataclasses import asdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent/"src"))
from worldcup_campaign.parlay_preview_runner import ParlayPreviewRunner

def root(): return Path(__file__).resolve().parent.parent

def main():
    p = argparse.ArgumentParser(description="Parlay Preview")
    p.add_argument("--date", type=str, required=True)
    p.add_argument("--bankroll", type=float, required=True)
    p.add_argument("--windows-left", type=int, default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument("--synthetic-odds", action="store_true")
    args = p.parse_args()
    r = root()

    paths = {
        "policy":str(r/"config"/"campaign_policy.json"),
        "states":str(r/"config"/"bankroll_states.json"),
        "stage_map":str(r/"config"/"worldcup_stage_map.json"),
        "match_registry":str(r/"data"/"seed"/"worldcup_2026_match_registry.json"),
        "strategy_rules":str(r/"config"/"daily_strategy_rules.json"),
        "tagging_rules":str(r/"config"/"match_tagging_rules.json"),
        "scenario_rules":str(r/"config"/"scenario_rules.json"),
        "ratings":str(r/"data"/"seed"/"worldcup_2026_team_ratings.json"),
        "prob_config":str(r/"config"/"probability_model_config.json"),
        "sanity_config":str(r/"config"/"probability_sanity_config.json"),
        "odds_policy":str(r/"config"/"odds_snapshot_policy.json"),
        "ev_config":str(r/"config"/"ev_ranking_config.json"),
        "score_config":str(r/"config"/"campaign_score_config.json"),
        "bucket_policy":str(r/"config"/"bucket_candidate_policy.json"),
        "integration_config":str(r/"config"/"daily_candidate_integration_config.json"),
        "market_registry":str(r/"config"/"market_universe.json"),
        "parlay_optimizer_config":str(r/"config"/"parlay_optimizer_config.json"),
        "parlay_correlation_policy":str(r/"config"/"parlay_correlation_policy.json"),
        "parlay_bucket_policy":str(r/"config"/"parlay_bucket_policy.json"),
    }

    runner = ParlayPreviewRunner(paths)
    preview = runner.run(args.date, args.bankroll, args.windows_left)
    out = r/"reports"/"generated"
    runner.write_json(preview, str(out/"parlay_preview.json"))
    runner.write_markdown(preview, str(out/"parlay_preview.md"))

    print(f"Parlay: source={preview.source_candidate_count} raw={preview.raw_combination_count} blocked={preview.blocked_combination_count} ranked={preview.ranked_parlay_count}", file=sys.stderr)
    if args.json:
        print(j.dumps(asdict(preview), indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__": main()