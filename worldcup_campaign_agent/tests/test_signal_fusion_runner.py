"""Tests for signal_fusion_runner and signal_fusion_engine modules — includes score guard and review guard."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldcup_campaign.signal_fusion_runner import SignalFusionRunner, _d
from worldcup_campaign.signal_fusion_engine import fuse_signals, FusionSummary, FusedCandidate

ROOT = Path(__file__).resolve().parent.parent


def get_paths():
    return {"fusion_config": str(ROOT / "config" / "signal_fusion_config.json")}


def _cfg():
    return {
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


# ============================================================
# Engine tests — core fusion
# ============================================================

class TestFusionEngine:
    def test_fuse_signals_empty(self):
        result = fuse_signals([], [], [], [], _cfg())
        assert result.candidate_count == 0
        assert result.fused_signal_count == 0
        assert len(result.warnings) >= 1

    def test_fuse_signals_with_candidates(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.5, "bucket": "edge"},
            {"candidate_id": "c2", "match_id": "M2", "selection_id": "away",
             "market_type": "1x2", "campaign_score": 0.3, "bucket": "attack"},
        ]
        alignment_records = [{"key": "M1_home", "alignment_status": "aligned"}]
        context_signals = [{"team": "M1", "context_signal": "positive"}]
        quality_scores = [
            {"key": "M1_home", "score": 0.8},
            {"key": "M2_away", "score": 0.2},
        ]
        result = fuse_signals(candidates, alignment_records, context_signals, quality_scores, _cfg())
        assert result.candidate_count == 2
        assert result.fused_signal_count == 2

    def test_promoted_candidate(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1_FRA", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.5, "bucket": "edge"},
        ]
        alignment_records = [{"key": "M1_FRA_home", "alignment_status": "aligned"}]
        context_signals = [{"team": "FRA", "context_signal": "positive"}]
        quality_scores = [{"key": "M1_FRA_home", "score": 0.9}]
        result = fuse_signals(candidates, alignment_records, context_signals, quality_scores, _cfg())
        assert result.promoted_count >= 1
        assert result.candidates[0].score_adjustment > 0

    def test_demoted_candidate(self):
        # major_disagreement + no context support = negative adjustment = demoted
        candidates = [
            {"candidate_id": "c1", "match_id": "M1_BRA", "selection_id": "draw",
             "market_type": "1x2", "campaign_score": 0.3, "bucket": "core"},
        ]
        alignment_records = [{"key": "M1_BRA_draw", "alignment_status": "major_disagreement"}]
        quality_scores = [{"key": "M1_BRA_draw", "score": 0.5}]
        result = fuse_signals(candidates, alignment_records, [], quality_scores, _cfg())
        # major_disagree causes review, but also may cause demotion
        assert result.demoted_count >= 1 or result.review_required_count >= 1

    def test_watch_only_low_quality(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.2, "bucket": "attack"},
        ]
        quality_scores = [{"key": "M1_home", "score": 0.1}]
        result = fuse_signals(candidates, [], [], quality_scores, _cfg())
        assert result.watch_only_count >= 1 or result.review_required_count >= 1

    def test_capped_adjustment(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1_FRA", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.9, "bucket": "core"},
        ]
        alignment_records = [{"key": "M1_FRA_home", "alignment_status": "aligned"}]
        context_signals = [{"team": "FRA", "context_signal": "positive"}]
        quality_scores = [{"key": "M1_FRA_home", "score": 1.0}]
        result = fuse_signals(candidates, alignment_records, context_signals, quality_scores, _cfg())
        assert result.candidates[0].score_adjustment <= 0.25

    def test_bucket_upgrade_edge_to_core(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1_FRA", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.5, "bucket": "edge"},
        ]
        alignment_records = [{"key": "M1_FRA_home", "alignment_status": "aligned"}]
        context_signals = [{"team": "FRA", "context_signal": "positive"}]
        quality_scores = [{"key": "M1_FRA_home", "score": 0.9}]
        result = fuse_signals(candidates, alignment_records, context_signals, quality_scores, _cfg())
        assert result.candidates[0].upgraded_bucket == "core"

    def test_bucket_demote_core_to_edge(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1_BRA", "selection_id": "draw",
             "market_type": "1x2", "campaign_score": 0.3, "bucket": "core"},
        ]
        alignment_records = [{"key": "M1_BRA_draw", "alignment_status": "major_disagreement"}]
        quality_scores = [{"key": "M1_BRA_draw", "score": 0.5}]
        result = fuse_signals(candidates, alignment_records, [], quality_scores, _cfg())
        assert result.candidates[0].upgraded_bucket == "edge"

    def test_no_real_money_fields(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.5, "bucket": "edge"},
        ]
        result = fuse_signals(candidates, [], [], [], _cfg())
        js = json.dumps(_d(result))
        for fb in ["stake_to_match", "stake_amount", "bet_instruction",
                    "bookmaker_account", "real_money_balance", "wallet_address",
                    "private_key", "api_secret", "guaranteed_profit"]:
            assert fb not in js, f"Found: {fb}"


# ============================================================
# Score Guard tests
# ============================================================

class TestScoreGuard:
    """Tests that scores are clamped to 0-1."""

    def test_raw_negative_clamped_to_zero(self):
        """Raw base score negative → normalized base score = 0."""
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": -0.15, "bucket": "edge"},
        ]
        result = fuse_signals(candidates, [], [], [], _cfg())
        c = result.candidates[0]
        assert c.raw_base_signal == -0.15
        assert c.normalized_base_campaign_score == 0.0
        assert c.base_campaign_score == 0.0
        assert c.score_clamped is True

    def test_raw_above_one_clamped_to_one(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 1.5, "bucket": "edge"},
        ]
        result = fuse_signals(candidates, [], [], [], _cfg())
        c = result.candidates[0]
        assert c.normalized_base_campaign_score == 1.0
        assert c.score_clamped is True

    def test_upgraded_score_not_negative(self):
        """Upgraded score must be >= 0 even after negative adjustment."""
        candidates = [
            {"candidate_id": "c1", "match_id": "M1_BRA", "selection_id": "draw",
             "market_type": "1x2", "campaign_score": 0.0, "bucket": "core"},
        ]
        alignment_records = [{"key": "M1_BRA_draw", "alignment_status": "major_disagreement"}]
        quality_scores = [{"key": "M1_BRA_draw", "score": 0.3}]
        result = fuse_signals(candidates, alignment_records, [], quality_scores, _cfg())
        c = result.candidates[0]
        assert c.upgraded_campaign_score >= 0.0, f"upgraded={c.upgraded_campaign_score}"

    def test_upgraded_score_not_exceed_one(self):
        """Upgraded score must be <= 1."""
        candidates = [
            {"candidate_id": "c1", "match_id": "M1_FRA", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 1.0, "bucket": "core"},
        ]
        alignment_records = [{"key": "M1_FRA_home", "alignment_status": "aligned"}]
        context_signals = [{"team": "FRA", "context_signal": "positive"}]
        quality_scores = [{"key": "M1_FRA_home", "score": 1.0}]
        result = fuse_signals(candidates, alignment_records, context_signals, quality_scores, _cfg())
        c = result.candidates[0]
        assert c.upgraded_campaign_score <= 1.0, f"upgraded={c.upgraded_campaign_score}"

    def test_fusion_score_in_range(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": -0.2, "bucket": "attack"},
        ]
        result = fuse_signals(candidates, [], [], [], _cfg())
        for c in result.candidates:
            assert 0.0 <= c.fusion_score <= 1.0, f"fusion={c.fusion_score}"

    def test_score_guard_summary_fields_present(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": -0.05, "bucket": "edge"},
            {"candidate_id": "c2", "match_id": "M2", "selection_id": "away",
             "market_type": "1x2", "campaign_score": 0.8, "bucket": "edge"},
        ]
        result = fuse_signals(candidates, [], [], [], _cfg())
        assert result.min_base_campaign_score >= 0.0
        assert result.max_base_campaign_score <= 1.0
        assert result.min_upgraded_campaign_score >= 0.0
        assert result.max_upgraded_campaign_score <= 1.0
        assert result.min_fusion_score >= 0.0
        assert result.max_fusion_score <= 1.0
        assert result.raw_negative_signal_count >= 1
        assert result.score_clamped_count >= 1

    def test_raw_negative_signal_count(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": -0.1, "bucket": "edge"},
            {"candidate_id": "c2", "match_id": "M2", "selection_id": "away",
             "market_type": "1x2", "campaign_score": -0.05, "bucket": "attack"},
            {"candidate_id": "c3", "match_id": "M3", "selection_id": "draw",
             "market_type": "1x2", "campaign_score": 0.3, "bucket": "edge"},
        ]
        result = fuse_signals(candidates, [], [], [], _cfg())
        assert result.raw_negative_signal_count == 2


# ============================================================
# Review Guard tests
# ============================================================

class TestReviewGuard:
    """Tests that review is triggered on unexplained disagreement etc."""

    def test_unexplained_disagreement_triggers_review(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.5, "bucket": "edge"},
        ]
        alignment_records = [{"key": "M1_home", "alignment_status": "major_disagreement"}]
        result = fuse_signals(candidates, alignment_records, [], [], _cfg())
        assert result.unexplained_disagreement_count >= 1
        assert result.review_required_count >= 1 or result.watch_only_count >= 1
        assert result.review_triggered_by_unexplained_disagreement_count >= 1

    def test_major_disagreement_blocks_core(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.9, "bucket": "core"},
        ]
        alignment_records = [{"key": "M1_home", "alignment_status": "major_disagreement"}]
        context_signals = [{"team": "M1", "context_signal": "positive"}]
        quality_scores = [{"key": "M1_home", "score": 0.9}]
        result = fuse_signals(candidates, alignment_records, context_signals, quality_scores, _cfg())
        c = result.candidates[0]
        assert c.upgraded_bucket != "core", f"major disagreement should block core, got {c.upgraded_bucket}"

    def test_missing_market_context_triggers_warning(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.7, "bucket": "edge"},
        ]
        # No alignment records → missing market context
        result = fuse_signals(candidates, [], [], [], _cfg())
        c = result.candidates[0]
        assert c.missing_market_context is True
        assert "missing_market_context" in c.review_reasons
        assert result.review_triggered_by_missing_market_context_count >= 1

    def test_missing_team_context_triggers_warning(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.7, "bucket": "edge"},
        ]
        # No context signals → missing team context
        result = fuse_signals(candidates, [], [], [], _cfg())
        c = result.candidates[0]
        assert c.missing_team_context is True
        assert "missing_team_context" in c.review_reasons
        assert result.review_triggered_by_missing_team_context_count >= 1

    def test_review_guard_summary_fields_present(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.5, "bucket": "edge"},
        ]
        result = fuse_signals(candidates, [], [], [], _cfg())
        assert hasattr(result, "review_triggered_by_unexplained_disagreement_count")
        assert hasattr(result, "review_triggered_by_missing_market_context_count")
        assert hasattr(result, "review_triggered_by_missing_team_context_count")

    def test_candidate_has_review_fields(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": -0.1, "bucket": "edge"},
        ]
        result = fuse_signals(candidates, [], [], [], _cfg())
        c = result.candidates[0]
        assert hasattr(c, "requires_review")
        assert hasattr(c, "review_reasons")
        assert hasattr(c, "raw_base_signal")
        assert hasattr(c, "normalized_base_campaign_score")
        assert hasattr(c, "fusion_score")
        assert hasattr(c, "score_clamped")
        assert hasattr(c, "missing_market_context")
        assert hasattr(c, "missing_team_context")

    def test_no_betting_fields_in_candidate(self):
        candidates = [
            {"candidate_id": "c1", "match_id": "M1", "selection_id": "home",
             "market_type": "1x2", "campaign_score": 0.5, "bucket": "edge"},
        ]
        result = fuse_signals(candidates, [], [], [], _cfg())
        js = json.dumps(_d(result.candidates[0]))
        for fb in ["stake", "stake_amount", "stake_to_match", "bet_instruction",
                    "bookmaker", "bookmaker_account", "real_money_balance",
                    "wallet_address", "private_key"]:
            assert fb not in js, f"Found: {fb}"


# ============================================================
# Runner tests
# ============================================================

class TestSignalFusionRunner:
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
        assert "market_expectation_available" in ss
        assert "team_news_available" in ss

    def test_fusion_summary(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        fu = p.fusion_summary
        assert "candidate_count" in fu
        assert isinstance(fu.get("candidate_count", -1), int)

    def test_score_guard_summary(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        sg = p.score_guard_summary
        assert sg["min_base_campaign_score"] >= 0.0
        assert sg["max_base_campaign_score"] <= 1.0
        assert sg["min_upgraded_campaign_score"] >= 0.0
        assert sg["max_upgraded_campaign_score"] <= 1.0

    def test_review_guard_summary(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        rg = p.review_guard_summary
        assert "unexplained_disagreement_count" in rg
        assert "review_triggered_by_unexplained_disagreement_count" in rg
        assert "review_triggered_by_missing_market_context_count" in rg
        assert "review_triggered_by_missing_team_context_count" in rg

    def test_review_triggers_on_unexplained(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        rg = p.review_guard_summary
        fu = p.fusion_summary
        ud = rg.get("unexplained_disagreement_count", 0)
        rc = fu.get("review_required_count", 0)
        wc = fu.get("watch_only_count", 0)
        if ud > 0:
            assert rc > 0 or wc > 0, f"unexplained={ud} but review={rc} watch={wc}"

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

    def test_warnings_field(self):
        r = SignalFusionRunner(get_paths())
        p = r.run("2026-06-11", 100.0)
        assert isinstance(p.warnings, list)
