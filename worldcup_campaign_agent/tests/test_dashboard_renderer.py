"""Tests for dashboard_renderer module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.dashboard_loader import DashboardLoader
from worldcup_campaign.dashboard_builder import DashboardBuilder
from worldcup_campaign.daily_brief_builder import DailyBriefBuilder
from worldcup_campaign.dashboard_renderer import DashboardRenderer

ROOT = Path(__file__).resolve().parent.parent
REPORTS = str(ROOT / "reports" / "generated")
DC = str(ROOT / "config" / "dashboard_config.json")
BC = str(ROOT / "config" / "daily_brief_config.json")

@pytest.fixture
def rendered(tmp_path):
    loader = DashboardLoader()
    sources = loader.load_all(REPORTS)
    builder = DashboardBuilder(DC)
    dashboard = builder.build("2026-06-11", 100.0, sources)
    bb = DailyBriefBuilder(BC)
    brief = bb.build(dashboard)
    renderer = DashboardRenderer()
    return renderer, dashboard, brief, tmp_path

def test_render_json(rendered):
    renderer, dashboard, brief, _ = rendered
    data = renderer.render_json(dashboard)
    assert "bankroll_summary" in data

def test_render_markdown(rendered):
    renderer, dashboard, brief, _ = rendered
    md = renderer.render_markdown(dashboard, brief)
    assert "Campaign Dashboard" in md

def test_render_html(rendered):
    renderer, dashboard, brief, _ = rendered
    html = renderer.render_html(dashboard, brief)
    assert "<!DOCTYPE html>" in html
    assert "</html>" in html

def test_html_no_external_js(rendered):
    renderer, dashboard, brief, _ = rendered
    html = renderer.render_html(dashboard, brief)
    assert "cdn." not in html.lower() or "src=" not in html.lower().replace("charset", "")

def test_write_outputs(rendered):
    renderer, dashboard, brief, tmp = rendered
    paths = renderer.write_outputs(dashboard, brief, str(tmp))
    assert Path(paths["json"]).exists()
    assert Path(paths["md"]).exists()
    assert Path(paths["html"]).exists()

def test_forbidden_field_blocks(rendered):
    renderer, dashboard, brief, _ = rendered
    from dataclasses import asdict
    d = asdict(dashboard)
    d["stake"] = 100  # Add forbidden field
    with pytest.raises(ValueError):
        renderer.validate_no_forbidden(d)

def test_no_bookmaker_in_html(rendered):
    renderer, dashboard, brief, _ = rendered
    html = renderer.render_html(dashboard, brief)
    assert "bookmaker_account" not in html

def test_no_real_money_in_html(rendered):
    renderer, dashboard, brief, _ = rendered
    html = renderer.render_html(dashboard, brief)
    assert "real_money_balance" not in html
