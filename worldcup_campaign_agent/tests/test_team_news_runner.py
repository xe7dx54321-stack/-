"""Tests for team news runner."""
import sys, json, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.team_news_runner import TeamNewsRunner, _d
ROOT = Path(__file__).resolve().parent.parent
def get_paths(): return {"team_news_config": str(ROOT / "config" / "team_news_config.json")}
class TestRunner:
    def test_2026_06_11(self):
        r = TeamNewsRunner(get_paths()); p = r.run("2026-06-11", 100.0)
        assert p.current_date == "2026-06-11"
    def test_2026_06_24(self):
        r = TeamNewsRunner(get_paths()); p = r.run("2026-06-24", 100.0)
        assert p.current_date == "2026-06-24"
    def test_2026_07_19(self):
        r = TeamNewsRunner(get_paths()); p = r.run("2026-07-19", 100.0)
        assert p.current_date == "2026-07-19"
    def test_bankroll_5000(self):
        r = TeamNewsRunner(get_paths()); p = r.run("2026-06-11", 5000.0)
        assert p.current_bankroll == 5000.0
    def test_fixture_path(self):
        r = TeamNewsRunner(get_paths())
        p = r.run("2026-06-11", 100.0, fixture_path=str(ROOT / "data" / "seed" / "team_news_seed.json"))
        assert p.news_summary["news_item_count"] >= 10
    def test_news_output(self):
        r = TeamNewsRunner(get_paths()); p = r.run("2026-06-11", 100.0)
        assert p.news_summary["normalized_news_count"] > 0
    def test_injury_output(self):
        r = TeamNewsRunner(get_paths()); p = r.run("2026-06-11", 100.0)
        assert p.injury_summary["injury_count"] + p.injury_summary["suspension_count"] > 0
    def test_context_output(self):
        r = TeamNewsRunner(get_paths()); p = r.run("2026-06-11", 100.0)
        assert p.context_summary["team_context_signal_count"] > 0
    def test_explanation_output(self):
        r = TeamNewsRunner(get_paths()); p = r.run("2026-06-11", 100.0)
        assert p.explanation_summary["market_explanation_count"] > 0
    def test_generates_json(self):
        r = TeamNewsRunner(get_paths()); r.run("2026-06-11", 100.0)
        assert (ROOT / "reports" / "generated" / "team_news_preview.json").exists()
    def test_generates_md(self):
        r = TeamNewsRunner(get_paths()); r.run("2026-06-11", 100.0)
        assert (ROOT / "reports" / "generated" / "team_news_preview.md").exists()
    def test_no_stake(self):
        r = TeamNewsRunner(get_paths()); p = r.run("2026-06-11", 100.0)
        js = json.dumps(_d(p))
        for fb in ["stake_to_match","stake_amount","bet_instruction","bookmaker_account","wallet_address","private_key","api_secret","real_money_balance"]:
            assert fb not in js
    def test_not_betting(self):
        r = TeamNewsRunner(get_paths()); p = r.run("2026-06-11", 100.0)
        assert p.not_betting_advice is True
    def test_round_1_15_regression(self):
        cmds = [
            ["python","scripts/run_campaign_foundation.py","--bankroll","100","--windows-left","40","--json"],
            ["python","scripts/run_calendar_preview.py","--date","2026-06-11","--json"],
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
            ["python","scripts/run_market_expectation.py","--date","2026-06-11","--bankroll","100","--json"],
        ]
        for cmd in cmds:
            rc = os.system(" ".join(cmd))
            assert rc == 0, f"Regression failed: {' '.join(cmd)}"
