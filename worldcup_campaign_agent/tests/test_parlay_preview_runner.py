"""Tests for parlay_preview_runner module."""
import sys, json, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from worldcup_campaign.parlay_preview_runner import ParlayPreviewRunner, ParlayPreview

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
        "parlay_optimizer_config": str(ROOT / "config" / "parlay_optimizer_config.json"),
        "parlay_correlation_policy": str(ROOT / "config" / "parlay_correlation_policy.json"),
        "parlay_bucket_policy": str(ROOT / "config" / "parlay_bucket_policy.json"),
    }


class TestRunnerExecution:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.paths = get_paths()
        self.runner = ParlayPreviewRunner(self.paths)

    def test_runner_2026_06_11_bankroll_100(self):
        preview = self.runner.run("2026-06-11", 100.0)
        assert preview is not None
        assert preview.current_date == "2026-06-11"
        assert preview.current_bankroll == 100.0
        assert preview.source_candidate_count >= 0
        assert preview.raw_combination_count >= 0
        assert preview.ranked_parlay_count >= 0

    def test_runner_2026_06_24_bankroll_100(self):
        preview = self.runner.run("2026-06-24", 100.0)
        assert preview is not None
        assert preview.current_date == "2026-06-24"

    def test_runner_2026_07_19_bankroll_100(self):
        preview = self.runner.run("2026-07-19", 100.0)
        assert preview is not None
        assert preview.current_date == "2026-07-19"

    def test_runner_bankroll_5000(self):
        preview = self.runner.run("2026-06-11", 5000.0)
        assert preview is not None
        assert preview.current_bankroll == 5000.0

    def test_safety_flags(self):
        preview = self.runner.run("2026-06-11", 100.0)
        safety = preview.safety
        assert safety["campaign_analysis_only"] is True
        assert safety["real_bet_execution"] is False
        assert safety["auto_betting"] is False
        assert safety["external_betting_api_allowed"] is False
        assert safety["simulation_only"] is True
        assert safety["not_betting_advice"] is True

    def test_analysis_flags(self):
        preview = self.runner.run("2026-06-11", 100.0)
        assert preview.analysis_only is True
        assert preview.simulation_only is True
        assert preview.not_betting_advice is True


class TestReportGeneration:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.paths = get_paths()
        self.runner = ParlayPreviewRunner(self.paths)
        self.preview = self.runner.run("2026-06-11", 100.0)
        self.out_dir = ROOT / "reports" / "generated"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def test_write_json_creates_file(self):
        json_path = str(self.out_dir / "parlay_preview_test.json")
        self.runner.write_json(self.preview, json_path)
        assert Path(json_path).exists()
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
        assert "current_date" in data
        assert "safety" in data

    def test_write_markdown_creates_file(self):
        md_path = str(self.out_dir / "parlay_preview_test.md")
        self.runner.write_markdown(self.preview, md_path)
        assert Path(md_path).exists()
        content = Path(md_path).read_text(encoding="utf-8")
        assert "Parlay Optimizer Preview" in content


class TestSafetyOutputFields:
    def test_json_no_stake_to_match(self):
        paths = get_paths()
        runner = ParlayPreviewRunner(paths)
        preview = runner.run("2026-06-11", 100.0)
        from dataclasses import asdict
        d = asdict(preview)
        assert "stake_to_match" not in json.dumps(d, default=str)
        assert "stake_amount" not in json.dumps(d, default=str)
        assert "bet_instruction" not in json.dumps(d, default=str)

    def test_json_no_bookmaker(self):
        paths = get_paths()
        runner = ParlayPreviewRunner(paths)
        preview = runner.run("2026-06-11", 100.0)
        from dataclasses import asdict
        d = asdict(preview)
        jstr = json.dumps(d, default=str)
        assert "bookmaker" not in jstr.lower() or "not_betting" in jstr

    def test_no_real_bet_execution_true(self):
        paths = get_paths()
        runner = ParlayPreviewRunner(paths)
        preview = runner.run("2026-06-11", 100.0)
        from dataclasses import asdict
        d = asdict(preview)
        jstr = json.dumps(d, default=str)
        assert '"real_bet_execution": true' not in jstr


class TestRegressionCommands:
    def test_round1_foundation(self):
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/test_policy.py", "tests/test_bankroll_state.py",
             "tests/test_market_registry.py", "tests/test_odds_math.py", "tests/test_target_math.py",
             "tests/test_runner_foundation.py", "-q", "--tb=no"],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        assert result.returncode == 0, f"R1 tests failed: {result.stderr}"
