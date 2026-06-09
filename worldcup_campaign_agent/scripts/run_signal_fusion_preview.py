#!/usr/bin/env python3
"""CLI for Signal Fusion & Strategy Upgrade."""
import argparse, sys, json as j
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.signal_fusion_runner import SignalFusionRunner, _d

def root(): return Path(__file__).resolve().parent.parent

def main():
    p = argparse.ArgumentParser(description="Signal Fusion & Strategy Upgrade")
    p.add_argument("--date", type=str, required=True)
    p.add_argument("--bankroll", type=float, required=True)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    r = root()
    paths = {"fusion_config": str(r / "config" / "signal_fusion_config.json")}
    runner = SignalFusionRunner(paths)
    preview = runner.run(args.date, args.bankroll)
    fu = preview.fusion_summary; sc = preview.score_summary
    print(f"Fusion: date={preview.current_date} candidates={fu.get('candidate_count',0)} upgraded={fu.get('upgraded_candidate_count',0)} promoted={fu.get('promoted_count',0)} avg_adj={sc.get('average_score_adjustment',0):.3f}", file=sys.stderr)
    if args.json:
        print(j.dumps(_d(preview), indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    main()
