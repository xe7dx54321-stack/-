#!/usr/bin/env python3
"""CLI for Team News Preview."""
import argparse, sys, json as j
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.team_news_runner import TeamNewsRunner, _d

def root(): return Path(__file__).resolve().parent.parent

def main():
    p = argparse.ArgumentParser(description="Team News Preview")
    p.add_argument("--date", type=str, required=True)
    p.add_argument("--bankroll", type=float, required=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--fixture", type=str, default=None)
    args = p.parse_args()
    r = root()
    paths = {"team_news_config": str(r / "config" / "team_news_config.json")}
    runner = TeamNewsRunner(paths)
    preview = runner.run(args.date, args.bankroll, fixture_path=args.fixture)
    ns = preview.news_summary; ctx = preview.context_summary; ex = preview.explanation_summary
    print(f"TeamNews: date={preview.current_date} news={ns.get('normalized_news_count',0)} teams={ns.get('team_count',0)} ctx={ctx.get('positive_context_count',0)}/{ctx.get('negative_context_count',0)} expl={ex.get('market_explanation_count',0)}", file=sys.stderr)
    if args.json:
        print(j.dumps(_d(preview), indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    main()
