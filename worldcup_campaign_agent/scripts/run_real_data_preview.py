#!/usr/bin/env python3
"""CLI for Real Data Preview."""
import argparse, sys, json as j
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
from worldcup_campaign.real_data_runner import RealDataRunner, _d

def root(): return Path(__file__).resolve().parent.parent

def main():
    p = argparse.ArgumentParser(description='Real Data Preview')
    p.add_argument('--date', type=str, required=True)
    p.add_argument('--bankroll', type=float, required=True)
    p.add_argument('--match-results', type=str, default=None)
    p.add_argument('--group-table', type=str, default=None)
    p.add_argument('--knockout', type=str, default=None)
    p.add_argument('--odds-snapshot', type=str, default=None)
    p.add_argument('--json', action='store_true')
    args = p.parse_args()
    r = root()
    runner = RealDataRunner(str(r / 'config'))
    preview = runner.run(args.date, args.bankroll,
                                   match_results_path=args.match_results,
                                   group_table_path=args.group_table,
                                   knockout_path=args.knockout,
                                   odds_snapshot_path=args.odds_snapshot)
    mr = preview.match_results
    print(f'RealData: matches={mr.get("count",0)} warnings={len(preview.warnings)}', file=sys.stderr)
    if args.json:
        print(j.dumps(_d(preview), indent=2, ensure_ascii=False, default=str))

if __name__ == '__main__':
    main()
