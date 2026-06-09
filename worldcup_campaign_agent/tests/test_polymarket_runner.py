"""Tests for polymarket_runner module."""
import sys, json, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.polymarket_runner import PolymarketRunner, _dataclass_to_dict
ROOT = Path(__file__).resolve().parent.parent
def get_paths():
    return {"polymarket_config": str(ROOT / "config" / "polymarket_config.json")}
class TestRunner:
    def test_2026_06_11(self):
        r = PolymarketRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        assert p.current_date == "2026-06-11"
    def test_2026_06_24(self):
        r = PolymarketRunner(get_paths())
        p = r.run("2026-06-24", 100.0)
        assert p.current_date == "2026-06-24"
    def test_2026_07_19(self):
        r = PolymarketRunner(get_paths())
        p = r.run("2026-07-19", 100.0)
        assert p.current_date == "2026-07-19"
    def test_bankroll_5000(self):
        r = PolymarketRunner(get_paths())
        p = r.run("2026-06-11", 5000.0)
        assert p.current_bankroll == 5000.0
    def test_fixture_path(self):
        r = PolymarketRunner(get_paths())
        fp = str(ROOT / "data" / "seed" / "polymarket_seed.json")
        p = r.run("2026-06-11", 100.0, fixture_path=fp)
        assert p.discovery_summary["event_count"] >= 3
    def test_discovery_summary(self):
        r = PolymarketRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        assert p.discovery_summary["relevant_event_count"] >= 3
    def test_gap_summary(self):
        r = PolymarketRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        assert p.gap_summary["gap_record_count"] > 0
    def test_generates_json(self):
        r = PolymarketRunner(get_paths())
        r.run("2026-06-11", 100.0)
        assert (ROOT / "reports" / "generated" / "polymarket_preview.json").exists()
    def test_generates_md(self):
        r = PolymarketRunner(get_paths())
        r.run("2026-06-11", 100.0)
        assert (ROOT / "reports" / "generated" / "polymarket_preview.md").exists()
    def test_no_stake(self):
        r = PolymarketRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        js = json.dumps(_dataclass_to_dict(p))
        for forbidden in ["stake_to_match","stake_amount","bet_instruction","wallet_address","private_key","api_secret","signed_order","submit_order"]:
            assert forbidden not in js, f"Found forbidden field: {forbidden}"
    def test_trading_disabled(self):
        r = PolymarketRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        s = p.safety
        assert s["order_submission_allowed"] is False
        assert s["wallet_connection_allowed"] is False
        assert s["network_fetch_default_enabled"] is False
    def test_not_betting_advice(self):
        r = PolymarketRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        assert p.not_betting_advice is True
    def test_round_1_13_regression(self):
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
        ]
        for cmd in cmds:
            rc = os.system(" ".join(cmd))
            assert rc == 0, f"Regression failed: {' '.join(cmd)}"
