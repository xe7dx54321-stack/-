"""Tests for operator_checklist module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.operator_checklist import OperatorChecklistBuilder, OperatorChecklist
from worldcup_campaign.campaign_schedule import CampaignScheduleBuilder

ROOT = Path(__file__).resolve().parent.parent
RULES = str(ROOT / "config" / "daily_execution_rules.json")
SC_CONFIG = str(ROOT / "config" / "campaign_schedule_config.json")
STAGE_MAP = str(ROOT / "config" / "worldcup_stage_map.json")
MATCHES = str(ROOT / "data" / "seed" / "worldcup_2026_match_registry.json")

def test_checklist_builds():
    builder = CampaignScheduleBuilder(SC_CONFIG, STAGE_MAP, MATCHES)
    schedule = builder.build_today_schedule("2026-06-11")
    oc = OperatorChecklistBuilder(RULES)
    checklist = oc.build(schedule)
    assert checklist.date == "2026-06-11"
    assert len(checklist.items) > 0

def test_checklist_has_pre_run_items():
    builder = CampaignScheduleBuilder(SC_CONFIG, STAGE_MAP, MATCHES)
    schedule = builder.build_today_schedule("2026-06-11")
    oc = OperatorChecklistBuilder(RULES)
    checklist = oc.build(schedule)
    pre = [i for i in checklist.items if i.phase == "pre_run"]
    assert len(pre) > 0

def test_checklist_has_during_run_items():
    builder = CampaignScheduleBuilder(SC_CONFIG, STAGE_MAP, MATCHES)
    schedule = builder.build_today_schedule("2026-06-11")
    oc = OperatorChecklistBuilder(RULES)
    checklist = oc.build(schedule)
    during = [i for i in checklist.items if i.phase == "during_run"]
    assert len(during) > 0

def test_checklist_has_post_run_items():
    builder = CampaignScheduleBuilder(SC_CONFIG, STAGE_MAP, MATCHES)
    schedule = builder.build_today_schedule("2026-06-11")
    oc = OperatorChecklistBuilder(RULES)
    checklist = oc.build(schedule)
    post = [i for i in checklist.items if i.phase == "post_run"]
    assert len(post) > 0

def test_checklist_not_betting_advice():
    builder = CampaignScheduleBuilder(SC_CONFIG, STAGE_MAP, MATCHES)
    schedule = builder.build_today_schedule("2026-06-11")
    oc = OperatorChecklistBuilder(RULES)
    checklist = oc.build(schedule)
    assert checklist.not_betting_advice is True

def test_forbidden_actions_include_place_bet():
    oc = OperatorChecklistBuilder(RULES)
    forbidden = oc.get_forbidden_actions()
    assert "place_bet" in forbidden

def test_allowed_actions_do_not_include_betting():
    oc = OperatorChecklistBuilder(RULES)
    allowed = oc.get_allowed_actions()
    assert "place_bet" not in allowed
    assert "run_analysis" in allowed

def test_checklist_no_bet_instructions(builder=None):
    builder = CampaignScheduleBuilder(SC_CONFIG, STAGE_MAP, MATCHES)
    schedule = builder.build_today_schedule("2026-06-11")
    oc = OperatorChecklistBuilder(RULES)
    checklist = oc.build(schedule)
    for item in checklist.items:
        assert "bet" not in item.action.lower() or "not_betting" in item.action.lower()
