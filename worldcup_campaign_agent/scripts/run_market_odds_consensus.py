#!/usr/bin/env python3
"""CLI for Market Odds Consensus."""
import argparse, sys, json as j
from dataclasses import asdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.market_odds_runner import MarketOddsRunner, _dataclass_to_dict


def root():
    return Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser(description="Market Odds Consensus")
    p.add_argument("--date", type=str, required=True)
    p.add_argument("--bankroll", type=float, required=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--manual-csv", type=str, default=None)
    p.add_argument("--manual-json", type=str, default=None)
    p.add_argument("--synthetic-odds", action="store_true", default=False)
    args = p.parse_args()
    r = root()

    paths = {
        "odds_config": str(r / "config" / "sportsbook_odds_config.json"),
    }

    runner = MarketOddsRunner(paths)
    preview = runner.run(
        args.date, args.bankroll,
        manual_csv=args.manual_csv,
        manual_json=args.manual_json,
        use_synthetic=args.synthetic_odds
    )

    ns = preview.normalized_snapshot
    nv = preview.no_vig_summary
    cs = preview.consensus_summary

    print(
        f"MarketOdds: date={preview.current_date} raw={ns.get('raw_count',0)} "
        f"normalized={ns.get('normalized_count',0)} "
        f"markets={nv.get('market_count',0)} "
        f"overround={nv.get('average_overround',0):.3f} "
        f"consensus={cs.get('market_count',0)}/{cs.get('strong_consensus_count',0)}",
        file=sys.stderr
    )

    if args.json:
        print(j.dumps(_dataclass_to_dict(preview), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
