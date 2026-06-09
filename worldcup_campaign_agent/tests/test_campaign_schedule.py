"""Tests for campaign_schedule module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.campaign_schedule import CampaignScheduleBuilder, DailySchedule

ROOT = Path(__file__).resolve().parent.parent
SC_CONFIG = str(ROOT / "config" / "campaign_schedule_config.json")
STAGE_MAP = str(ROOT / "config" / "worldcup_stage_map.json")
MATCHES = str(ROOT / "data" / "seed" / "worldcup_2026_match_registry.json")

@pytest.fixture
def builder():
    return CampaignScheduleBuilder(SC_CONFIG, STAGE_MAP, MATCHES)

def test_full_timeline_has_50_days(builder):
    timeline = builder.build_full_timeline()
    assert len(timeline) == 50

def test_timeline_has_matchdays(builder):
    timeline = builder.build_full_timeline()
    matchdays = [s for s in timeline if s.is_matchday]
    assert len(matchdays) > 20

def test_timeline_has_non_matchdays(builder):
    timeline = builder.build_full_timeline()
    non = [s for s in timeline if not s.is_matchday]
    assert len(non) > 0

def test_today_schedule_2026_06_11(builder):
    schedule = builder.build_today_schedule("2026-06-11")
    assert schedule.date == "2026-06-11"
    assert schedule.match_count >= 0
    assert schedule.daily_mode in ["matchday", "pre_matchday", "rest_day", "post_matchday", "post_tournament"]

def test_today_has_recommended_modules(builder):
    schedule = builder.build_today_schedule("2026-06-11")
    assert len(schedule.recommended_modules) > 0

def test_today_has_bucket_focus(builder):
    schedule = builder.build_today_schedule("2026-06-11")
    assert isinstance(schedule.bucket_focus, list)

def test_schedule_has_safety_flags(builder):
    schedule = builder.build_today_schedule("2026-06-11")
    assert schedule.analysis_only is True
    assert schedule.simulation_only is True
    assert schedule.not_betting_advice is True

def test_upcoming_schedule(builder):
    timeline = builder.build_full_timeline()
    upcoming = builder.get_upcoming_schedule(timeline, 7)
    assert len(upcoming) <= 7

def test_parlay_min_candidates(builder):
    # 06-11 has 4 matches < 6 parlay_min, so parlay should be disabled
    schedule = builder.build_today_schedule("2026-06-11")
    if schedule.parlay_enabled:
        assert schedule.match_count >= 6

def test_futures_enabled_during_group_stage(builder):
    schedule = builder.build_today_schedule("2026-06-11")
    assert schedule.futures_enabled is True

def test_no_stake_fields(builder):
    schedule = builder.build_today_schedule("2026-06-11")
    d = schedule.__dict__
    assert "stake" not in d
    assert "bet_instruction" not in d
    assert "bookmaker" not in d
