"""Tests for EV ranking."""
import pytest
from worldcup_campaign.market_candidate import MarketCandidate
from worldcup_campaign.ev_ranking import EVRanker

class TestEVRanking:
    @pytest.fixture
    def ranker(self): return EVRanker(50)
    def test_rank_empty(self, ranker):
        r = ranker.rank([],"2026-06-11","synthetic")
        assert r.candidate_count == 0
    def test_rank_by_ev_descending(self, ranker):
        c1 = MarketCandidate("m1",1,"1x2","home","H","A","g1",2.0,0.6,0.5,0.5,0.1,0.2,"1.50-2.00","value",[])
        c2 = MarketCandidate("m2",2,"1x2","home","H2","A2","g1",2.0,0.4,0.5,0.5,-0.1,-0.2,"1.50-2.00","no_value",[])
        r = ranker.rank([c1,c2],"2026-06-11","synthetic")
        assert r.candidate_count == 2
        assert r.candidates[0].ev >= r.candidates[1].ev
    def test_uses_real_odds_false(self, ranker):
        r = ranker.rank([],"2026-06-11","synthetic")
        assert r.uses_real_bookmaker_odds is False
    def test_not_betting_advice(self, ranker):
        r = ranker.rank([],"2026-06-11","synthetic")
        assert r.not_betting_advice is True
    def test_filters_blocked(self, ranker):
        c1 = MarketCandidate("m1",1,"1x2","home","H","A","g1",2.0,0.5,0.5,0.5,0.0,0.0,"1.50-2.00","value",[])
        c1.is_blocked = True
        c2 = MarketCandidate("m2",2,"1x2","home","H2","A2","g1",2.0,0.5,0.5,0.5,0.0,0.0,"1.50-2.00","value",[])
        r = ranker.rank([c1,c2],"2026-06-11","synthetic")
        assert r.candidate_count == 1