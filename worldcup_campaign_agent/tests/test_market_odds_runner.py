"""Tests for market_odds_runner module."""
import sys, json, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.market_odds_runner import MarketOddsRunner, _dataclass_to_dict

ROOT = Path(__file__).resolve().parent.parent


def get_paths():
    return {
        "odds_config": str(ROOT / "config" / "sportsbook_odds_config.json"),
    }


class TestRunner:
    def test_default_seed_json(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert preview.current_date == "2026-06-11"
        ns = preview.normalized_snapshot
        assert ns["raw_count"] >= 10

    def test_manual_csv(self):
        runner = MarketOddsRunner(get_paths())
        csv_path = str(ROOT / "data" / "seed" / "manual_odds_seed.csv")
        preview = runner.run("2026-06-11", 100.0, manual_csv=csv_path)
        assert preview.normalized_snapshot["raw_count"] >= 10

    def test_manual_json(self):
        runner = MarketOddsRunner(get_paths())
        json_path = str(ROOT / "data" / "seed" / "manual_odds_seed.json")
        preview = runner.run("2026-06-11", 100.0, manual_json=json_path)
        assert preview.normalized_snapshot["raw_count"] >= 10

    def test_synthetic(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0, use_synthetic=True)
        assert preview.current_date == "2026-06-11"

    def test_no_vig_summary(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert "market_count" in preview.no_vig_summary

    def test_consensus_summary(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert "market_count" in preview.consensus_summary

    def test_movement_summary(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert "record_count" in preview.movement_summary

    def test_freshness_summary(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert "fresh_count" in preview.freshness_summary

    def test_model_gap(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert "record_count" in preview.model_vs_market_gap

    def test_generates_json(self):
        runner = MarketOddsRunner(get_paths())
        runner.run("2026-06-11", 100.0)
        path = ROOT / "reports" / "generated" / "market_odds_consensus.json"
        assert path.exists()

    def test_generates_md(self):
        runner = MarketOddsRunner(get_paths())
        runner.run("2026-06-11", 100.0)
        path = ROOT / "reports" / "generated" / "market_odds_consensus.md"
        assert path.exists()

    def test_no_stake_to_match(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        d = _dataclass_to_dict(preview)
        js = json.dumps(d)
        assert "stake_to_match" not in js

    def test_no_bet_instruction(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        d = _dataclass_to_dict(preview)
        js = json.dumps(d)
        assert "bet_instruction" not in js

    def test_no_bookmaker_account(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        d = _dataclass_to_dict(preview)
        js = json.dumps(d)
        assert "bookmaker_account" not in js

    def test_no_api_key(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        d = _dataclass_to_dict(preview)
        js = json.dumps(d)
        assert "api_key" not in js and "api_secret" not in js

    def test_network_default_disabled(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert preview.safety["network_fetch_default_enabled"] is False

    def test_not_betting_advice(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert preview.not_betting_advice is True

    def test_2026_06_24(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-24", 100.0)
        assert preview.current_date == "2026-06-24"

    def test_2026_07_19(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-07-19", 100.0)
        assert preview.current_date == "2026-07-19"

    def test_bankroll_5000(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 5000.0)
        assert preview.current_bankroll == 5000.0


    def test_strong_consensus_zero_with_two_sources(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        cs = preview.consensus_summary
        assert cs["strong_consensus_count"] == 0, f"Got strong={cs['strong_consensus_count']} with 2 sources"

    def test_movement_record_count_gt_zero(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        ms = preview.movement_summary
        assert ms["record_count"] > 0, f"movement_record_count={ms['record_count']}"

    def test_gap_record_count_gt_zero(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        mg = preview.model_vs_market_gap
        assert mg["record_count"] > 0, f"gap_record_count={mg['record_count']}"

    def test_gap_directions_sum(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        mg = preview.model_vs_market_gap
        total = mg["model_above_market_count"] + mg["model_below_market_count"] + mg["aligned_count"]
        assert total == mg["record_count"]

    def test_opening_current_in_seed(self):
        runner = MarketOddsRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        snap_types = set()
        for e in preview.odds_snapshot.get("entries", []):
            snap_types.add(e.get("snapshot_type", ""))
        assert "opening" in snap_types
        assert "current" in snap_types
    def test_round_1_12_regression(self):
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
            ["python", "scripts/run_model_calibration_review.py", "--date", "2026-06-11", "--bankroll", "100", "--json"],
        ]
        for cmd in scripts:
            result = os.system(" ".join(cmd))
            assert result == 0, f"Regression failed: {' '.join(cmd)}"
