"""Tests for calibration_runner module."""
import sys, json, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.calibration_runner import CalibrationRunner, _dataclass_to_dict

ROOT = Path(__file__).resolve().parent.parent

def get_paths():
    return {
        "source_alignment_policy": str(ROOT / "config" / "source_alignment_policy.json"),
        "calibration_config": str(ROOT / "config" / "calibration_config.json"),
        "model_review_policy": str(ROOT / "config" / "model_review_policy.json"),
    }


class TestRunner:
    def test_runner_executes(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-11", 100.0)
        assert review.current_date == "2026-06-11"

    def test_2026_06_11(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-11", 100.0)
        assert review.current_date == "2026-06-11"
        assert review.current_bankroll == 100.0

    def test_2026_06_24(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-24", 100.0)
        assert review.current_date == "2026-06-24"

    def test_2026_07_19(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-07-19", 100.0)
        assert review.current_date == "2026-07-19"

    def test_bankroll_5000(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-11", 5000.0)
        assert review.current_bankroll == 5000.0

    def test_source_alignment_result(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-11", 100.0)
        assert "cli_date" in review.source_alignment_result

    def test_probability_calibration_review(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-11", 100.0)
        assert "record_count" in review.probability_calibration_review

    def test_bucket_performance_review(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-11", 100.0)
        assert "bucket_breakdowns" in review.bucket_performance_review

    def test_parlay_performance_review(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-11", 100.0)
        assert "source_candidate_count" in review.parlay_performance_review

    def test_futures_performance_review(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-11", 100.0)
        assert "futures_candidate_count" in review.futures_performance_review

    def test_calibration_recommendations(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-11", 100.0)
        assert "recommendations" in review.calibration_recommendations

    def test_generates_model_calibration_review_json(self):
        runner = CalibrationRunner(get_paths())
        runner.run("2026-06-11", 100.0)
        path = ROOT / "reports" / "generated" / "model_calibration_review.json"
        assert path.exists()

    def test_generates_model_calibration_review_md(self):
        runner = CalibrationRunner(get_paths())
        runner.run("2026-06-11", 100.0)
        path = ROOT / "reports" / "generated" / "model_calibration_review.md"
        assert path.exists()

    def test_generates_calibration_recommendations_json(self):
        runner = CalibrationRunner(get_paths())
        runner.run("2026-06-11", 100.0)
        path = ROOT / "reports" / "generated" / "calibration_recommendations.json"
        assert path.exists()

    def test_no_stake_to_match(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-11", 100.0)
        d = _dataclass_to_dict(review)
        js = json.dumps(d)
        assert "stake_to_match" not in js

    def test_no_stake_amount(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-11", 100.0)
        d = _dataclass_to_dict(review)
        js = json.dumps(d)
        assert "stake_amount" not in js

    def test_no_bet_instruction(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-11", 100.0)
        d = _dataclass_to_dict(review)
        js = json.dumps(d)
        assert "bet_instruction" not in js

    def test_no_bookmaker_account(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-11", 100.0)
        d = _dataclass_to_dict(review)
        js = json.dumps(d)
        assert "bookmaker_account" not in js

    def test_no_real_money_balance(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-11", 100.0)
        d = _dataclass_to_dict(review)
        js = json.dumps(d)
        assert "real_money_balance" not in js

    def test_no_guaranteed_profit(self):
        runner = CalibrationRunner(get_paths())
        review = runner.run("2026-06-11", 100.0)
        d = _dataclass_to_dict(review)
        js = json.dumps(d)
        assert "guaranteed_profit" not in js

    def test_round_1_11_regression(self):
        """Verify Round 1-11 scripts still run."""
        scripts = [
            ["python", "scripts/run_campaign_foundation.py", "--bankroll", "100", "--windows-left", "40", "--json"],
            ["python", "scripts/run_calendar_preview.py", "--date", "2026-06-11", "--json"],
            ["python", "scripts/run_daily_strategy_preview.py", "--date", "2026-06-11", "--bankroll", "100", "--json"],
            ["python", "scripts/run_match_probability_preview.py", "--date", "2026-06-11", "--json"],
            ["python", "scripts/run_ev_ranking_preview.py", "--date", "2026-06-11", "--bankroll", "100", "--json", "--synthetic-odds"],
            ["python", "scripts/run_integrated_daily_strategy.py", "--date", "2026-06-11", "--bankroll", "100", "--json", "--synthetic-odds"],
            ["python", "scripts/run_parlay_preview.py", "--date", "2026-06-11", "--bankroll", "100", "--json", "--synthetic-odds"],
            ["python", "scripts/run_futures_preview.py", "--date", "2026-06-11", "--bankroll", "100", "--json", "--synthetic-futures-odds"],
            ["python", "scripts/run_campaign_schedule_preview.py", "--date", "2026-06-11", "--bankroll", "100", "--json"],
            ["python", "scripts/run_postmatch_settlement.py", "--date", "2026-06-11", "--bankroll", "100", "--json"],
            ["python", "scripts/run_campaign_dashboard.py", "--date", "2026-06-11", "--bankroll", "100", "--json"],
        ]
        for cmd in scripts:
            result = os.system(" ".join(cmd))
            assert result == 0, f"Regression failed: {' '.join(cmd)}"
