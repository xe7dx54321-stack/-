#!/usr/bin/env python3
"""CLI for Post-Match Settlement Preview."""
import argparse, sys, json as j
from dataclasses import asdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.postmatch_settlement_runner import PostmatchSettlementRunner


def root():
    return Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser(description="Post-Match Settlement Preview")
    p.add_argument("--date", type=str, required=True)
    p.add_argument("--bankroll", type=float, required=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--manual-results", type=str, default=None)
    args = p.parse_args()
    r = root()

    paths = {
        "policy": str(r / "config" / "campaign_policy.json"),
        "states": str(r / "config" / "bankroll_states.json"),
        "stage_map": str(r / "config" / "worldcup_stage_map.json"),
        "match_registry": str(r / "data" / "seed" / "worldcup_2026_match_registry.json"),
        "strategy_rules": str(r / "config" / "daily_strategy_rules.json"),
        "tagging_rules": str(r / "config" / "match_tagging_rules.json"),
        "scenario_rules": str(r / "config" / "scenario_rules.json"),
        "ratings": str(r / "data" / "seed" / "worldcup_2026_team_ratings.json"),
        "prob_config": str(r / "config" / "probability_model_config.json"),
        "sanity_config": str(r / "config" / "probability_sanity_config.json"),
        "odds_policy": str(r / "config" / "odds_snapshot_policy.json"),
        "ev_config": str(r / "config" / "ev_ranking_config.json"),
        "score_config": str(r / "config" / "campaign_score_config.json"),
        "bucket_policy": str(r / "config" / "bucket_candidate_policy.json"),
        "integration_config": str(r / "config" / "daily_candidate_integration_config.json"),
        "market_registry": str(r / "config" / "market_universe.json"),
        "settlement_config": str(r / "config" / "postmatch_settlement_config.json"),
        "settlement_rules": str(r / "config" / "settlement_rules.json"),
    }

    runner = PostmatchSettlementRunner(paths)
    manual_path = args.manual_results or str(r / "data" / "seed" / "manual_result_seed.json")
    preview = runner.run(args.date, args.bankroll, manual_path)
    out = r / "reports" / "generated"
    runner.write_json(preview, str(out / "postmatch_settlement.json"))
    runner.write_markdown(preview, str(out / "postmatch_settlement.md"))

    print(
        f"Settlement: date={preview.date} ledger={preview.ledger_entries_count} "
        f"settled={preview.settled_entries_count} pending={preview.pending_entries_count} "
        f"hit={preview.hit_count} miss={preview.miss_count} "
        f"bankroll={preview.simulated_bankroll_before}->{preview.simulated_bankroll_after} "
        f"state={preview.bankroll_state_after}",
        file=sys.stderr
    )
    if args.json:
        print(j.dumps(asdict(preview), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
