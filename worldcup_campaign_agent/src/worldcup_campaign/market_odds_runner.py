"""Market odds consensus runner: full pipeline for odds ingestion, normalization, no-vig, consensus, movement, freshness, model gap."""
import json, sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from worldcup_campaign.odds_source_adapter import (
    load_odds_from_csv, load_odds_from_json, load_synthetic_odds_from_ev_ranking,
    OddsSnapshot
)
from worldcup_campaign.odds_normalizer import normalize_odds_entries, NormalizedOddsSnapshot
from worldcup_campaign.no_vig_calculator import build_no_vig_markets, NoVigSummary
from worldcup_campaign.market_consensus import build_market_consensus, ConsensusSummary
from worldcup_campaign.odds_movement import analyze_odds_movement, MovementSummary
from worldcup_campaign.odds_freshness import check_odds_freshness, FreshnessSummary
from worldcup_campaign.market_model_gap import compute_model_vs_market_gap, ModelMarketGapSummary


@dataclass
class MarketOddsConsensusPreview:
    campaign_name: str = "worldcup_2026_high_odds_campaign"
    current_date: str = ""
    current_bankroll: float = 100.0
    odds_snapshot: dict = field(default_factory=dict)
    normalized_snapshot: dict = field(default_factory=dict)
    no_vig_summary: dict = field(default_factory=dict)
    consensus_summary: dict = field(default_factory=dict)
    movement_summary: dict = field(default_factory=dict)
    freshness_summary: dict = field(default_factory=dict)
    model_vs_market_gap: dict = field(default_factory=dict)
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


class MarketOddsRunner:
    def __init__(self, config_paths: dict):
        self.paths = config_paths

    def run(self, date: str, bankroll: float, manual_csv: str = None, manual_json: str = None,
            use_synthetic: bool = False) -> MarketOddsConsensusPreview:
        config = json.loads(Path(self.paths["odds_config"]).read_text(encoding="utf-8-sig"))
        reports_dir = str(Path(self.paths["odds_config"]).parent.parent / "reports" / "generated")

        preview = MarketOddsConsensusPreview(
            current_date=date,
            current_bankroll=bankroll,
            generated_at=datetime.now().isoformat(),
        )

        # 1. Load odds
        raw_snapshot = None
        if manual_csv:
            raw_snapshot = load_odds_from_csv(manual_csv)
        elif manual_json:
            raw_snapshot = load_odds_from_json(manual_json)
        elif use_synthetic:
            ev_path = Path(reports_dir) / "ev_ranking_preview.json"
            mp_path = Path(reports_dir) / "match_probability_preview.json"
            ev_data = {}
            mp_data = {}
            if ev_path.exists():
                ev_data = json.loads(ev_path.read_text(encoding="utf-8"))
            if mp_path.exists():
                mp_data = json.loads(mp_path.read_text(encoding="utf-8"))
            raw_snapshot = load_synthetic_odds_from_ev_ranking(ev_data, mp_data)
        else:
            # Try manual_json in seed data as default
            seed_json = str(Path(self.paths["odds_config"]).parent.parent / "data" / "seed" / "manual_odds_seed.json")
            seed_csv = str(Path(self.paths["odds_config"]).parent.parent / "data" / "seed" / "manual_odds_seed.csv")
            if Path(seed_json).exists():
                raw_snapshot = load_odds_from_json(seed_json)
            elif Path(seed_csv).exists():
                raw_snapshot = load_odds_from_csv(seed_csv)
            else:
                raw_snapshot = OddsSnapshot(snapshot_date=date, warnings=["No odds data available."])

        preview.odds_snapshot = _dataclass_to_dict(raw_snapshot)
        preview.warnings.extend(raw_snapshot.warnings)

        # 2. Normalize
        normalized = normalize_odds_entries(raw_snapshot.entries, config)
        preview.normalized_snapshot = _dataclass_to_dict(normalized)

        # 3. No-vig
        no_vig = build_no_vig_markets(normalized, config)
        preview.no_vig_summary = _dataclass_to_dict(no_vig)
        preview.warnings.extend(no_vig.warnings)

        # 4. Consensus
        consensus = build_market_consensus(normalized, no_vig, config)
        preview.consensus_summary = _dataclass_to_dict(consensus)
        preview.warnings.extend(consensus.warnings)

        # 5. Movement
        movement = analyze_odds_movement(normalized, config)
        preview.movement_summary = _dataclass_to_dict(movement)
        preview.warnings.extend(movement.warnings)

        # 6. Freshness
        freshness = check_odds_freshness(normalized, config)
        preview.freshness_summary = _dataclass_to_dict(freshness)
        preview.warnings.extend(freshness.warnings)

        # 7. Model vs market gap
        mp_path = Path(reports_dir) / "match_probability_preview.json"
        mp_data = {}
        if mp_path.exists():
            mp_data = json.loads(mp_path.read_text(encoding="utf-8"))
        gap = compute_model_vs_market_gap(normalized, mp_data, config)
        preview.model_vs_market_gap = _dataclass_to_dict(gap)
        preview.warnings.extend(gap.warnings)

        # 8. Safety
        preview.safety = {
            "campaign_analysis_only": True,
            "real_bet_execution": False,
            "auto_betting": False,
            "external_betting_api_allowed": False,
            "real_money_instruction_allowed": False,
            "network_fetch_default_enabled": config.get("data_source", {}).get("network_fetch_default_enabled", False),
            "analysis_only": True,
            "simulation_only": True,
            "not_betting_advice": True,
        }

        # 9. Write outputs
        self._write_outputs(preview, reports_dir)

        return preview

    def _write_outputs(self, preview: MarketOddsConsensusPreview, reports_dir: str):
        out_dir = Path(reports_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        json_path = out_dir / "market_odds_consensus.json"
        json_path.write_text(json.dumps(_dataclass_to_dict(preview), indent=2, ensure_ascii=False, default=str), encoding="utf-8")

        md_path = out_dir / "market_odds_consensus.md"
        md_path.write_text(self._render_markdown(preview), encoding="utf-8")

    def _render_markdown(self, preview: MarketOddsConsensusPreview) -> str:
        ns = preview.normalized_snapshot
        nv = preview.no_vig_summary
        cs = preview.consensus_summary
        ms = preview.movement_summary
        fs = preview.freshness_summary
        mg = preview.model_vs_market_gap

        lines = [
            "# Market Odds Consensus Report",
            "",
            f"**Date:** {preview.current_date} | **Bankroll:** {preview.current_bankroll}",
            "",
            "## 1. Odds Snapshot Summary",
            f"- Raw entries: {ns.get('raw_count', 0)}",
            f"- Normalized: {ns.get('normalized_count', 0)}",
            f"- Invalid: {ns.get('invalid_count', 0)}",
            f"- Source providers: {', '.join(ns.get('source_providers', []))}",
            "",
            "## 2. No-Vig Analysis",
            f"- Markets analyzed: {nv.get('market_count', 0)}",
            f"- Average overround: {nv.get('average_overround', 0):.4f}",
            f"- Max overround: {nv.get('max_overround', 0):.4f}",
            f"- High overround count: {nv.get('high_overround_count', 0)}",
            "",
            "## 3. Market Consensus",
            f"- Consensus markets: {cs.get('market_count', 0)}",
            f"- Strong consensus: {cs.get('strong_consensus_count', 0)}",
            f"- Usable consensus: {cs.get('usable_consensus_count', 0)}",
            f"- Weak consensus: {cs.get('weak_consensus_count', 0)}",
            f"- Dispersion warnings: {cs.get('dispersion_warning_count', 0)}",
            "",
            "## 4. Odds Movement",
            f"- Movement records: {ms.get('record_count', 0)}",
            f"- Significant moves: {ms.get('significant_move_count', 0)}",
            f"- Insufficient history: {ms.get('insufficient_history_count', 0)}",
            "",
            "## 5. Odds Freshness",
            f"- Fresh providers: {fs.get('fresh_count', 0)}",
            f"- Stale providers: {fs.get('stale_count', 0)}",
            f"- Oldest age: {fs.get('oldest_age_hours', 0)}h",
            f"- Freshness warnings: {fs.get('freshness_warning_count', 0)}",
            "",
            "## 6. Model vs Market Gap",
            f"- Gap records: {mg.get('record_count', 0)}",
            f"- Model above market: {mg.get('model_above_market_count', 0)}",
            f"- Model below market: {mg.get('model_below_market_count', 0)}",
            f"- Aligned: {mg.get('aligned_count', 0)}",
            f"- Average gap: {mg.get('average_gap', 0):.4f}",
            "",
            "## 7. Warnings",
        ]
        for w in preview.warnings:
            lines.append(f"- {w}")

        lines.extend([
            "",
            "## 8. Safety Boundary",
            f"- Analysis only: {preview.analysis_only}",
            f"- Simulation only: {preview.simulation_only}",
            f"- Not betting advice: {preview.not_betting_advice}",
            f"- Network fetch enabled: {preview.safety.get('network_fetch_default_enabled', False)}",
            "",
            "---",
            "*This is market odds analysis only. Not betting advice. No real bookmaker account used.*",
        ])
        return "\n".join(lines)
        return "\n".join(lines)
