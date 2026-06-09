"""Polymarket discovery: event/market discovery and World Cup relevance matching."""
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PolymarketMarket:
    market_id: str = ""
    question: str = ""
    outcome: str = "YES"
    last_price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    midpoint: float = 0.0
    spread: float = 0.0
    volume: float = 0.0
    liquidity: float = 0.0
    implied_probability: float = 0.0
    price_history: list = field(default_factory=list)
    is_relevant: bool = False
    relevance_tags: list = field(default_factory=list)
    is_deferred: bool = False
    team_mapping: str = ""


@dataclass
class PolymarketEvent:
    event_id: str = ""
    title: str = ""
    tags: list = field(default_factory=list)
    volume: float = 0.0
    liquidity: float = 0.0
    active: bool = True
    markets: list = field(default_factory=list)
    is_relevant: bool = False


@dataclass
class DiscoverySummary:
    events: list = field(default_factory=list)
    event_count: int = 0
    relevant_event_count: int = 0
    market_count: int = 0
    relevant_market_count: int = 0
    mapped_market_count: int = 0
    deferred_market_count: int = 0
    warnings: list = field(default_factory=list)


def load_polymarket_fixture(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def classify_liquidity(liquidity: float, config: dict) -> str:
    high = config.get("liquidity", {}).get("high_liquidity_threshold", 100000)
    medium = config.get("liquidity", {}).get("medium_liquidity_threshold", 10000)
    if liquidity >= high:
        return "high"
    elif liquidity >= medium:
        return "medium"
    return "low"


def discover_polymarket_markets(fixture: dict, config: dict) -> DiscoverySummary:
    relevant_tags = config.get("discovery", {}).get("relevant_tags", ["world cup", "fifa", "soccer", "wc2026"])
    deferred_tags = config.get("discovery", {}).get("deferred_tags", ["golden boot", "golden ball"])
    min_vol = config.get("discovery", {}).get("min_volume_for_consideration", 1000)

    summary = DiscoverySummary()
    events_data = fixture.get("events", [])

    for ev in events_data:
        ev_tags = [t.lower() for t in ev.get("tags", [])]
        is_relevant = any(rt in et or et in rt for rt in relevant_tags for et in ev_tags)
        is_deferred_event = any(dt in et for dt in deferred_tags for et in ev_tags)

        event = PolymarketEvent(
            event_id=ev.get("event_id", ""),
            title=ev.get("title", ""),
            tags=ev.get("tags", []),
            volume=ev.get("volume", 0),
            liquidity=ev.get("liquidity", 0),
            active=ev.get("active", True),
            is_relevant=is_relevant,
        )
        summary.events.append(event)
        summary.event_count += 1

        if is_relevant:
            summary.relevant_event_count += 1

        for m in ev.get("markets", []):
            market = PolymarketMarket(
                market_id=m.get("market_id", ""),
                question=m.get("question", ""),
                outcome=m.get("outcome", "YES"),
                last_price=m.get("last_price", 0),
                bid=m.get("bid", 0),
                ask=m.get("ask", 0),
                midpoint=(m.get("bid", 0) + m.get("ask", 0)) / 2,
                spread=round(abs(m.get("ask", 0) - m.get("bid", 0)), 6),
                volume=m.get("volume", 0),
                liquidity=m.get("liquidity", 0),
                implied_probability=round(m.get("last_price", 0), 6),
                price_history=m.get("price_history", []),
                is_relevant=is_relevant,
                is_deferred=is_deferred_event,
            )
            event.markets.append(market)
            summary.market_count += 1

            if is_relevant:
                summary.relevant_market_count += 1
                if market.volume >= min_vol:
                    summary.mapped_market_count += 1
            if is_deferred_event:
                summary.deferred_market_count += 1

    if summary.mapped_market_count == 0:
        summary.warnings.append("No Polymarket markets mapped to World Cup events; check seed data or tags.")
    if summary.deferred_market_count > 0:
        summary.warnings.append(f"{summary.deferred_market_count} deferred markets (golden boot/ball/etc.) — not mapped to match-level analysis.")

    return summary
