"""Tests for foundation runner."""

import json
import tempfile
from pathlib import Path

import pytest

from worldcup_campaign.runner import FoundationRunner, FoundationReport


def _config_path(filename: str) -> str:
    return str(
        Path(__file__).resolve().parent.parent / "config" / filename
    )


class TestFoundationRunner:
    """Tests for the foundation dry-run runner."""

    def test_runner_executes(self):
        """Runner should execute and return a report."""
        runner = FoundationRunner(
            policy_path=_config_path("campaign_policy.json"),
            states_path=_config_path("bankroll_states.json"),
            market_path=_config_path("market_universe.json"),
            current_bankroll=100.0,
            windows_left=40,
        )
        report = runner.run()
        assert isinstance(report, FoundationReport)
        assert report.campaign_name == "worldcup_2026_high_odds_campaign"
        assert report.current_bankroll == 100.0
        assert report.target_bankroll == 1000000.0
        assert report.state == "S2"

    def test_report_has_required_fields(self):
        """Report must contain all required fields."""
        runner = FoundationRunner(
            policy_path=_config_path("campaign_policy.json"),
            states_path=_config_path("bankroll_states.json"),
            market_path=_config_path("market_universe.json"),
            current_bankroll=100.0,
            windows_left=40,
        )
        report = runner.run()
        d = report.__dict__ if hasattr(report, '__dict__') else {}
        from dataclasses import asdict
        d = asdict(report)
        required_keys = [
            "campaign_name", "current_bankroll", "target_bankroll",
            "required_multiplier", "windows_left", "required_growth_per_window",
            "target_urgency", "state", "attack_level", "max_deployable",
            "bucket_amounts", "safety", "market_counts_by_bucket",
        ]
        for key in required_keys:
            assert key in d, f"Missing field: {key}"

    def test_max_deployable_lte_50_percent(self):
        """Max deployable must not exceed 50% of current bankroll."""
        runner = FoundationRunner(
            policy_path=_config_path("campaign_policy.json"),
            states_path=_config_path("bankroll_states.json"),
            market_path=_config_path("market_universe.json"),
            current_bankroll=100.0,
            windows_left=40,
        )
        report = runner.run()
        assert report.max_deployable <= report.current_bankroll * 0.5

    def test_safety_flags_correct(self):
        """All safety flags must be correct."""
        runner = FoundationRunner(
            policy_path=_config_path("campaign_policy.json"),
            states_path=_config_path("bankroll_states.json"),
            market_path=_config_path("market_universe.json"),
            current_bankroll=100.0,
            windows_left=40,
        )
        report = runner.run()
        assert report.safety["campaign_analysis_only"] is True
        assert report.safety["real_bet_execution"] is False
        assert report.safety["auto_betting"] is False
        assert report.safety["external_betting_api_allowed"] is False
        assert report.safety["real_money_instruction_allowed"] is False

    def test_write_json_report(self):
        """JSON report should be written."""
        with tempfile.TemporaryDirectory() as tmp:
            runner = FoundationRunner(
                policy_path=_config_path("campaign_policy.json"),
                states_path=_config_path("bankroll_states.json"),
                market_path=_config_path("market_universe.json"),
                current_bankroll=100.0,
                windows_left=40,
            )
            report = runner.run()
            json_path = Path(tmp) / "test_report.json"
            runner.write_json_report(report, str(json_path))
            assert json_path.exists()
            data = json.loads(json_path.read_text())
            assert data["campaign_name"] == "worldcup_2026_high_odds_campaign"
            assert data["state"] == "S2"
            assert "bucket_amounts" in data
            assert "safety" in data

    def test_write_markdown_report(self):
        """Markdown report should be written."""
        with tempfile.TemporaryDirectory() as tmp:
            runner = FoundationRunner(
                policy_path=_config_path("campaign_policy.json"),
                states_path=_config_path("bankroll_states.json"),
                market_path=_config_path("market_universe.json"),
                current_bankroll=100.0,
                windows_left=40,
            )
            report = runner.run()
            md_path = Path(tmp) / "test_report.md"
            runner.write_markdown_report(report, str(md_path))
            assert md_path.exists()
            content = md_path.read_text()
            assert "# WorldCup Campaign Foundation Preview" in content
            assert "Campaign Policy" in content
            assert "Bankroll State" in content
            assert "Bucket Allocation" in content
            assert "Target Gap" in content
            assert "Market Universe Summary" in content
            assert "Safety Boundary" in content
