"""Tests for Real Data Adapter & Settlement Auto-Match."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.real_data_adapter import (
    check_source_policy, scan_for_forbidden, FORBIDDEN,
    load_match_results_json, load_match_results_csv, normalize_match_results,
    load_group_table_results, load_real_odds_snapshot_json,
    settle_1x2, settle_over_under, settle_correct_score, settle_futures,
    match_ledger_to_results, NormalizedMatchResult, AutoSettlementPreview, _d
)
from worldcup_campaign.real_data_runner import RealDataRunner

ROOT = Path(__file__).resolve().parent.parent
SD = ROOT / "data" / "seed"


class TestSourcePolicy:
    def test_policy_all_clear(self):
        cfg = {"network_fetch_default_enabled": False, "login_required_source_allowed": False,
               "wallet_connection_allowed": False, "bookmaker_account_access_allowed": False}
        sp = check_source_policy(cfg)
        assert sp.all_clear is True

    def test_policy_login_violation(self):
        cfg = {"network_fetch_default_enabled": False, "login_required_source_allowed": True,
               "wallet_connection_allowed": False, "bookmaker_account_access_allowed": False}
        sp = check_source_policy(cfg)
        assert sp.all_clear is False

    def test_scan_no_forbidden(self):
        data = {"matches": [{"match_id": "M1", "home_score_90": 2}]}
        ff = scan_for_forbidden(data, FORBIDDEN)
        assert len(ff) == 0

    def test_scan_detects_stake(self):
        data = {"matches": [{"match_id": "M1", "stake": 10}]}
        ff = scan_for_forbidden(data, FORBIDDEN)
        assert len(ff) >= 1


class TestMatchResultLoader:
    def test_load_json(self):
        policy = {}
        results = load_match_results_json(str(SD / "match_results_seed.json"), policy)
        assert len(results) == 4
        assert results[0].match_id == "GS_A_R1_001"

    def test_load_csv(self):
        policy = {}
        results = load_match_results_csv(str(SD / "match_results_seed.csv"), policy)
        assert len(results) == 4

    def test_normalize(self):
        policy = {}
        raw = load_match_results_json(str(SD / "match_results_seed.json"), policy)
        normalized = normalize_match_results(raw, {})
        assert len(normalized) == 4
        assert normalized[0].winner_90 in ("home", "draw", "away", "")


class TestSettlementRules:
    def test_1x2_home_win(self):
        mr = NormalizedMatchResult(match_id="M1", home_score_90=2, away_score_90=1,
                                    winner_90="home", result_status="completed")
        r = settle_1x2({"candidate_id": "c1", "selection_id": "home"}, mr)
        assert r.outcome_status == "hit"

    def test_1x2_miss(self):
        mr = NormalizedMatchResult(match_id="M1", home_score_90=0, away_score_90=1,
                                    winner_90="away", result_status="completed")
        r = settle_1x2({"candidate_id": "c1", "selection_id": "home"}, mr)
        assert r.outcome_status == "miss"

    def test_over_under_hit(self):
        mr = NormalizedMatchResult(match_id="M1", home_score_90=2, away_score_90=1,
                                    result_status="completed")
        r = settle_over_under({"candidate_id": "c1", "market_type": "over_under_2.5", "selection_id": "over"}, mr)
        assert r.outcome_status == "hit"

    def test_over_under_push(self):
        mr = NormalizedMatchResult(match_id="M1", home_score_90=1, away_score_90=1,
                                    result_status="completed")
        r = settle_over_under({"candidate_id": "c1", "market_type": "over_under_2.0", "selection_id": "over"}, mr)
        assert r.outcome_status == "push"

    def test_correct_score_hit(self):
        mr = NormalizedMatchResult(match_id="M1", home_score_90=2, away_score_90=1,
                                    result_status="completed")
        r = settle_correct_score({"candidate_id": "c1", "selection_id": "2-1"}, mr)
        assert r.outcome_status == "hit"

    def test_futures_pending(self):
        r = settle_futures({"candidate_id": "c1", "market_type": "winner"}, {}, {})
        assert r.outcome_status == "pending"

    def test_pending_match(self):
        mr = NormalizedMatchResult(match_id="M1", result_status="scheduled")
        r = settle_1x2({"candidate_id": "c1", "selection_id": "home"}, mr)
        assert r.outcome_status == "pending"


class TestAutoSettlement:
    def test_match_ledger(self):
        ledger = {"ledger": [
            {"entry_id": "e1", "match_id": "GS_A_R1_001", "market_type": "1x2", "selection_id": "draw"}
        ]}
        results = [NormalizedMatchResult(match_id="GS_A_R1_001", home_score_90=1, away_score_90=1,
                                          winner_90="draw", result_status="completed")]
        preview = match_ledger_to_results(ledger, results, {}, {}, {})
        assert preview.ledger_entry_count == 1
        assert preview.matched_count == 1


class TestRealDataRunner:
    def test_run_2026_06_11(self):
        r = RealDataRunner()
        p = r.run("2026-06-11", 100.0)
        assert p.current_date == "2026-06-11"
        assert p.match_results.get("count", 0) == 4

    def test_run_2026_06_24(self):
        r = RealDataRunner()
        p = r.run("2026-06-24", 100.0)
        assert p.current_date == "2026-06-24"

    def test_run_2026_07_19(self):
        r = RealDataRunner()
        p = r.run("2026-07-19", 100.0)
        assert p.current_date == "2026-07-19"

    def test_bankroll_5000(self):
        r = RealDataRunner()
        p = r.run("2026-06-11", 5000.0)
        assert p.current_bankroll == 5000.0

    def test_source_policy_output(self):
        r = RealDataRunner()
        p = r.run("2026-06-11", 100.0)
        assert "all_clear" in p.source_policy_status

    def test_generates_json(self):
        r = RealDataRunner()
        r.run("2026-06-11", 100.0)
        assert (ROOT / "reports" / "generated" / "real_data_preview.json").exists()

    def test_generates_md(self):
        r = RealDataRunner()
        r.run("2026-06-11", 100.0)
        assert (ROOT / "reports" / "generated" / "real_data_preview.md").exists()

    def test_no_stake(self):
        r = RealDataRunner()
        p = r.run("2026-06-11", 100.0)
        js = json.dumps(_d(p))
        for fb in ["stake_to_match", "stake_amount", "bet_instruction",
                    "bookmaker_account", "wallet_address", "private_key",
                    "real_money_balance", "guaranteed_profit"]:
            assert fb not in js

    def test_not_betting(self):
        r = RealDataRunner()
        p = r.run("2026-06-11", 100.0)
        assert p.not_betting_advice is True
        assert p.analysis_only is True
        assert p.simulation_only is True

    def test_safety_flags(self):
        r = RealDataRunner()
        p = r.run("2026-06-11", 100.0)
        s = p.safety
        assert s["real_bet_execution"] is False
        assert s["auto_betting"] is False
        assert s["network_fetch_default_enabled"] is False
