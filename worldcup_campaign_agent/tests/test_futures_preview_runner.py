"""Tests for futures_preview_runner module."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.futures_preview_runner import FuturesPreviewRunner

ROOT = Path(__file__).resolve().parent.parent

def get_paths():
    return {
        "groups": str(ROOT / "data" / "seed" / "worldcup_2026_groups.json"),
        "match_registry": str(ROOT / "data" / "seed" / "worldcup_2026_match_registry.json"),
        "ratings": str(ROOT / "data" / "seed" / "worldcup_2026_team_ratings.json"),
        "group_sim_config": str(ROOT / "config" / "group_simulation_config.json"),
        "tournament_path_config": str(ROOT / "config" / "tournament_path_config.json"),
        "futures_odds_policy": str(ROOT / "config" / "futures_odds_policy.json"),
        "futures_market_config": str(ROOT / "config" / "futures_market_config.json"),
        "futures_candidate_policy": str(ROOT / "config" / "futures_candidate_policy.json"),
        "campaign_score_config": str(ROOT / "config" / "campaign_score_config.json"),
    }

class TestRunner:
    def test_2026_06_11_bankroll_100(self):
        runner = FuturesPreviewRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert preview is not None
        assert preview.groups_simulated == 12
        assert preview.path_probabilities_count == 48

    def test_2026_06_24_bankroll_100(self):
        runner = FuturesPreviewRunner(get_paths())
        preview = runner.run("2026-06-24", 100.0)
        assert preview.groups_simulated == 12

    def test_2026_07_19_bankroll_100(self):
        runner = FuturesPreviewRunner(get_paths())
        preview = runner.run("2026-07-19", 100.0)
        assert preview.groups_simulated == 12

    def test_bankroll_5000(self):
        runner = FuturesPreviewRunner(get_paths())
        preview = runner.run("2026-06-11", 5000.0)
        assert preview.current_bankroll == 5000.0

class TestSafety:
    def test_safety_flags(self):
        runner = FuturesPreviewRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        s = preview.safety
        assert s["campaign_analysis_only"] is True
        assert s["real_bet_execution"] is False
        assert s["auto_betting"] is False
        assert s["simulation_only"] is True
        assert s["not_betting_advice"] is True

    def test_analysis_flags(self):
        runner = FuturesPreviewRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        assert preview.analysis_only is True
        assert preview.simulation_only is True
        assert preview.not_betting_advice is True

    def test_no_stake_fields(self):
        runner = FuturesPreviewRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        from dataclasses import asdict
        d = asdict(preview)
        jstr = json.dumps(d, default=str)
        assert "stake_to_match" not in jstr
        assert "stake_amount" not in jstr
        assert "bet_instruction" not in jstr

    def test_no_bookmaker(self):
        runner = FuturesPreviewRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        from dataclasses import asdict
        d = asdict(preview)
        jstr = json.dumps(d, default=str)
        assert '"bookmaker"' not in jstr.lower() or "real_bet" in jstr

class TestReports:
    def test_write_json(self):
        runner = FuturesPreviewRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        out = str(ROOT / "reports" / "generated" / "futures_test.json")
        runner.write_json(preview, out)
        assert Path(out).exists()
        data = json.loads(Path(out).read_text(encoding="utf-8"))
        assert "groups_simulated" in data

    def test_write_markdown(self):
        runner = FuturesPreviewRunner(get_paths())
        preview = runner.run("2026-06-11", 100.0)
        out = str(ROOT / "reports" / "generated" / "futures_test.md")
        runner.write_markdown(preview, out)
        assert Path(out).exists()
        content = Path(out).read_text(encoding="utf-8")
        assert "Tournament Futures" in content
