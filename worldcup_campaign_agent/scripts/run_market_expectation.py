#!/usr/bin/env python3
"""CLI for Market Expectation Engine."""
import argparse, sys, json as j
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.market_expectation_runner import MarketExpectationRunner, _d


def root():
    return Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser(description="Market Expectation Engine")
    p.add_argument("--date", type=str, required=True)
    p.add_argument("--bankroll", type=float, required=True)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    r = root()

    paths = {"expectation_config": str(r / "config" / "market_expectation_config.json")}
    runner = MarketExpectationRunner(paths)
    preview = runner.run(args.date, args.bankroll)

    sq = preview.signal_quality_summary
    al = preview.alignment_summary
    bl = preview.blended_summary
    print(
        f"Expectation: date={preview.current_date} "
        f"quality={sq.get('average_quality_score',0):.3f} "
        f"aligned={al.get('market_aligned_count',0)}/{al.get('record_count',0)} "
        f"major={al.get('major_disagreement_count',0)} "
        f"blended={bl.get('blended_record_count',0)}",
        file=sys.stderr
    )
    if args.json:
        print(j.dumps(_d(preview), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
