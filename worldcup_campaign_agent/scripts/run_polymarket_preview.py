#!/usr/bin/env python3
"""CLI for Polymarket Prediction Market Preview."""
import argparse, sys, json as j
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.polymarket_runner import PolymarketRunner, _dataclass_to_dict


def root():
    return Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser(description="Polymarket Prediction Market Preview")
    p.add_argument("--date", type=str, required=True)
    p.add_argument("--bankroll", type=float, required=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--fixture", type=str, default=None)
    args = p.parse_args()
    r = root()

    paths = {"polymarket_config": str(r / "config" / "polymarket_config.json")}
    runner = PolymarketRunner(paths)
    preview = runner.run(args.date, args.bankroll, fixture_path=args.fixture)

    ds = preview.discovery_summary
    gs = preview.gap_summary
    print(
        f"Polymarket: date={preview.current_date} "
        f"events={ds.get('relevant_event_count',0)}/{ds.get('event_count',0)} "
        f"markets={ds.get('mapped_market_count',0)} "
        f"gaps={gs.get('gap_record_count',0)} "
        f"major={gs.get('major_disagreement_count',0)}",
        file=sys.stderr
    )
    if args.json:
        print(j.dumps(_dataclass_to_dict(preview), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
