"""Polymarket runner: full pipeline for prediction market data analysis."""
import json, sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from worldcup_campaign.polymarket_discovery import (
    load_polymarket_fixture, discover_polymarket_markets, DiscoverySummary
)
from worldcup_campaign.polymarket_signal import extract_polymarket_signals, SignalSummary
from worldcup_campaign.polymarket_consensus import build_polymarket_consensus, ConsensusSummary
from worldcup_campaign.polymarket_gap import analyze_polymarket_gaps, GapSummary


@dataclass
class PolymarketPreview:
    campaign_name: str = "worldcup_2026_high_odds_campaign"
    current_date: str = ""
    current_bankroll: float = 100.0
    discovery_summary: dict = field(default_factory=dict)
    signal_summary: dict = field(default_factory=dict)
    consensus_summary: dict = field(default_factory=dict)
    gap_summary: dict = field(default_factory=dict)
    safety: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    generated_at: str = ""
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


def _dataclass_to_dict(obj):
    if hasattr(obj, '__dataclass_fields__'):
        return {k: _dataclass_to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_dataclass_to_dict(i) for i in obj]
    return obj


class PolymarketRunner:
    def __init__(self, config_paths: dict):
        self.paths = config_paths

    def run(self, date: str, bankroll: float, fixture_path: str = None) -> PolymarketPreview:
        config = json.loads(Path(self.paths["polymarket_config"]).read_text(encoding="utf-8-sig"))
        reports_dir = str(Path(self.paths["polymarket_config"]).parent.parent / "reports" / "generated")

        preview = PolymarketPreview(
            current_date=date, current_bankroll=bankroll,
            generated_at=datetime.now().isoformat(),
        )

        # Load fixture
        if not fixture_path:
            fixture_path = str(Path(self.paths["polymarket_config"]).parent.parent / "data" / "seed" / "polymarket_seed.json")
        fixture = load_polymarket_fixture(fixture_path)

        # 1. Discovery
        discovery = discover_polymarket_markets(fixture, config)
        preview.discovery_summary = _dataclass_to_dict(discovery)
        preview.warnings.extend(discovery.warnings)

        # 2. Signals
        signals = extract_polymarket_signals(discovery, config)
        preview.signal_summary = _dataclass_to_dict(signals)
        preview.warnings.extend(signals.warnings)

        # 3. Consensus
        consensus = build_polymarket_consensus(discovery, config)
        preview.consensus_summary = _dataclass_to_dict(consensus)
        preview.warnings.extend(consensus.warnings)

        # 4. Gaps (cross-reference with sportsbook and model)
        mo_path = Path(reports_dir) / "market_odds_consensus.json"
        mp_path = Path(reports_dir) / "match_probability_preview.json"
        mo_data = json.loads(mo_path.read_text(encoding="utf-8")) if mo_path.exists() else {}
        mp_data = json.loads(mp_path.read_text(encoding="utf-8")) if mp_path.exists() else {}
        gaps = analyze_polymarket_gaps(discovery, signals, consensus, mo_data, mp_data, config)
        preview.gap_summary = _dataclass_to_dict(gaps)
        preview.warnings.extend(gaps.warnings)

        # 5. Safety
        preview.safety = {
            "campaign_analysis_only": True,
            "real_bet_execution": False,
            "auto_betting": False,
            "external_betting_api_allowed": False,
            "real_money_instruction_allowed": False,
            "network_fetch_default_enabled": config.get("network", {}).get("network_fetch_default_enabled", False),
            "order_submission_allowed": config.get("trading", {}).get("order_submission_allowed", False),
            "wallet_connection_allowed": config.get("trading", {}).get("wallet_connection_allowed", False),
            "analysis_only": True,
            "simulation_only": True,
            "not_betting_advice": True,
        }

        # Write outputs
        self._write_outputs(preview, reports_dir)
        return preview

    def _write_outputs(self, preview, reports_dir: str):
        out_dir = Path(reports_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "polymarket_preview.json").write_text(
            json.dumps(_dataclass_to_dict(preview), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        (out_dir / "polymarket_preview.md").write_text(self._render_md(preview), encoding="utf-8")

    def _render_md(self, p) -> str:
        ds = p.discovery_summary; ss = p.signal_summary; cs = p.consensus_summary; gs = p.gap_summary
        lines = [
            "# Polymarket Prediction Market Preview", "",
            f"**Date:** {p.current_date} | **Bankroll:** {p.current_bankroll}", "",
            "## 1. Event Discovery",
            f"- Total events: {ds.get('event_count',0)}",
            f"- Relevant events: {ds.get('relevant_event_count',0)}",
            f"- Total markets: {ds.get('market_count',0)}",
            f"- Relevant markets: {ds.get('relevant_market_count',0)}",
            f"- Mapped markets: {ds.get('mapped_market_count',0)}",
            f"- Deferred markets: {ds.get('deferred_market_count',0)}", "",
            "## 2. Market Signals",
            f"- Normalized outcomes: {ss.get('normalized_outcome_count',0)}",
            f"- Orderbook signals: {ss.get('orderbook_signal_count',0)}",
            f"- Price history signals: {ss.get('price_history_signal_count',0)}",
            f"- Liquidity signals: {ss.get('liquidity_signal_count',0)}", "",
            "## 3. Prediction Consensus",
            f"- Consensus records: {cs.get('prediction_consensus_count',0)}",
            f"- Strong consensus: {cs.get('strong_consensus_count',0)}",
            f"- Usable consensus: {cs.get('usable_consensus_count',0)}", "",
            "## 4. Market Disagreement (Gaps)",
            f"- Gap records: {gs.get('gap_record_count',0)}",
            f"- Model above Polymarket: {gs.get('model_above_polymarket_count',0)}",
            f"- Model below Polymarket: {gs.get('model_below_polymarket_count',0)}",
            f"- Sportsbook above Polymarket: {gs.get('sportsbook_above_polymarket_count',0)}",
            f"- Sportsbook below Polymarket: {gs.get('sportsbook_below_polymarket_count',0)}",
            f"- Major disagreements: {gs.get('major_disagreement_count',0)}",
            f"- Low liquidity gap: {gs.get('low_liquidity_gap_count',0)}", "",
            "## 5. Warnings",
        ]
        for w in p.warnings:
            lines.append(f"- {w}")
        lines.extend([
            "", "## 6. Safety",
            f"- Analysis only: {p.analysis_only}",
            f"- Order submission: {p.safety.get('order_submission_allowed',False)}",
            f"- Wallet connection: {p.safety.get('wallet_connection_allowed',False)}",
            f"- Not betting advice: {p.not_betting_advice}",
            "", "---",
            "*Fixture-based analysis. No real Polymarket data, no trading, no orders.*",
        ])
        return "\n".join(lines)
