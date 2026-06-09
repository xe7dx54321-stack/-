"""Tests for signal_fusion_runner and signal_fusion_engine modules."""
import sys, json, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.signal_fusion_runner import SignalFusionRunner, _d
from worldcup_campaign.signal_fusion_engine import fuse_signals, FusionSummary, FusedCandidate

ROOT = Path(__file__).resolve().parent.parent


def get_paths():
    return {"fusion_config": str(ROOT / "config" / "signal_fusion_config.json")}


class TestFusionEngine:
    """Tests for the core signal_fusion_engine module."""

    def test_fuse_signals_empty(self):
        config = {
            "fusion": {
                "market_support_weight": 0.20,
                "team_context_weight": 0.15,
                "signal_quality_weight": 0.10,
                "max_campaign_score_adjustment": 0.25,
                "min_campaign_score_adjustment": -0.15,
                "promotion_threshold": 0.10,
                "demotion_threshold": -0.05
            }
        }
        result = fuse_signals([], [], [], [], config)
        assert result.candidate_count == 0
        assert result.fused_signal_count == 0
        assert len(result.warnings) >= 1

    def test_fuse_signals_with_candidates(self):
        config = {
            "fusion": {
                "market_support_weight": 0.20,
                "team_context_weight": 0.15,
                "signal_quality_weight": 0.10,
                "max_campaign_score_adjustment": 0.25,
                "min_campaign_score_adjustment": -0.15,
                "promotion_threshold": 0.10,
                "demotion_threshold": -0.05
            }
        }
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.5, "bucket": "edge"},
            {"candidate_id": "c2", "match_id": "M2", "selection_id": "away",
             "market_type": "1x2", "campaign_score": 0.3, "bucket": "attack"},
        ]
        alignment_records = [
            {"key": "M1_home", "alignment_status": "aligned"},
        ]
        context_signals = [
            {"team": "M1", "context_signal": "positive"},
        ]
        quality_scores = [
            {"key": "M1_home", "score": 0.8},
            {"key": "M2_away", "score": 0.2},
        ]
        result = fuse_signals(candidates, alignment_records, context_signals, quality_scores, config)
        assert result.candidate_count == 2
        assert result.fused_signal_count == 2
        assert result.upgraded_candidate_count >= 0

    def test_promoted_candidate(self):
        config = {
            "fusion": {
                "market_support_weight": 0.20,
                "team_context_weight": 0.15,
                "signal_quality_weight": 0.10,
                "max_campaign_score_adjustment": 0.25,
                "min_campaign_score_adjustment": -0.15,
                "promotion_threshold": 0.10,
                "demotion_threshold": -0.05
            }
        }
        candidates = [
            {"candidate_id": "c1", "match_id": "M1_FRA", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.5, "bucket": "edge"},
        ]
        alignment_records = [
            {"key": "M1_FRA_home", "alignment_status": "aligned"},
        ]
        context_signals = [
            {"team": "FRA", "context_signal": "positive"},
        ]
        quality_scores = [
            {"key": "M1_FRA_home", "score": 0.9},
        ]
        result = fuse_signals(candidates, alignment_records, context_signals, quality_scores, config)
        assert result.promoted_count >= 1
        assert result.candidates[0].status == "promoted"
        assert result.candidates[0].score_adjustment > 0

    def test_demoted_candidate(self):
        config = {
            "fusion": {
                "market_support_weight": 0.20,
                "team_context_weight": 0.15,
                "signal_quality_weight": 0.10,
                "max_campaign_score_adjustment": 0.25,
                "min_campaign_score_adjustment": -0.15,
                "promotion_threshold": 0.10,
                "demotion_threshold": -0.05
            }
        }
        candidates = [
            {"candidate_id": "c1", "match_id": "M1_BRA", "selection_id": "draw",
             "market_type": "1x2", "campaign_score": 0.3, "bucket": "core"},
        ]
        alignment_records = [
            {"key": "M1_BRA_draw", "alignment_status": "major_disagreement"},
        ]
        context_signals = []
        quality_scores = [
            {"key": "M1_BRA_draw", "score": 0.5},
        ]
        result = fuse_signals(candidates, alignment_records, context_signals, quality_scores, config)
        assert result.demoted_count >= 1
        assert result.candidates[0].status == "demoted"

    def test_watch_only_low_quality(self):
        config = {
            "fusion": {
                "market_support_weight": 0.20,
                "team_context_weight": 0.15,
                "signal_quality_weight": 0.10,
                "max_campaign_score_adjustment": 0.25,
                "min_campaign_score_adjustment": -0.15,
                "promotion_threshold": 0.10,
                "demotion_threshold": -0.05
            }
        }
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.2, "bucket": "attack"},
        ]
        quality_scores = [
            {"key": "M1_home", "score": 0.1},
        ]
        result = fuse_signals(candidates, [], [], quality_scores, config)
        assert result.watch_only_count >= 1 or result.review_required_count >= 1

    def test_capped_adjustment(self):
        config = {
            "fusion": {
                "market_support_weight": 0.20,
                "team_context_weight": 0.15,
                "signal_quality_weight": 0.10,
                "max_campaign_score_adjustment": 0.25,
                "min_campaign_score_adjustment": -0.15,
                "promotion_threshold": 0.10,
                "demotion_threshold": -0.05
            }
        }
        candidates = [
            {"candidate_id": "c1", "match_id": "M1_FRA", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.9, "bucket": "core"},
        ]
        alignment_records = [
            {"key": "M1_FRA_home", "alignment_status": "aligned"},
        ]
        context_signals = [
            {"team": "FRA", "context_signal": "positive"},
        ]
        quality_scores = [
            {"key": "M1_FRA_home", "score": 1.0},
        ]
        result = fuse_signals(candidates, alignment_records, context_signals, quality_scores, config)
        assert result.candidates[0].score_adjustment <= 0.25

    def test_bucket_upgrade_edge_to_core(self):
        config = {
            "fusion": {
                "market_support_weight": 0.20,
                "team_context_weight": 0.15,
                "signal_quality_weight": 0.10,
                "max_campaign_score_adjustment": 0.25,
                "min_campaign_score_adjustment": -0.15,
                "promotion_threshold": 0.10,
                "demotion_threshold": -0.05
            }
        }
        candidates = [
            {"candidate_id": "c1", "match_id": "M1_FRA", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.5, "bucket": "edge"},
        ]
        alignment_records = [
            {"key": "M1_FRA_home", "alignment_status": "aligned"},
        ]
        context_signals = [
            {"team": "FRA", "context_signal": "positive"},
        ]
        quality_scores = [
            {"key": "M1_FRA_home", "score": 0.9},
        ]
        result = fuse_signals(candidates, alignment_records, context_signals, quality_scores, config)
        assert result.candidates[0].upgraded_bucket == "core"

    def test_bucket_demote_core_to_edge(self):
        config = {
            "fusion": {
                "market_support_weight": 0.20,
                "team_context_weight": 0.15,
                "signal_quality_weight": 0.10,
                "max_campaign_score_adjustment": 0.25,
                "min_campaign_score_adjustment": -0.15,
                "promotion_threshold": 0.10,
                "demotion_threshold": -0.05
            }
        }
        candidates = [
            {"candidate_id": "c1", "match_id": "M1_BRA", "selection_id": "draw",
             "market_type": "1x2", "campaign_score": 0.3, "bucket": "core"},
        ]
        alignment_records = [
            {"key": "M1_BRA_draw", "alignment_status": "major_disagreement"},
        ]
        quality_scores = [
            {"key": "M1_BRA_draw", "score": 0.2},
        ]
        result = fuse_signals(candidates, alignment_records, [], quality_scores, config)
        assert result.candidates[0].upgraded_bucket == "edge"

    def test_no_real_money_fields_in_engine_output(self):
        config = {
            "fusion": {
                "market_support_weight": 0.20,
                "team_context_weight": 0.15,
                "signal_quality_weight": 0.10,
                "max_campaign_score_adjustment": 0.25,
                "min_campaign_score_adjustment": -0.15,
                "promotion_threshold": 0.10,
                "demotion_threshold": -0.05
            }
        }
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.5, "bucket": "edge"},
        ]
        result = fuse_signals(candidates, [], [], [], config)
        js = json.dumps(_d(result))
        for fb in ["stake_to_match", "stake_amount", "bet_instruction",
                    "bookmaker_account", "real_money_balance", "wallet_address",
                    "private_key", "api_secret", "guaranteed_profit"]:
            assert fb not in js, f"Found: {fb}"


class TestSignalFusionRunner:
    """Tests for the signal_fusion_runner module."""

    def test_2026_06_11(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        assert p.current_date == "2026-06-11"

    def test_2026_06_24(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-24", 100.0)
        assert p.current_date == "2026-06-24"

    def test_2026_07_19(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-07-19", 100.0)
        assert p.current_date == "2026-07-19"

    def test_bankroll_5000(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-11", 5000.0)
        assert p.current_bankroll == 5000.0

    def test_source_summary(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        ss = p.source_summary
        assert "ev_ranking_available" in ss
        assert "integrated_strategy_available" in ss
        assert "market_expectation_available" in ss
        assert "team_news_available" in ss

    def test_fusion_summary(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        fu = p.fusion_summary
        assert "candidate_count" in fu
        assert "fused_signal_count" in fu
        assert isinstance(fu.get("candidate_count", -1), int)

    def test_support_summary(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        su = p.support_summary
        assert "market_supported_count" in su
        assert "team_context_supported_count" in su
        assert "low_quality_warning_count" in su

    def test_score_summary(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        sc = p.score_summary
        assert "average_base_campaign_score" in sc
        assert "average_upgraded_campaign_score" in sc
        assert "average_score_adjustment" in sc

    def test_generates_json(self):
        r = SignalFusionRunner(get_paths())
        r.run("2026-06-11", 100.0)
        assert (ROOT / "reports" / "generated" / "signal_fusion_preview.json").exists()

    def test_generates_md(self):
        r = SignalFusionRunner(get_paths())
        r.run("2026-06-11", 100.0)
        assert (ROOT / "reports" / "generated" / "signal_fusion_preview.md").exists()

    def test_no_stake(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        js = json.dumps(_d(p))
        for fb in ["stake_to_match", "stake_amount", "bet_instruction",
                    "bookmaker_account", "wallet_address", "private_key",
                    "api_secret", "signed_order", "submit_order",
                    "real_money_balance", "guaranteed_profit"]:
            assert fb not in js, f"Found forbidden: {fb}"

    def test_not_betting(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        assert p.not_betting_advice is True
        assert p.analysis_only is True
        assert p.simulation_only is True

    def test_safety_flags(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        s = p.safety
        assert s["campaign_analysis_only"] is True
        assert s["real_bet_execution"] is False
        assert s["auto_betting"] is False
        assert s["network_fetch_default_enabled"] is False

    def test_warnings_field(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        assert isinstance(p.warnings, list)
