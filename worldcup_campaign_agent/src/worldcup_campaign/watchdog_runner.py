"""Watchdog runner: loads sources, runs safety checks, outputs health report."""
import json, sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from worldcup_campaign.daily_ops_watchdog import (
    run_watchdog, WatchdogResult, FORBIDDEN_FIELDS
)


@dataclass
class DailyOpsWatchdogPreview:
    campaign_name: str = "worldcup_2026_high_odds_campaign"
    current_date: str = ""
    current_bankroll: float = 100.0
    mode: str = "full"
    source_health: dict = field(default_factory=dict)
    circuit_breaker: dict = field(default_factory=dict)
    review_queue: dict = field(default_factory=dict)
    quality_gate: dict = field(default_factory=dict)
    safety: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    generated_at: str = ""
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


def _d(obj):
    if hasattr(obj, '__dataclass_fields__'):
        return {k: _d(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_d(i) for i in obj]
    return obj


class WatchdogRunner:
    def __init__(self, config_path: str):
        self.config_path = config_path

    def run(self, date: str, bankroll: float, mode: str = "full"):
        config = json.loads(Path(self.config_path).read_text(encoding="utf-8-sig"))
        reports_dir = Path(self.config_path).resolve().parent.parent / "reports" / "generated"
        rp = reports_dir

        # Build source paths from config
        all_sources = config.get("sources", {})
        required = all_sources.get("required", [])
        optional = all_sources.get("optional", [])
        source_names = required + optional
        source_paths = {}
        for name in source_names:
            source_paths[name] = str(rp / name)

        # Load extra data for circuit breaker
        def _load_json(fname):
            p = rp / fname
            if p.exists():
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    return {}
            return {}

        sf_data = _load_json("signal_fusion_preview.json")
        me_data = _load_json("market_expectation.json")
        tn_data = _load_json("team_news_preview.json")

        # Filter sources by mode
        if mode == "pre_daily_ops":
            # Pre-ops: only check that base sources exist
            filtered_paths = {k: v for k, v in source_paths.items()
                            if k in required or "signal_fusion" in k or "market_expectation" in k}
        elif mode == "post_daily_ops":
            # Post-ops: check all post-run sources
            filtered_paths = source_paths
        else:
            filtered_paths = source_paths

        # Run watchdog
        result = run_watchdog(filtered_paths, config, sf_data, me_data, tn_data)

        preview = DailyOpsWatchdogPreview(
            current_date=date, current_bankroll=bankroll, mode=mode,
            generated_at=datetime.now().isoformat(),
            source_health=result.source_health,
            circuit_breaker=result.circuit_breaker,
            review_queue=result.review_queue,
            quality_gate=result.quality_gate,
            warnings=result.warnings if hasattr(result, 'warnings') else [],
            safety={
                "campaign_analysis_only": True,
                "real_bet_execution": False,
                "auto_betting": False,
                "network_fetch_default_enabled": False,
                "analysis_only": True,
                "simulation_only": True,
                "not_betting_advice": True,
            }
        )

        # Write outputs
        rp.mkdir(parents=True, exist_ok=True)
        output = _d(preview)
        (rp / "daily_ops_watchdog.json").write_text(
            json.dumps(output, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        (rp / "daily_ops_watchdog.md").write_text(self._render_md(preview), encoding="utf-8")

        # Self-check: ensure no forbidden fields in our own output
        ff_found = []
        def _scan(d, path=""):
            if isinstance(d, dict):
                for k, v in d.items():
                    if k in FORBIDDEN_FIELDS:
                        ff_found.append(f"{path}.{k}")
                    _scan(v, f"{path}.{k}" if path else k)
            elif isinstance(d, list):
                for i, item in enumerate(d):
                    _scan(item, f"{path}[{i}]")
        _scan(output)
        if ff_found:
            preview.warnings.append(f"Self-check: forbidden fields in output: {ff_found}")

        return preview

    def _render_md(self, p) -> str:
        sh = p.source_health; cb = p.circuit_breaker
        rq = p.review_queue; qg = p.quality_gate
        lines = [
            "# Daily Ops Watchdog & Circuit Breaker", "",
            f"**Date:** {p.current_date} | **Bankroll:** {p.current_bankroll} | **Mode:** {p.mode}", "",
            f"## Overall Status: **{cb.get('overall_status', 'UNKNOWN')}**", "",
            "---", "",
            "## 1. Source Health", "",
            f"- Sources: {sh.get('source_count',0)} total | {sh.get('available_count',0)} available | {sh.get('missing_count',0)} missing",
            f"- Valid: {sh.get('valid_count',0)} | Stale: {sh.get('stale_count',0)}",
            f"- Warnings: {sh.get('warning_count',0)} | Degraded: {sh.get('degraded_count',0)} | Blocked: {sh.get('blocked_count',0)}",
            f"- Status: {sh.get('overall_status','?')}", "",
            "| Source | Available | Valid | Stale | Status | Notes |",
            "|--------|-----------|-------|-------|--------|-------|",
        ]
        for item in sh.get("items", []):
            notes = "; ".join(item.get("notes", []))[:100]
            lines.append(f"| {item.get('source_name','')} | {item.get('available')} | {item.get('valid_json')} | {item.get('stale')} | {item.get('status','')} | {notes} |")

        lines.extend([
            "", "## 2. Circuit Breaker", "",
            f"- Status: **{cb.get('overall_status','?')}**",
            f"- Allowed to continue: {cb.get('allowed_to_continue')}",
            f"- Blocked from daily ops: {cb.get('blocked_from_daily_ops')}",
            f"- Blocked from strategy upgrade: {cb.get('blocked_from_strategy_upgrade')}",
            f"- Hard blocks: {cb.get('hard_block_count',0)}",
            f"- Degradations: {cb.get('degraded_count',0)}",
            f"- Warnings: {cb.get('warning_count',0)}", "",
        ])
        if cb.get("hard_blocks"):
            lines.append("### Hard Blocks")
            for b in cb["hard_blocks"]:
                lines.append(f"- BLOCKED: {str(b)[:200]}")
            lines.append("")
        if cb.get("degradations"):
            lines.append("### Degradations")
            for d in cb["degradations"]:
                lines.append(f"- DEGRADED: {str(d)[:200]}")
            lines.append("")
        if cb.get("warnings"):
            lines.append("### Warnings")
            for w in cb["warnings"]:
                lines.append(f"- WARN: {str(w)[:200]}")
            lines.append("")

        lines.extend([
            "## 3. Manual Review Queue", "",
            f"- Items: {rq.get('review_item_count',0)}",
            f"- Info: {rq.get('info_count',0)} | Warn: {rq.get('warn_count',0)} | Degraded: {rq.get('degraded_count',0)} | Block: {rq.get('block_count',0)}", "",
        ])

        lines.extend([
            "## 4. Quality Gate", "",
            f"- Status: **{qg.get('status','?')}**",
            f"- Pass: {qg.get('pass_count',0)} | Warn: {qg.get('warn_count',0)} | Degraded: {qg.get('degraded_count',0)} | Block: {qg.get('block_count',0)}", "",
        ])
        cats = qg.get("categories", {})
        if cats:
            lines.append("| Category | Status |")
            lines.append("|----------|--------|")
            for cat, status in cats.items():
                lines.append(f"| {cat} | {status} |")
            lines.append("")

        lines.extend([
            "## 5. Safety", "",
            f"- Analysis only: {p.analysis_only}",
            f"- Simulation only: {p.simulation_only}",
            f"- Not betting advice: {p.not_betting_advice}",
            f"- Real bet execution: False",
            f"- Auto betting: False",
            f"- Network fetch: False", "",
            "---", "",
            "*Daily Ops Watchdog. Safety gate, not execution. Not betting advice.*"
        ])
        return "\n".join(lines)
