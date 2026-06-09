"""Tests for match probability runner."""
import json, tempfile
from pathlib import Path
import pytest
from worldcup_campaign.match_probability_runner import MatchProbabilityRunner

def _cfg(f): return str(Path(__file__).resolve().parent.parent/"config"/f)
def _data(f): return str(Path(__file__).resolve().parent.parent/"data"/"seed"/f)

class TestMatchProbabilityRunner:
    @pytest.fixture
    def runner(self):
        return MatchProbabilityRunner(
            ratings_path=_data("worldcup_2026_team_ratings.json"),
            prob_config_path=_cfg("probability_model_config.json"),
            match_registry_path=_data("worldcup_2026_match_registry.json"),
            policy_path=_cfg("campaign_policy.json"),
        )
    def test_run_for_date_opens(self, runner):
        p = runner.run_for_date("2026-06-11")
        assert p.matches_count == 4
        assert p.is_dry_run is True
    def test_run_for_date_group_r3(self, runner):
        p = runner.run_for_date("2026-06-24")
        assert p.matches_count == 6
    def test_run_for_date_final(self, runner):
        p = runner.run_for_date("2026-07-19")
        assert p.matches_count == 1
    def test_run_for_match_id(self, runner):
        p = runner.run_for_match_id("GS_A_R1_001")
        assert p.matches_count == 1
        m = p.matches[0]
        assert m["match_id"] == "GS_A_R1_001"
    def test_probs_sum_to_1(self, runner):
        p = runner.run_for_date("2026-06-11")
        for m in p.matches:
            s = m["home_win_prob"] + m["draw_prob"] + m["away_win_prob"]
            assert abs(s - 1.0) < 0.01
    def test_expected_goals_reasonable(self, runner):
        p = runner.run_for_date("2026-06-11")
        for m in p.matches:
            assert 0.3 <= m["expected_goals_home"] <= 5.0
            assert 0.3 <= m["expected_goals_away"] <= 5.0
    def test_confidence_present(self, runner):
        p = runner.run_for_date("2026-06-11")
        for m in p.matches:
            assert "confidence" in m
            assert 0.0 <= m["confidence"] <= 1.0
    def test_scorelines_present(self, runner):
        p = runner.run_for_date("2026-06-11")
        for m in p.matches:
            assert len(m.get("top_scorelines", [])) > 0
    def test_over_under_present(self, runner):
        p = runner.run_for_date("2026-06-11")
        for m in p.matches:
            assert len(m.get("over_under", [])) == 5
    def test_no_odds_no_stake(self, runner):
        """Must not output odds, stake, bet instructions."""
        p = runner.run_for_date("2026-06-11")
        d = p.__dict__ if hasattr(p, '__dict__') else {}
        for forbidden in ["odds", "stake", "bet_instruction", "bookmaker", "guaranteed"]:
            for key in d:
                assert forbidden not in str(key).lower()
    def test_safety_flags(self, runner):
        p = runner.run_for_date("2026-06-11")
        assert p.safety["campaign_analysis_only"] is True
        assert p.safety["real_bet_execution"] is False
    def test_write_json(self, runner):
        with tempfile.TemporaryDirectory() as tmp:
            p = runner.run_for_date("2026-06-11")
            path = Path(tmp)/"test.json"
            runner.write_json(p, str(path))
            assert path.exists()
            data = json.loads(path.read_text())
            assert data["matches_count"] == 4
    def test_write_markdown(self, runner):
        with tempfile.TemporaryDirectory() as tmp:
            p = runner.run_for_date("2026-06-24")
            path = Path(tmp)/"test.md"
            runner.write_markdown(p, str(path))
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "Match Probability Preview" in content
    def test_unknown_match_id_fails(self, runner):
        with pytest.raises(ValueError):
            runner.run_for_match_id("NONEXISTENT")