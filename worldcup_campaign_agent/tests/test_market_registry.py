"""Tests for market universe registry."""

from pathlib import Path

import pytest

from worldcup_campaign.market_registry import (
    load_market_universe,
    validate_market_universe,
    get_markets_for_bucket,
    get_market_definition,
    MarketDefinition,
)


def _config_path(filename: str) -> str:
    return str(
        Path(__file__).resolve().parent.parent / "config" / filename
    )


class TestLoadMarketUniverse:
    """Tests for loading market universe."""

    def test_load_valid_markets(self):
        """Market universe should load successfully."""
        markets = load_market_universe(_config_path("market_universe.json"))
        assert len(markets) == 20

    def test_all_market_types_unique(self):
        """All market_type values must be unique."""
        markets = load_market_universe(_config_path("market_universe.json"))
        types = [m.market_type for m in markets]
        assert len(types) == len(set(types))

    def test_all_buckets_valid(self):
        """No market should reference unknown buckets."""
        markets = load_market_universe(_config_path("market_universe.json"))
        valid = {"core", "edge", "attack", "futures"}
        for m in markets:
            for bucket in m.allowed_buckets:
                assert bucket in valid or bucket == "reserve", (
                    f"Market {m.market_type} has invalid bucket '{bucket}'"
                )

    def test_no_market_in_reserve(self):
        """No market should be in the reserve bucket."""
        markets = load_market_universe(_config_path("market_universe.json"))
        for m in markets:
            assert "reserve" not in m.allowed_buckets, (
                f"Market '{m.market_type}' should not be in reserve bucket"
            )


class TestCoreBucket:
    """Core bucket should not contain high-variance or complex markets."""

    def test_core_no_correct_score(self):
        markets = load_market_universe(_config_path("market_universe.json"))
        core_markets = get_markets_for_bucket("core", markets)
        core_types = [m.market_type for m in core_markets]
        assert "correct_score" not in core_types

    def test_core_no_parlay_4_leg(self):
        markets = load_market_universe(_config_path("market_universe.json"))
        core_markets = get_markets_for_bucket("core", markets)
        core_types = [m.market_type for m in core_markets]
        assert "parlay_4_leg" not in core_types

    def test_core_no_parlay_3_leg(self):
        """parlay_3_leg should not be in core (per spec)."""
        markets = load_market_universe(_config_path("market_universe.json"))
        core_markets = get_markets_for_bucket("core", markets)
        core_types = [m.market_type for m in core_markets]
        assert "parlay_3_leg" not in core_types

    def test_core_no_golden_boot(self):
        markets = load_market_universe(_config_path("market_universe.json"))
        core_markets = get_markets_for_bucket("core", markets)
        core_types = [m.market_type for m in core_markets]
        assert "golden_boot" not in core_types


class TestFuturesBucket:
    """Futures bucket should only contain futures type markets."""

    def test_futures_only_futures(self):
        markets = load_market_universe(_config_path("market_universe.json"))
        futures_markets = get_markets_for_bucket("futures", markets)
        for m in futures_markets:
            assert m.is_futures, (
                f"Market '{m.market_type}' in futures bucket but is_futures=False"
            )


class TestAttackBucket:
    """Attack bucket should contain high-variance markets."""

    def test_attack_has_correct_score(self):
        markets = load_market_universe(_config_path("market_universe.json"))
        attack_markets = get_markets_for_bucket("attack", markets)
        attack_types = [m.market_type for m in attack_markets]
        assert "correct_score" in attack_types

    def test_attack_has_parlay_3_or_4(self):
        markets = load_market_universe(_config_path("market_universe.json"))
        attack_markets = get_markets_for_bucket("attack", markets)
        attack_types = [m.market_type for m in attack_markets]
        assert "parlay_3_leg" in attack_types or "parlay_4_leg" in attack_types


class TestGetMarketDefinition:
    """Tests for get_market_definition lookup."""

    def test_get_known_market(self):
        markets = load_market_universe(_config_path("market_universe.json"))
        m = get_market_definition("1x2", markets)
        assert m.market_type == "1x2"
        assert m.display_name == "1X2 (Win-Draw-Loss)"

    def test_unknown_market_type_fails(self):
        markets = load_market_universe(_config_path("market_universe.json"))
        with pytest.raises(ValueError, match="Unknown market_type"):
            get_market_definition("nonexistent_market", markets)


class TestUnknownBucket:
    """Tests for invalid bucket queries."""

    def test_unknown_bucket_fails(self):
        markets = load_market_universe(_config_path("market_universe.json"))
        with pytest.raises(ValueError, match="Unknown bucket"):
            get_markets_for_bucket("invalid_bucket", markets)
