"""Polymarket signal: price, orderbook, liquidity, and price movement analysis."""
from dataclasses import dataclass, field


@dataclass
class OrderbookSignal:
    market_id: str = ""
    bid: float = 0.0
    ask: float = 0.0
    midpoint: float = 0.0
    spread: float = 0.0
    spread_warning: bool = False
    depth_bid: float = 0.0
    depth_ask: float = 0.0
    imbalance: float = 0.0


@dataclass
class PriceHistorySignal:
    market_id: str = ""
    current_price: float = 0.0
    price_change_24h: float = 0.0
    direction: str = "stable"
    momentum: str = "neutral"


@dataclass
class LiquiditySignal:
    market_id: str = ""
    liquidity: float = 0.0
    volume: float = 0.0
    liquidity_level: str = "low"
    turnover_ratio: float = 0.0


@dataclass
class SignalSummary:
    orderbook_signals: list = field(default_factory=list)
    price_history_signals: list = field(default_factory=list)
    liquidity_signals: list = field(default_factory=list)
    normalized_outcome_count: int = 0
    orderbook_signal_count: int = 0
    price_history_signal_count: int = 0
    liquidity_signal_count: int = 0
    warnings: list = field(default_factory=list)


def extract_polymarket_signals(discovery_summary, config: dict) -> SignalSummary:
    spread_warn = config.get("signal", {}).get("spread_warning_threshold", 0.05)
    summary = SignalSummary()

    for event in discovery_summary.events:
        for market in event.markets:
            if not market.is_relevant or market.is_deferred:
                continue

            summary.normalized_outcome_count += 1

            # Orderbook signal
            spread = market.spread
            obs = OrderbookSignal(
                market_id=market.market_id,
                bid=market.bid,
                ask=market.ask,
                midpoint=market.midpoint,
                spread=spread,
                spread_warning=spread > spread_warn,
                depth_bid=market.liquidity * market.bid,
                depth_ask=market.liquidity * (1 - market.ask),
                imbalance=round(market.bid / market.ask - 1, 4) if market.ask > 0 else 0,
            )
            summary.orderbook_signals.append(obs)
            summary.orderbook_signal_count += 1

            # Price history signal
            hist = market.price_history
            if len(hist) >= 2:
                change = hist[-1] - hist[0]
                pct_change = round(change / hist[0], 4) if hist[0] > 0 else 0
                direction = "up" if change > 0.01 else ("down" if change < -0.01 else "stable")
                momentum = "rising" if pct_change > 0.02 else ("falling" if pct_change < -0.02 else "neutral")
                phs = PriceHistorySignal(
                    market_id=market.market_id,
                    current_price=hist[-1],
                    price_change_24h=pct_change,
                    direction=direction,
                    momentum=momentum,
                )
                summary.price_history_signals.append(phs)
                summary.price_history_signal_count += 1

            # Liquidity signal
            liq_level = "high" if market.liquidity >= 100000 else ("medium" if market.liquidity >= 10000 else "low")
            ls = LiquiditySignal(
                market_id=market.market_id,
                liquidity=market.liquidity,
                volume=market.volume,
                liquidity_level=liq_level,
                turnover_ratio=round(market.volume / market.liquidity, 4) if market.liquidity > 0 else 0,
            )
            summary.liquidity_signals.append(ls)
            summary.liquidity_signal_count += 1

    if summary.normalized_outcome_count == 0:
        summary.warnings.append("No relevant Polymarket outcomes found for signal extraction.")

    return summary
