"""Tests for probability quality assessment."""
from worldcup_campaign.probability_quality import assess_quality

class TestProbabilityQuality:
    def test_placeholder_warning(self):
        qa = assess_quality(True, False, 50, False, 0.5)
        assert "home_team_is_placeholder" in qa.factors
    def test_confidence_label_high(self):
        qa = assess_quality(False, False, 200, False, 0.7)
        assert qa.confidence_label == "high"
    def test_confidence_label_low(self):
        qa = assess_quality(False, False, 10, False, 0.2)
        assert qa.confidence_label == "low"
    def test_knockout_warning(self):
        qa = assess_quality(False, False, 100, True, 0.5)
        assert any("knockout" in w.lower() for w in qa.warnings)
    def test_seed_data_flag(self):
        qa = assess_quality(False, False, 100, False, 0.5)
        assert qa.is_seed_data is True