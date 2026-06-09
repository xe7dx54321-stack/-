"""Tests for daily_brief_builder module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.dashboard_loader import DashboardLoader
from worldcup_campaign.dashboard_builder import DashboardBuilder
from worldcup_campaign.daily_brief_builder import DailyBriefBuilder

ROOT = Path(__file__).resolve().parent.parent
REPORTS = str(ROOT / "reports" / "generated")
DC = str(ROOT / "config" / "dashboard_config.json")
BC = str(ROOT / "config" / "daily_brief_config.json")

@pytest.fixture
def brief():
    loader = DashboardLoader()
    sources = loader.load_all(REPORTS)
    builder = DashboardBuilder(DC)
    dashboard = builder.build("2026-06-11", 100.0, sources)
    bb = DailyBriefBuilder(BC)
    return bb.build(dashboard)

def test_brief_created(brief):
    assert brief.date == "2026-06-11"

def test_boss_summary(brief):
    assert len(brief.boss_summary) > 0

def test_boss_summary_not_exceed_8(brief):
    assert len(brief.boss_summary) <= 8

def test_brief_is_chinese(brief):
    text = str(brief.boss_summary)
    assert any('一' <= c <= '鿿' for c in text)

def test_has_researcher_detail(brief):
    assert brief.researcher_detail is not None
    assert len(brief.researcher_detail) > 0

def test_has_bucket_brief(brief):
    assert brief.bucket_brief is not None

def test_has_parlay_brief(brief):
    assert brief.parlay_brief is not None

def test_has_futures_brief(brief):
    assert brief.futures_brief is not None

def test_has_settlement_brief(brief):
    assert brief.settlement_brief is not None

def test_has_warnings(brief):
    assert isinstance(brief.warnings, list)

def test_has_safety_note(brief):
    assert len(brief.safety_note) > 0

def test_no_forbidden_phrases(brief):
    text = str(brief.boss_summary) + brief.safety_note
    forbidden = ["稳赚", "保证盈利", "必须下注"]
    for f in forbidden:
        assert f not in text, f"Found forbidden phrase: {f}"

def test_no_bet_instruction(brief):
    from dataclasses import asdict
    jstr = str(asdict(brief))
    assert "bet_instruction" not in jstr

def test_render_markdown(brief):
    bb = DailyBriefBuilder(BC)
    md = bb.render_markdown(brief)
    assert "老板摘要" in md
    assert "Safety Note" in md
