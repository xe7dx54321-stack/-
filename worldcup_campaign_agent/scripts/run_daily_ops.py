#!/usr/bin/env python3
"""CLI for Daily Ops Runner."""
import argparse, sys, json as j
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
from worldcup_campaign.daily_ops_runner import DailyOpsRunner, _d

def root(): return Path(__file__).resolve().parent.parent

def main():
    p = argparse.ArgumentParser(description='Daily Ops Runner')
    p.add_argument('--date', type=str, required=True)
    p.add_argument('--bankroll', type=float, required=True)
    p.add_argument('--mode', type=str, default='dry_run', choices=['dry_run','execute','skip_optional','watchdog_only'])
    p.add_argument('--json', action='store_true')
    args = p.parse_args()
    r = root()
    runner = DailyOpsRunner(str(r / 'config'))
    result = runner.run(args.date, args.bankroll, args.mode)
    m = result.manifest
    steps_count = len(m.get('steps', []))
    print(f'DailyOps: status={result.overall_status} steps={steps_count} mode={args.mode} upgrade_blocked={result.blocked_from_strategy_upgrade}', file=sys.stderr)
    if args.json:
        print(j.dumps(_d(result), indent=2, ensure_ascii=False, default=str))

if __name__ == '__main__':
    main()
