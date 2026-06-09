"""Tests for daily_execution_planner module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.daily_execution_planner import DailyExecutionPlanner

ROOT = Path(__file__).resolve().parent.parent

@pytest.fixture
def planner():
    return DailyExecutionPlanner(
        str(ROOT / "config" / "campaign_schedule_config.json"),
        str(ROOT / "config" / "daily_execution_rules.json"),
        str(ROOT / "config" / "worldcup_stage_map.json"),
        str(ROOT / "data" / "seed" / "worldcup_2026_match_registry.json"),
    )

def test_plan_day_2026_06_11(planner):
    plan = planner.plan_day("2026-06-11", 100.0)
    assert plan.date == "2026-06-11"
    assert plan.daily_mode in ["matchday", "rest_day"]
    assert len(plan.recommended_modules) > 0

def test_plan_day_has_modules(planner):
    plan = planner.plan_day("2026-06-11", 100.0)
    assert "foundation" in plan.recommended_modules

def test_plan_day_has_checklist(planner):
    plan = planner.plan_day("2026-06-11", 100.0)
    assert len(plan.operator_checklist) > 0

def test_plan_day_bucket_focus(planner):
    plan = planner.plan_day("2026-06-11", 100.0)
    assert isinstance(plan.bucket_focus, list)

def test_plan_day_safety_flags(planner):
    plan = planner.plan_day("2026-06-11", 100.0)
    assert plan.analysis_only is True
    assert plan.simulation_only is True
    assert plan.not_betting_advice is True

def test_path_sanity_warning_for_low_winner_sum(planner):
    plan = planner.plan_day("2026-06-11", 100.0, winner_prob_sum=0.63)
    assert len(plan.path_sanity_warnings) > 0

def test_no_path_sanity_warning_for_high_winner_sum(planner):
    plan = planner.plan_day("2026-06-11", 100.0, winner_prob_sum=0.95)
    assert len(plan.path_sanity_warnings) == 0

def test_parlay_enabled_with_enough_matches(planner):
    plan = planner.plan_day("2026-06-24", 100.0)
    # 06-24 should have 6+ matches
    assert plan.parlay_enabled == (plan.match_count >= 6)

def test_no_stake_in_plan(planner):
    plan = planner.plan_day("2026-06-11", 100.0)
    d = plan.__dict__
    assert "stake" not in d
    assert "bet_instruction" not in d
