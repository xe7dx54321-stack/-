"""Tests for market_expectation_runner module."""
import sys, json, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.market_expectation_runner import MarketExpectationRunner, _d
ROOT = Path(__file__).resolve().parent.parent
def get_paths():
    return {"expectation_config": str(ROOT / "config" / "market_expectation_config.json")}
class TestRunner:
    def test_2026_06_11(self):
        r = MarketExpectationRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        assert p.current_date == "2026-06-11"
    def test_2026_06_24(self):
        r = MarketExpectationRunner(get_paths())
        p = r.run("2026-06-24", 100.0)
        assert p.current_date == "2026-06-24"
    def test_2026_07_19(self):
        r = MarketExpectationRunner(get_paths())
        p = r.run("2026-07-19", 100.0)
        assert p.current_date == "2026-07-19"
    def test_bankroll_5000(self):
        r = MarketExpectationRunner(get_paths())
        p = r.run("2026-06-11", 5000.0)
        assert p.current_bankroll == 5000.0
    def test_source_summary(self):
        r = MarketExpectationRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        assert p.source_summary["model_available"] or p.source_summary["sportsbook_available"]
    def test_signal_quality_output(self):
        r = MarketExpectationRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        assert "average_quality_score" in p.signal_quality_summary
    def test_alignment_output(self):
        r = MarketExpectationRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        assert "record_count" in p.alignment_summary
    def test_blended_output(self):
        r = MarketExpectationRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        assert "blended_record_count" in p.blended_summary
    def test_generates_json(self):
        r = MarketExpectationRunner(get_paths())
        r.run("2026-06-11", 100.0)
        assert (ROOT / "reports" / "generated" / "market_expectation.json").exists()
    def test_generates_md(self):
        r = MarketExpectationRunner(get_paths())
        r.run("2026-06-11", 100.0)
        assert (ROOT / "reports" / "generated" / "market_expectation.md").exists()
    def test_no_stake(self):
        r = MarketExpectationRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        js = json.dumps(_d(p))
        for fb in ["stake_to_match","stake_amount","bet_instruction","bookmaker_account","wallet_address","private_key","api_secret","signed_order","submit_order","real_money_balance","guaranteed_profit"]:
            assert fb not in js, f"Found: {fb}"
    def test_not_betting(self):
        r = MarketExpectationRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        assert p.not_betting_advice is True
    def test_round_1_14_regression(self):
        cmds = [
            ["python","scripts/run_campaign_foundation.py","--bankroll","100","--windows-left","40","--json"],
            ["python","scripts/run_calendar_preview.py","--date","2026-06-11","--json"],
            ["python","scripts/run_daily_strategy_preview.py","--date","2026-06-11","--bankroll","100","--json"],
            ["python","scripts/run_match_probability_preview.py","--date","2026-06-11","--json"],
            ["python","scripts/run_ev_ranking_preview.py","--date","2026-06-11","--bankroll","100","--json","--synthetic-odds"],
            ["python","scripts/run_integrated_daily_strategy.py","--date","2026-06-11","--bankroll","100","--json","--synthetic-odds"],
            ["python","scripts/run_parlay_preview.py","--date","2026-06-11","--bankroll","100","--json","--synthetic-odds"],
            ["python","scripts/run_futures_preview.py","--date","2026-06-11","--bankroll","100","--json","--synthetic-futures-odds"],
            ["python","scripts/run_campaign_schedule_preview.py","--date","2026-06-11","--bankroll","100","--json"],
            ["python","scripts/run_postmatch_settlement.py","--date","2026-06-11","--bankroll","100","--json"],
            ["python","scripts/run_campaign_dashboard.py","--date","2026-06-11","--bankroll","100","--json"],
            ["python","scripts/run_model_calibration_review.py","--date","2026-06-11","--bankroll","100","--json"],
            ["python","scripts/run_market_odds_consensus.py","--date","2026-06-11","--bankroll","100","--json"],
            ["python","scripts/run_polymarket_preview.py","--date","2026-06-11","--bankroll","100","--json"],
        ]
        for cmd in cmds:
            rc = os.system(" ".join(cmd))
            assert rc == 0, f"Regression failed: {' '.join(cmd)}"
