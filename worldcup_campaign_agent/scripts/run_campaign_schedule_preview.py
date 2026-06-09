#!/usr/bin/env python3
"""CLI for Campaign Schedule Preview."""
import argparse, sys, json as j
from dataclasses import asdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.schedule_runner import ScheduleRunner


def root():
    return Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser(description="Campaign Schedule Preview")
    p.add_argument("--date", type=str, default=None)
    p.add_argument("--bankroll", type=float, default=100.0)
    p.add_argument("--json", action="store_true")
    p.add_argument("--full-timeline", action="store_true")
    args = p.parse_args()
    r = root()

    paths = {
        "schedule_config": str(r / "config" / "campaign_schedule_config.json"),
        "stage_map": str(r / "config" / "worldcup_stage_map.json"),
        "execution_rules": str(r / "config" / "daily_execution_rules.json"),
        "match_registry": str(r / "data" / "seed" / "worldcup_2026_match_registry.json"),
    }

    runner = ScheduleRunner(paths)

    if args.full_timeline:
        timeline = runner.run_full_timeline(args.bankroll)
        out = r / "reports" / "generated"
        preview = runner.run(args.date or "2026-06-11", args.bankroll,
                           winner_prob_sum=0.6338)
        runner.write_json(preview, str(out / "campaign_schedule_preview.json"))
        runner.write_markdown(preview, str(out / "campaign_schedule_preview.md"))

        result = {
            "full_timeline": timeline,
            "day_count": len(timeline),
            "matchday_count": sum(1 for d in timeline if d["is_matchday"]),
            "safety": preview.safety,
        }
        print(f"Timeline: {len(timeline)} days, matchdays: {sum(1 for d in timeline if d['is_matchday'])}", file=sys.stderr)
        if args.json:
            print(j.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        date_str = args.date or "2026-06-11"
        preview = runner.run(date_str, args.bankroll, winner_prob_sum=0.6338)
        out = r / "reports" / "generated"
        runner.write_json(preview, str(out / "campaign_schedule_preview.json"))
        runner.write_markdown(preview, str(out / "campaign_schedule_preview.md"))

        ts = preview.today_schedule
        print(
            f"Schedule: date={ts.get('date','')} mode={ts.get('daily_mode','')} "
            f"matches={ts.get('match_count',0)} modules={len(ts.get('recommended_modules',[]))} "
            f"parlay={ts.get('parlay_enabled',False)} futures={ts.get('futures_enabled',False)}",
            file=sys.stderr
        )
        if args.json:
            print(j.dumps(asdict(preview), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
