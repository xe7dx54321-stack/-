"""Tests for match strategy labeler."""

from datetime import date
from pathlib import Path

import pytest

from worldcup_campaign.match_registry import load_match_registry, get_matches_by_date
from worldcup_campaign.match_strategy_labeler import MatchStrategyLabeler


def _config_path(filename: str) -> str:
    return str(Path(__file__).resolve().parent.parent / "config" / filename)

def _data_path(filename: str) -> str:
    return str(Path(__file__).resolve().parent.parent / "data" / "seed" / filename)


class TestMatchStrategyLabeler:
    @pytest.fixture
    def labeler(self):
        return MatchStrategyLabeler(_config_path("match_tagging_rules.json"))

    @pytest.fixture
    def matches(self):
        return load_match_registry(_data_path("worldcup_2026_match_registry.json"))

    def test_labels_opening_day(self, labeler, matches):
        today = date(2026, 6, 11)
        today_matches = get_matches_by_date(today, matches)
        labeled = labeler.label_matches(today_matches, today)
        assert len(labeled) == 4
        for ml in labeled:
            assert ml.is_today is True
            assert len(ml.labels) > 0

    def test_labels_final(self, labeler, matches):
        today = date(2026, 7, 19)
        today_matches = get_matches_by_date(today, matches)
        labeled = labeler.label_matches(today_matches, today)
        assert len(labeled) == 1
        assert "championship_match" in labeled[0].labels

    def test_labels_group_r3(self, labeler, matches):
        today = date(2026, 6, 24)
        today_matches = get_matches_by_date(today, matches)
        labeled = labeler.label_matches(today_matches, today)
        assert len(labeled) == 6
        for ml in labeled:
            assert ml.is_today is True

    def test_label_definition_exists(self, labeler):
        for name in ["high_confidence_core", "value_edge", "high_odds_attack", "skip"]:
            d = labeler.get_label_definition(name)
            assert d is not None, f"Label '{name}' not found"

    def test_labels_not_empty_or_skip_on_match_day(self, labeler, matches):
        """Active match days should not produce empty labels."""
        today = date(2026, 6, 11)
        today_matches = get_matches_by_date(today, matches)
        labeled = labeler.label_matches(today_matches, today)
        for ml in labeled:
            assert ml.labels, f"Match {ml.match_id} has no labels"