#!/usr/bin/env python3
"""CLI for Model Calibration & Review."""
import argparse, sys, json as j
from dataclasses import asdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.calibration_runner import CalibrationRunner, _dataclass_to_dict


def root():
    return Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser(description="Model Calibration & Review")
    p.add_argument("--date", type=str, required=True)
    p.add_argument("--bankroll", type=float, required=True)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    r = root()

    paths = {
        "source_alignment_policy": str(r / "config" / "source_alignment_policy.json"),
        "calibration_config": str(r / "config" / "calibration_config.json"),
        "model_review_policy": str(r / "config" / "model_review_policy.json"),
    }

    runner = CalibrationRunner(paths)
    review = runner.run(args.date, args.bankroll)

    sa = review.source_alignment_result
    pc = review.probability_calibration_review

    print(
        f"Calibration: date={review.current_date} bankroll={review.current_bankroll} "
        f"alignment={'OK' if sa.get('bankroll_aligned') else 'MISMATCH'} "
        f"records={pc.get('record_count',0)}/{pc.get('realized_count',0)} "
        f"brier={pc.get('brier_score','N/A')} "
        f"recommendations={len(review.calibration_recommendations.get('recommendations',[]))}",
        file=sys.stderr
    )

    if args.json:
        print(j.dumps(_dataclass_to_dict(review), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
