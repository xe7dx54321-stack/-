"""Tests for Full Campaign Dry-Run."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.full_campaign_dry_run import (
    build_full_campaign_timeline, classify_dry_run_day,
    run_dry_run_day, DryRunDay, DryRunDayResult,
    calculate_bankroll_update, classify_bankroll_state,
    build_bankroll_state_history, DryRunStateHistory,
    summarize_dry_run_settlement, DryRunSettlementSummary,
    aggregate_dry_run_reviews, DryRunReviewSummary,
    build_artifact_manifest, DryRunArtifactManifest,
    FullCampaignDryRunRunner, FullCampaignDryRunResult,
    render_dry_run_json, render_dry_run_markdown,
    write_dry_run_outputs, validate_no_forbidden,
    _d, FORBIDDEN
)

ROOT = Path(__file__).resolve().parent.parent


class TestTimeline:
    def test_build_timeline_from_seed(self):
        tl = build_full_campaign_timeline("2026-06-11", "2026-07-19", {})
        assert tl.day_count == 39
        assert tl.matchday_count > 0
        assert tl.campaign_start_date == "2026-06-11"
        assert tl.campaign_end_date == "2026-07-19"

    def test_timeline_days_have_dates(self):
        tl = build_full_campaign_timeline("2026-06-11", "2026-07-19", {})
        assert len(tl.days) == 39
        assert tl.days[0].date == "2026-06-11"
        assert tl.days[-1].date == "2026-07-19"

    def test_classify_matchday(self):
        day = DryRunDay(date="2026-06-11", day_type="matchday")
        policy = classify_dry_run_day(day, {"matchday_policy":"run_full_daily_ops"})
        assert policy == "run_full_daily_ops"

    def test_classify_rest_day(self):
        day = DryRunDay(date="2026-06-13", day_type="rest_day")
        policy = classify_dry_run_day(day, {"rest_day_policy":"run_light_watchdog_only"})
        assert policy == "run_light_watchdog_only"


class TestDayRunner:
    def test_run_matchday(self):
        day = DryRunDay(date="2026-06-11", day_type="matchday", match_count=4, stage="group_stage")
        result = run_dry_run_day(day, 100.0, {}, {})
        assert result.date == "2026-06-11"
        assert result.day_type == "matchday"
        assert result.daily_ops_status == "SUCCESS"
        assert result.watchdog_status in ("PASS", "WARN")
        assert result.day_status in ("SUCCESS", "WARN")
        assert result.ending_bankroll_preview > 100.0
        assert result.review_item_count > 0

    def test_run_rest_day(self):
        day = DryRunDay(date="2026-06-13", day_type="rest_day", match_count=0)
        result = run_dry_run_day(day, 100.0, {}, {})
        assert result.day_status == "SUCCESS"
        assert result.daily_ops_status == "SKIPPED"
        assert result.ending_bankroll_preview == 100.0
        assert result.review_item_count == 0

    def test_bankroll_positive_for_rest_day(self):
        day = DryRunDay(date="2026-06-13", day_type="rest_day", match_count=0)
        result = run_dry_run_day(day, 50.0, {}, {})
        assert result.ending_bankroll_preview == 50.0

    def test_high_match_count_warn(self):
        day = DryRunDay(date="2026-06-11", day_type="matchday", match_count=8, stage="knockout")
        result = run_dry_run_day(day, 100.0, {}, {})
        assert result.watchdog_status == "WARN"


class TestBankroll:
    def test_classify_s0(self):
        assert classify_bankroll_state(30.0) == "S0"

    def test_classify_s2(self):
        assert classify_bankroll_state(100.0) == "S2"

    def test_classify_target_reached(self):
        assert classify_bankroll_state(1000000.0) == "TARGET_REACHED"

    def test_calculate_update(self):
        settlement = {"matches": [{"requires_review": False, "confidence": 0.9, "auto_outcome_status": "hit"}]}
        u = calculate_bankroll_update(100.0, settlement, {"settlement_confidence_required_for_update": 0.8})
        assert u.settlement_applied_count == 1
        assert u.simulated_profit_loss == 0.5
        assert u.ending_bankroll_preview == 100.5

    def test_state_history(self):
        results = [
            DryRunDayResult(date="2026-06-11", day_type="matchday", starting_bankroll=100.0, ending_bankroll_preview=100.5, day_status="SUCCESS"),
            DryRunDayResult(date="2026-06-12", day_type="matchday", starting_bankroll=100.5, ending_bankroll_preview=101.0, day_status="SUCCESS"),
        ]
        sh = build_bankroll_state_history(results, 100.0, {})
        assert sh.initial_bankroll == 100.0
        assert sh.final_bankroll_preview == 101.0
        assert len(sh.days) == 2


class TestSettlementSummary:
    def test_summarize(self):
        results = [
            DryRunDayResult(date="2026-06-11", day_type="matchday", settlement_status="SUCCESS", review_item_count=5),
            DryRunDayResult(date="2026-06-13", day_type="rest_day", settlement_status="SKIPPED", review_item_count=0),
        ]
        s = summarize_dry_run_settlement(results)
        assert s.total_ledger_entries == 2
        assert s.auto_settled_count == 1


class TestReviewSummary:
    def test_aggregate(self):
        results = [
            DryRunDayResult(date="2026-06-11", day_type="matchday", review_item_count=5, watchdog_status="WARN", package_type="review_required_package", settlement_status="SUCCESS"),
            DryRunDayResult(date="2026-06-13", day_type="rest_day", review_item_count=0, watchdog_status="PASS"),
        ]
        r = aggregate_dry_run_reviews(results)
        assert r.total_review_items == 5
        assert r.watchdog_review_count >= 1


class TestArtifactManifest:
    def test_build(self):
        results = [DryRunDayResult(date="2026-06-11", day_type="matchday")]
        m = build_artifact_manifest(results, {"forbidden_artifact_fields": FORBIDDEN})
        assert m.total_artifacts > 0
        assert isinstance(m.artifacts, list)
        assert m.missing_artifact_count >= 0


class TestRunner:
    def test_runner_creates_result(self):
        runner = FullCampaignDryRunRunner()
        result = runner.run("2026-06-11", "2026-07-19", 100.0)
        assert isinstance(result, FullCampaignDryRunResult)
        assert result.day_count == 39
        assert result.matchday_count > 0
        assert result.completed_day_count >= 0
        assert result.blocked_day_count >= 0
        assert result.warn_day_count >= 0
        assert result.initial_bankroll == 100.0
        assert result.final_bankroll_preview > 100.0

    def test_runner_bankroll_5000(self):
        runner = FullCampaignDryRunRunner()
        result = runner.run("2026-06-11", "2026-07-19", 5000.0)
        assert result.initial_bankroll == 5000.0
        assert result.final_bankroll_preview >= 5000.0

    def test_state_history_exists(self):
        runner = FullCampaignDryRunRunner()
        result = runner.run("2026-06-11", "2026-07-19", 100.0)
        assert result.state_history is not None
        assert len(result.state_history.days) == 39

    def test_settlement_summary_exists(self):
        runner = FullCampaignDryRunRunner()
        result = runner.run("2026-06-11", "2026-07-19", 100.0)
        assert result.settlement_summary is not None

    def test_review_summary_exists(self):
        runner = FullCampaignDryRunRunner()
        result = runner.run("2026-06-11", "2026-07-19", 100.0)
        assert result.review_summary is not None

    def test_artifact_manifest_exists(self):
        runner = FullCampaignDryRunRunner()
        result = runner.run("2026-06-11", "2026-07-19", 100.0)
        assert result.artifact_manifest is not None

    def test_bottleneck_analysis_exists(self):
        runner = FullCampaignDryRunRunner()
        result = runner.run("2026-06-11", "2026-07-19", 100.0)
        assert "total_blocked_days" in result.bottleneck_analysis


class TestRenderer:
    def test_render_json(self):
        runner = FullCampaignDryRunRunner()
        result = runner.run("2026-06-11", "2026-06-13", 100.0)
        d = render_dry_run_json(result)
        assert "campaign_name" in d
        assert d["analysis_only"] == True

    def test_render_markdown(self):
        runner = FullCampaignDryRunRunner()
        result = runner.run("2026-06-11", "2026-06-13", 100.0)
        md = render_dry_run_markdown(result)
        assert "# Full Campaign Dry-Run Report" in md
        assert "Safety Boundary" in md

    def test_write_outputs(self):
        runner = FullCampaignDryRunRunner()
        result = runner.run("2026-06-11", "2026-06-13", 100.0)
        paths = write_dry_run_outputs(result)
        assert "json" in paths
        assert "markdown" in paths
        assert Path(paths["json"]).exists()
        assert Path(paths["markdown"]).exists()


class TestSafety:
    def test_no_forbidden_fields(self):
        runner = FullCampaignDryRunRunner()
        result = runner.run("2026-06-11", "2026-07-19", 100.0)
        forbidden = validate_no_forbidden(result)
        assert len(forbidden) == 0, f"Forbidden fields found: {forbidden}"

    def test_safety_flags(self):
        runner = FullCampaignDryRunRunner()
        result = runner.run("2026-06-11", "2026-07-19", 100.0)
        assert result.analysis_only == True
        assert result.simulation_only == True
        assert result.not_betting_advice == True
        assert result.safety["real_bet_execution"] == False
        assert result.safety["auto_betting"] == False

    def test_no_stake_in_result(self):
        runner = FullCampaignDryRunRunner()
        result = runner.run("2026-06-11", "2026-07-19", 100.0)
        s = json.dumps(_d(result)).lower()
        assert "stake_to_match" not in s
        assert "bookmaker_account" not in s
        assert "real_money_balance" not in s

    def test_bankroll_not_negative(self):
        runner = FullCampaignDryRunRunner()
        result = runner.run("2026-06-11", "2026-07-19", 100.0)
        assert result.final_bankroll_preview >= 0

    def test_markdown_no_bet_instruction(self):
        runner = FullCampaignDryRunRunner()
        result = runner.run("2026-06-11", "2026-06-13", 100.0)
        md = render_dry_run_markdown(result)
        assert "bet_instruction" not in md.lower()
        assert "stake" not in md.lower()
