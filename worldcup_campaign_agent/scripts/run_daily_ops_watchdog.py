#!/usr/bin/env python3
"""CLI for Daily Ops Watchdog & Circuit Breaker."""
import argparse, sys, json as j
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.watchdog_runner import WatchdogRunner, _d

def root(): return Path(__file__).resolve().parent.parent

def main():
    p = argparse.ArgumentParser(description='Daily Ops Watchdog')
    p.add_argument('--date', type=str, required=True)
    p.add_argument('--bankroll', type=float, required=True)
    p.add_argument('--mode', type=str, default='full', choices=['pre_daily_ops','post_daily_ops','full'])
    p.add_argument('--json', action='store_true')
    args = p.parse_args()
    r = root()
    config_path = str(r / 'config' / 'daily_ops_watchdog_config.json')
    runner = WatchdogRunner(config_path)
    preview = runner.run(args.date, args.bankroll, args.mode)
    cb = preview.circuit_breaker
    sh = preview.source_health
    print(f"Watchdog: status={cb.get('overall_status','?')} sources={sh.get('available_count',0)}/{sh.get('source_count',0)} blocks={cb.get('hard_block_count',0)}", file=sys.stderr)
    if args.json:
        print(j.dumps(_d(preview), indent=2, ensure_ascii=False, default=str))

if __name__ == '__main__':
    main()
