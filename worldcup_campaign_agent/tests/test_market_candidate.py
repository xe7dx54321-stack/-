"""Tests for market candidate builder."""
from pathlib import Path
import pytest
from worldcup_campaign.market_candidate import MarketCandidateBuilder
def _cfg(f): return str(Path(__file__).resolve().parent.parent/"config"/f)

class TestMarketCandidate:
    @pytest.fixture
    def builder(self): return MarketCandidateBuilder(_cfg("ev_ranking_config.json"))
    def test_build_1x2_three_candidates(self, builder):
        c = builder.build_1x2_candidates("m1",1,"H","A","group_round_1",0.5,0.25,0.25,1.8,3.5,4.0)
        assert len(c) == 3
    def test_ev_calculated(self, builder):
        c = builder.build_1x2_candidates("m1",1,"H","A","group_round_1",0.6,0.2,0.2,1.5,4.0,5.0)
        assert c[0].ev != 0
    def test_edge_calculated(self, builder):
        c = builder.build_1x2_candidates("m1",1,"H","A","group_round_1",0.55,0.15,0.30,1.7,5.0,3.0)
        assert c[0].edge is not None
    def test_value_flag_set(self, builder):
        c = builder.build_1x2_candidates("m1",1,"H","A","group_round_1",0.6,0.2,0.2,1.5,4.0,5.0)
        assert c[0].value_flag != ""
    def test_odds_band(self, builder):
        c = builder.build_1x2_candidates("m1",1,"H","A","group_round_1",0.5,0.25,0.25,1.8,3.5,4.0)
        assert c[0].odds_band != ""
    def test_ou_candidates(self, builder):
        c = builder.build_ou_candidates("m1",1,"H","A","group_round_1",2.5,0.5,0.5,1.8,1.9)
        assert len(c) == 2