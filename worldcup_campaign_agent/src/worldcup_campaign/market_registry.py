"""Market universe registry: load, validate, and query betting markets."""

import json
from dataclasses import dataclass
from pathlib import Path


VALID_BUCKETS = ["reserve", "core", "edge", "attack", "futures"]


@dataclass
class MarketDefinition:
    market_type: str
    display_name: str
    category: str
    allowed_buckets: list[str]
    max_bucket_share: float
    requires_model_probability: bool
    requires_odds: bool
    is_high_variance: bool
    is_futures: bool
    is_parlay: bool
    enabled: bool


def load_market_universe(path: str) -> list[MarketDefinition]:
    """Load market universe from JSON file."""
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    markets = []
    for entry in raw:
        m = MarketDefinition(
            market_type=entry["market_type"],
            display_name=entry["display_name"],
            category=entry["category"],
            allowed_buckets=list(entry["allowed_buckets"]),
            max_bucket_share=float(entry.get("max_bucket_share", 1.0)),
            requires_model_probability=bool(entry.get("requires_model_probability", True)),
            requires_odds=bool(entry.get("requires_odds", True)),
            is_high_variance=bool(entry.get("is_high_variance", False)),
            is_futures=bool(entry.get("is_futures", False)),
            is_parlay=bool(entry.get("is_parlay", False)),
            enabled=bool(entry.get("enabled", True)),
        )
        markets.append(m)
    validate_market_universe(markets)
    return markets


def validate_market_universe(markets: list[MarketDefinition]) -> None:
    """Validate market universe integrity."""
    market_types = set()
    for m in markets:
        # Check unique market_type
        if m.market_type in market_types:
            raise ValueError(f"Duplicate market_type: {m.market_type}")
        market_types.add(m.market_type)

        # Check all buckets are valid
        for bucket in m.allowed_buckets:
            if bucket not in VALID_BUCKETS:
                raise ValueError(
                    f"Market '{m.market_type}': unknown bucket '{bucket}'"
                )

        # No market should go into reserve bucket
        if "reserve" in m.allowed_buckets:
            raise ValueError(
                f"Market '{m.market_type}': 'reserve' is not a playable bucket"
            )

        # parlay type must have is_parlay=true
        if m.category == "parlay" and not m.is_parlay:
            raise ValueError(
                f"Market '{m.market_type}': category is 'parlay' but is_parlay is false"
            )

        # futures type must have is_futures=true
        if m.category == "futures" and not m.is_futures:
            raise ValueError(
                f"Market '{m.market_type}': category is 'futures' but is_futures is false"
            )


def get_markets_for_bucket(
    bucket: str, markets: list[MarketDefinition]
) -> list[MarketDefinition]:
    """Get all enabled markets allowed for a given bucket."""
    if bucket not in VALID_BUCKETS:
        raise ValueError(f"Unknown bucket: '{bucket}'")
    return [
        m for m in markets
        if m.enabled and bucket in m.allowed_buckets
    ]


def get_market_definition(
    market_type: str, markets: list[MarketDefinition]
) -> MarketDefinition:
    """Get a specific market definition by type."""
    for m in markets:
        if m.market_type == market_type:
            if not m.enabled:
                raise ValueError(f"Market '{market_type}' is disabled")
            return m
    raise ValueError(f"Unknown market_type: '{market_type}'")
