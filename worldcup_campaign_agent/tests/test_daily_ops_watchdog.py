"""
Tests for Daily Ops Watchdog and Circuit Breaker.
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.daily_ops_watchdog import (
    run_source_health_check, run_circuit_breaker, build_review_queue,
    build_quality_gate, SourceHealthSummary, CircuitBreakerResult,
    ReviewQueue, QualityGate, FORBIDDEN_FIELDS,
    _deep_scan_for_fields, _scan_execution_flags
)
from worldcup_campaign.watchdog_runner import WatchdogRunner, _d

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = str(ROOT / "config" / "daily_ops_watchdog_config.json")
RP = ROOT / "reports" / "generated"


def _cfg():
    return json.loads(open(CONFIG_PATH, encoding="utf-8-sig").read())


class TestForbiddenFieldScan:
    def test_no_forbidden(self):
        data = {"campaign_name": "test"}
        findings = _deep_scan_for_fields(data, set(FORBIDDEN_FIELDS))
        assert len(findings) == 0

    def test_detects_stake(self):
        data = {"candidates": [{"stake": 10}]}
        findings = _deep_scan_for_fields(data, set(FORBIDDEN_FIELDS))
        assert len(findings) >= 1

    def test_detects_bet_instruction(self):
        data = {"output": {"bet_instruction": "do X"}}
        findings = _deep_scan_for_fields(data, set(FORBIDDEN_FIELDS))
        assert len(findings) >= 1

    def test_detects_wallet(self):
        data = {"wallet_address": "0x123"}
        findings = _deep_scan_for_fields(data, set(FORBIDDEN_FIELDS))
        assert len(findings) >= 1

    def test_deeply_nested(self):
        data = {"a": {"b": {"stake_to_match": 50}}}
        findings = _deep_scan_for_fields(data, set(FORBIDDEN_FIELDS))
        assert len(findings) >= 1


class TestExecutionFlagScan:
    def test_no_flags(self):
        data = {"real_bet_execution": False}
        findings = _scan_execution_flags(data, {"real_bet_execution"}, {True, "true"})
        assert len(findings) == 0

    def test_detects_real_bet(self):
        data = {"real_bet_execution": True}
        findings = _scan_execution_flags(data, {"real_bet_execution"}, {True, "true"})
        assert len(findings) >= 1


class TestSourceHealth:
    def test_missing(self):
        paths = {"nope": str(ROOT / "reports" / "generated" / "nonexistent_xyz.json")}
        result = run_source_health_check(paths, [], _cfg())
        assert result.missing_count >= 1

    def test_with_real_reports(self):
        paths = {}
        for f in ["campaign_state_snapshot.json", "ev_ranking_preview.json"]:
            p = RP / f
            if p.exists():
                paths[f] = str(p)
        if paths:
            result = run_source_health_check(paths, [], _cfg())
            assert result.available_count >= 1


class TestCircuitBreaker:
    def test_clean_passes(self):
        sh = SourceHealthSummary(source_count=3, available_count=3, valid_count=3)
        result = run_circuit_breaker(sh, {}, {}, {}, _cfg())
        assert result.overall_status == "PASS"

    def test_hard_block_forbidden(self):
        sh = SourceHealthSummary(source_count=1, blocked_count=1)
        item = type("x", (), {"source_name": "t", "status": "blocked",
                "notes": ['forbidden_fields: ["stake"]']})()
        sh.items = [item]
        result = run_circuit_breaker(sh, {}, {}, {}, _cfg())
        assert result.overall_status == "BLOCKED"

    def test_score_out_of_range(self):
        sh = SourceHealthSummary(source_count=1, available_count=1)
        sf = {"fusion_summary": {"candidates": [
            {"candidate_id": "c1", "base_campaign_score": -0.5}
        ], "candidate_count": 1}}
        result = run_circuit_breaker(sh, sf, {}, {}, _cfg())
        assert result.overall_status == "BLOCKED"

    def test_no_forbidden_in_result(self):
        sh = SourceHealthSummary(source_count=1)
        result = run_circuit_breaker(sh, {}, {}, {}, _cfg())
        js = json.dumps(_d(result))
        for fb in FORBIDDEN_FIELDS:
            assert fb not in js


class TestReviewQueue:
    def test_builds(self):
        sh = SourceHealthSummary(source_count=2, available_count=1, missing_count=1)
        cb = CircuitBreakerResult(warning_count=1, warnings=["test"])
        rq = build_review_queue(sh, cb, {}, _cfg())
        assert rq.review_item_count >= 1


class TestQualityGate:
    def test_all_pass(self):
        sh = SourceHealthSummary(source_count=3, available_count=3, valid_count=3)
        cb = CircuitBreakerResult(overall_status="PASS")
        qg = build_quality_gate(sh, cb, ReviewQueue())
        assert qg.status == "PASS"

    def test_block(self):
        sh = SourceHealthSummary(source_count=1, blocked_count=1)
        cb = CircuitBreakerResult(overall_status="BLOCKED", hard_block_count=1)
        qg = build_quality_gate(sh, cb, ReviewQueue())
        assert qg.block_count >= 1


class TestWatchdogRunner:
    def test_2026_06_11(self):
        p = WatchdogRunner(CONFIG_PATH).run("2026-06-11", 100.0, "full")
        assert p.current_date == "2026-06-11"

    def test_2026_06_24(self):
        p = WatchdogRunner(CONFIG_PATH).run("2026-06-24", 100.0, "full")
        assert p.current_date == "2026-06-24"

    def test_2026_07_19(self):
        p = WatchdogRunner(CONFIG_PATH).run("2026-07-19", 100.0, "full")
        assert p.current_date == "2026-07-19"

    def test_bankroll_5000(self):
        p = WatchdogRunner(CONFIG_PATH).run("2026-06-11", 5000.0, "full")
        assert p.current_bankroll == 5000.0

    def test_pre_mode(self):
        p = WatchdogRunner(CONFIG_PATH).run("2026-06-11", 100.0, "pre_daily_ops")
        assert p.mode == "pre_daily_ops"

    def test_post_mode(self):
        p = WatchdogRunner(CONFIG_PATH).run("2026-06-11", 100.0, "post_daily_ops")
        assert p.mode == "post_daily_ops"

    def test_source_health(self):
        p = WatchdogRunner(CONFIG_PATH).run("2026-06-11", 100.0, "full")
        assert "source_count" in p.source_health
        assert "overall_status" in p.source_health

    def test_circuit_breaker(self):
        p = WatchdogRunner(CONFIG_PATH).run("2026-06-11", 100.0, "full")
        assert "overall_status" in p.circuit_breaker
        assert "allowed_to_continue" in p.circuit_breaker

    def test_review_queue(self):
        p = WatchdogRunner(CONFIG_PATH).run("2026-06-11", 100.0, "full")
        assert "review_item_count" in p.review_queue

    def test_quality_gate(self):
        p = WatchdogRunner(CONFIG_PATH).run("2026-06-11", 100.0, "full")
        assert "status" in p.quality_gate
        assert "categories" in p.quality_gate

    def test_generates_json(self):
        WatchdogRunner(CONFIG_PATH).run("2026-06-11", 100.0, "full")
        assert (RP / "daily_ops_watchdog.json").exists()

    def test_generates_md(self):
        WatchdogRunner(CONFIG_PATH).run("2026-06-11", 100.0, "full")
        assert (RP / "daily_ops_watchdog.md").exists()

    def test_no_stake(self):
        p = WatchdogRunner(CONFIG_PATH).run("2026-06-11", 100.0, "full")
        js = json.dumps(_d(p))
        for fb in FORBIDDEN_FIELDS:
            assert fb not in js
        for fb in ["wallet_address", "private_key", "api_secret", "signed_order",
                    "submit_order", "real_money_balance", "guaranteed_profit"]:
            assert fb not in js

    def test_not_betting(self):
        p = WatchdogRunner(CONFIG_PATH).run("2026-06-11", 100.0, "full")
        assert p.not_betting_advice is True
        assert p.analysis_only is True
        assert p.simulation_only is True

    def test_safety_flags(self):
        p = WatchdogRunner(CONFIG_PATH).run("2026-06-11", 100.0, "full")
        s = p.safety
        assert s["real_bet_execution"] is False
        assert s["auto_betting"] is False
        assert s["network_fetch_default_enabled"] is False
