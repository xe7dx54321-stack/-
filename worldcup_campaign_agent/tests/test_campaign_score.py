"""Tests for campaign score."""
from pathlib import Path
import pytest
from worldcup_campaign.campaign_score import load_campaign_score_config, calculate_campaign_score
def _cfg(f): return str(Path(__file__).resolve().parent.parent/"config"/f)

class TestCampaignScore:
    @pytest.fixture
    def config(self): return load_campaign_score_config(_cfg("campaign_score_config.json"))
    def test_score_in_range(self, config):
        c = {"mock_odds":2.0,"edge":0.05,"ev":0.1,"model_probability":0.5,"value_flag":"value","match_id":"m","market_type":"1x2"}
        r = calculate_campaign_score(c,100,1000000,40,config)
        assert 0 <= r.campaign_score <= 1
    def test_negative_ev_penalized_but_not_deleted(self, config):
        c = {"mock_odds":2.0,"edge":0.0,"ev":-0.1,"model_probability":0.5,"value_flag":"no_value","match_id":"m","market_type":"1x2"}
        r = calculate_campaign_score(c,100,1000000,40,config)
        assert r.campaign_score >= 0
    def test_value_candidate_needs_value_flag(self, config):
        c = {"mock_odds":2.0,"edge":0.1,"ev":0.2,"model_probability":0.5,"value_flag":"no_value","match_id":"m","market_type":"1x2"}
        r = calculate_campaign_score(c,100,1000000,40,config)
        assert r.candidate_tier != "value_candidate"
    def test_high_tc_boosts_score(self, config):
        c1 = {"mock_odds":2.0,"edge":0.1,"ev":0.1,"model_probability":0.5,"value_flag":"value","match_id":"m","market_type":"1x2"}
        c2 = {"mock_odds":20.0,"edge":0.1,"ev":0.1,"model_probability":0.5,"value_flag":"value","match_id":"m","market_type":"1x2"}
        r1 = calculate_campaign_score(c1,100,1000000,40,config)
        r2 = calculate_campaign_score(c2,100,1000000,40,config)
        assert r2.score_components["target_contribution_score"] >= r1.score_components["target_contribution_score"]
    def test_low_confidence_penalty(self, config):
        c = {"mock_odds":2.0,"edge":0.1,"ev":0.1,"model_probability":0.5,"value_flag":"value","match_id":"m","market_type":"1x2","confidence":0.1}
        r = calculate_campaign_score(c,100,1000000,40,config)
        assert "very_low_confidence_penalty" in r.penalties_applied
    def test_reason_codes_not_empty(self, config):
        c = {"mock_odds":5.0,"edge":0.1,"ev":0.1,"model_probability":0.3,"value_flag":"value","match_id":"m","market_type":"1x2"}
        r = calculate_campaign_score(c,100,1000000,40,config)
        assert len(r.reason_codes) > 0
    def test_not_betting_advice(self, config):
        c = {"mock_odds":2.0,"edge":0.0,"ev":0.0,"model_probability":0.5,"value_flag":"no_value","match_id":"m","market_type":"1x2"}
        r = calculate_campaign_score(c,100,1000000,40,config)
        assert r.not_betting_advice is True