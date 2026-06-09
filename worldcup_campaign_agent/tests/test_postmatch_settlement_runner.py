"""Tests for postmatch_settlement_runner module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.postmatch_settlement_runner import PostmatchSettlementRunner

ROOT = Path(__file__).resolve().parent.parent

def get_paths():
    return {
        "policy": str(ROOT / "config" / "campaign_policy.json"),
        "states": str(ROOT / "config" / "bankroll_states.json"),
        "stage_map": str(ROOT / "config" / "worldcup_stage_map.json"),
        "match_registry": str(ROOT / "data" / "seed" / "worldcup_2026_match_registry.json"),
        "strategy_rules": str(ROOT / "config" / "daily_strategy_rules.json"),
        "tagging_rules": str(ROOT / "config" / "match_tagging_rules.json"),
        "scenario_rules": str(ROOT / "config" / "scenario_rules.json"),
        "ratings": str(ROOT / "data" / "seed" / "worldcup_2026_team_ratings.json"),
        "prob_config": str(ROOT / "config" / "probability_model_config.json"),
        "sanity_config": str(ROOT / "config" / "probability_sanity_config.json"),
        "odds_policy": str(ROOT / "config" / "odds_snapshot_policy.json"),
        "ev_config": str(ROOT / "config" / "ev_ranking_config.json"),
        "score_config": str(ROOT / "config" / "campaign_score_config.json"),
        "bucket_policy": str(ROOT / "config" / "bucket_candidate_policy.json"),
        "integration_config": str(ROOT / "config" / "daily_candidate_integration_config.json"),
        "market_registry": str(ROOT / "config" / "market_universe.json"),
        "settlement_config": str(ROOT / "config" / "postmatch_settlement_config.json"),
        "settlement_rules": str(ROOT / "config" / "settlement_rules.json"),
    }

def test_runner_2026_06_11():
    runner = PostmatchSettlementRunner(get_paths())
    preview = runner.run("2026-06-11", 100.0)
    assert preview.date == "2026-06-11"
    assert preview.ledger_entries_count > 0

def test_runner_2026_06_24():
    runner = PostmatchSettlementRunner(get_paths())
    preview = runner.run("2026-06-24", 100.0)
    assert preview.date == "2026-06-24"

def test_runner_2026_07_19():
    runner = PostmatchSettlementRunner(get_paths())
    preview = runner.run("2026-07-19", 100.0)
    assert preview.date == "2026-07-19"

def test_runner_bankroll_5000():
    runner = PostmatchSettlementRunner(get_paths())
    preview = runner.run("2026-06-11", 5000.0)
    assert preview.simulated_bankroll_before == 5000.0

def test_runner_with_manual_results():
    runner = PostmatchSettlementRunner(get_paths())
    seed = str(ROOT / "data" / "seed" / "manual_result_seed.json")
    preview = runner.run("2026-06-11", 100.0, seed)
    assert preview is not None

def test_safety_flags():
    runner = PostmatchSettlementRunner(get_paths())
    preview = runner.run("2026-06-11", 100.0)
    s = preview.safety
    assert s["campaign_analysis_only"] is True
    assert s["real_bet_execution"] is False
    assert s["no_real_money"] is True

def test_no_stake_fields():
    runner = PostmatchSettlementRunner(get_paths())
    preview = runner.run("2026-06-11", 100.0)
    from dataclasses import asdict
    d = asdict(preview)
    jstr = json.dumps(d, default=str)
    assert "stake_to_match" not in jstr
    assert "stake_amount" not in jstr
    assert "bet_instruction" not in jstr
    assert "bookmaker" not in jstr.lower()

def test_no_real_money_balance():
    runner = PostmatchSettlementRunner(get_paths())
    preview = runner.run("2026-06-11", 100.0)
    from dataclasses import asdict
    d = asdict(preview)
    jstr = json.dumps(d, default=str)
    assert "real_money_balance" not in jstr

def test_routing_hint_present():
    runner = PostmatchSettlementRunner(get_paths())
    preview = runner.run("2026-06-11", 100.0)
    assert len(preview.next_day_routing_hint) > 0

def test_campaign_snapshot_generated():
    runner = PostmatchSettlementRunner(get_paths())
    preview = runner.run("2026-06-11", 100.0)
    assert preview.campaign_snapshot is not None
    assert "simulated_bankroll" in preview.campaign_snapshot

def test_reports(tmp_path):
    runner = PostmatchSettlementRunner(get_paths())
    preview = runner.run("2026-06-11", 100.0)
    jp = str(tmp_path / "settlement.json")
    mp = str(tmp_path / "settlement.md")
    runner.write_json(preview, jp)
    runner.write_markdown(preview, mp)
    assert Path(jp).exists()
    assert Path(mp).exists()
