"""Visual Command Center: aggregator, renderer, static HTML, runner."""
import json, sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from worldcup_campaign.visual_command_center_core import (
    VisualDashboardSources, VisualStatusSummary, VisualCandidateSummary,
    VisualReviewSummary, BankrollSeries, ReviewCountSeries,
    load_visual_dashboard_sources, build_status_summary,
    build_candidate_cards, build_review_cards,
    build_bankroll_series, build_review_count_series,
    _d, _load_json, _scan_forbidden, ROOT, FORBIDDEN
)


@dataclass
class VisualCommandCenterSnapshot:
    campaign_name: str="worldcup_2026_high_odds_campaign"
    frontend_mode: str="local_only"
    local_url: str="http://localhost:8501"
    fallback_html_path: str="reports/generated/visual_command_center.html"
    generated_at: str=""
    status_summary: Optional[VisualStatusSummary]=None
    candidate_summary: Optional[VisualCandidateSummary]=None
    review_summary: Optional[VisualReviewSummary]=None
    bankroll_series: Optional[BankrollSeries]=None
    review_count_series: Optional[ReviewCountSeries]=None
    artifact_source_count: int=0
    warnings: list=field(default_factory=list)
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True
    real_money_execution_ready: bool=False


def build_visual_snapshot(config_paths=None):
    snap = VisualCommandCenterSnapshot(generated_at=datetime.now().isoformat())
    cfg = _load_json(ROOT / "config" / "visual_command_center_config.json") or {}
    sources = load_visual_dashboard_sources(cfg)
    snap.status_summary = build_status_summary(sources)
    snap.candidate_summary = build_candidate_cards(sources)
    snap.review_summary = build_review_cards(sources)
    snap.bankroll_series = build_bankroll_series(sources)
    snap.review_count_series = build_review_count_series(sources)
    snap.artifact_source_count = sources.available_count
    for s in sources.sources:
        if s.warnings: snap.warnings.extend(s.warnings)
    return snap


def render_visual_json(snap):
    out = {
        "campaign_name": snap.campaign_name, "frontend_mode": snap.frontend_mode,
        "local_url": snap.local_url, "fallback_html_path": snap.fallback_html_path,
        "generated_at": snap.generated_at,
        "analysis_only": True, "simulation_only": True, "not_betting_advice": True,
        "real_money_execution_ready": False,
    }
    if snap.status_summary: out["status_summary"] = _d(snap.status_summary)
    if snap.candidate_summary: out["candidate_summary"] = _d(snap.candidate_summary)
    if snap.review_summary: out["review_summary"] = _d(snap.review_summary)
    if snap.bankroll_series: out["bankroll_series"] = _d(snap.bankroll_series)
    if snap.review_count_series: out["review_count_series"] = _d(snap.review_count_series)
    out["artifact_source_count"] = snap.artifact_source_count
    out["warnings"] = snap.warnings
    return out


def render_visual_markdown(snap):
    L = ["# Visual Command Center", ""]
    L.append("## 1. Status Summary")
    if snap.status_summary:
        ss = snap.status_summary
        L.append("**Overall:** " + ss.overall_status + " (" + ss.status_color + ")")
        L.append("| Card | Status | Color |")
        L.append("|---|---|---|")
        for c in ss.status_cards:
            L.append("| " + c.label + " | " + c.status + " | " + c.color + " |")
    L.append("")
    L.append("## 2. Today Overview")
    L.append("- **Local URL:** " + snap.local_url)
    L.append("")
    L.append("## 3. Strategy Candidates")
    if snap.candidate_summary:
        cs = snap.candidate_summary
        L.append("**Total:** " + str(cs.candidate_count) + " | Core: " + str(cs.core_count) + " | Edge: " + str(cs.edge_count))
    L.append("")
    L.append("## 4. Review Queue")
    if snap.review_summary:
        rs = snap.review_summary
        L.append("**Total:** " + str(rs.review_count) + " | Open: " + str(rs.open_count))
    L.append("")
    L.append("## 5. Safety Boundary")
    L.append("- analysis_only: true | simulation_only: true | not_betting_advice: true | real_money_execution_ready: false")
    return "\n".join(L)


def render_static_html(snap):
    ss = snap.status_summary
    cs = snap.candidate_summary
    rs = snap.review_summary
    bs = snap.bankroll_series

    cards_html = ""
    if ss:
        for c in ss.status_cards:
            cards_html += '<div class="status-card ' + c.color + '"><div class="card-label">' + c.label + '</div><div class="card-value">' + c.status + '</div></div>\n'

    candidate_rows = ""
    if cs:
        for c in cs.candidate_cards[:20]:
            candidate_rows += '<tr><td>' + str(c.match_id) + '</td><td>' + str(c.market_type) + '</td><td>' + str(c.selection_label) + '</td><td><span class="bucket ' + str(c.bucket) + '">' + str(c.bucket) + '</span></td><td>' + f"{c.campaign_score:.3f}" + '</td><td>' + str(c.confidence) + '</td><td>' + str(c.simulation_budget_preview) + '</td></tr>\n'

    review_rows = ""
    if rs:
        for r in rs.review_cards[:20]:
            sc = "sev-" + str(r.severity)
            review_rows += '<tr><td>' + str(r.review_id) + '</td><td>' + str(r.review_type) + '</td><td><span class="' + sc + '">' + str(r.severity) + '</span></td><td>' + str(r.reason)[:80] + '</td><td>' + str(r.status) + '</td></tr>\n'

    bankroll_html = ""
    if bs and bs.point_count > 0:
        bankroll_html = "<p>Bankroll series: " + str(bs.point_count) + " data points</p>\n"
        bankroll_html += '<table><tr><th>Date</th><th>Bankroll</th></tr>\n'
        for i in range(min(bs.point_count, 30)):
            bankroll_html += '<tr><td>' + str(bs.dates[i]) + '</td><td>' + f"{bs.values[i]:.1f}" + '</td></tr>\n'
        bankroll_html += '</table>\n'

    cc = cs.candidate_count if cs else 0
    ccore = cs.core_count if cs else 0
    cedge = cs.edge_count if cs else 0
    cattack = cs.attack_count if cs else 0
    rtotal = rs.review_count if rs else 0
    ropen = rs.open_count if rs else 0
    rcrit = rs.critical_count if rs else 0

    html = "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
    html += '<meta charset="UTF-8">\n'
    html += '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    html += "<title>WorldCup Campaign - Visual Command Center</title>\n"
    html += "<style>\n"
    html += "*{box-sizing:border-box;margin:0;padding:0}\n"
    html += "body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;background:#0f1923;color:#e0e0e0;padding:20px}\n"
    html += ".safety-banner{background:#1a3a1a;border:2px solid #2d5a2d;padding:12px 20px;margin-bottom:20px;border-radius:8px;font-size:13px;display:flex;gap:20px;flex-wrap:wrap}\n"
    html += ".safety-banner span{color:#4caf50;font-weight:bold}\n"
    html += "h1{color:#fff;margin-bottom:20px;font-size:24px}\n"
    html += "h2{color:#ccc;margin:20px 0 10px;font-size:18px;border-bottom:1px solid #333;padding-bottom:5px}\n"
    html += ".status-grid{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}\n"
    html += ".status-card{padding:16px;border-radius:8px;min-width:140px;text-align:center}\n"
    html += ".status-card.green{background:#1a3a1a;border:1px solid #2d5a2d}\n"
    html += ".status-card.yellow{background:#3a3a1a;border:1px solid #5a5a2d}\n"
    html += ".status-card.orange{background:#3a2a1a;border:1px solid #5a3a2d}\n"
    html += ".status-card.red{background:#3a1a1a;border:1px solid #5a2d2d}\n"
    html += ".status-card.gray{background:#2a2a2a;border:1px solid #444}\n"
    html += ".card-label{font-size:11px;text-transform:uppercase;color:#999;margin-bottom:4px}\n"
    html += ".card-value{font-size:18px;font-weight:bold;color:#fff}\n"
    html += "table{width:100%;border-collapse:collapse;margin:10px 0;font-size:13px}\n"
    html += "th{background:#1a2a3a;padding:8px;text-align:left;color:#aaa;font-weight:600}\n"
    html += "td{padding:8px;border-bottom:1px solid #222}\ntr:hover{background:#1a2a3a}\n"
    html += ".bucket{padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}\n"
    html += ".bucket.core,.bucket.Core{background:#1a3a5a;color:#64b5f6}\n"
    html += ".bucket.edge,.bucket.Edge{background:#3a2a1a;color:#ffb74d}\n"
    html += ".bucket.attack,.bucket.Attack{background:#3a1a1a;color:#ef5350}\n"
    html += ".bucket.futures,.bucket.Futures,.bucket.watch_only{background:#2a2a3a;color:#9e9e9e}\n"
    html += ".sev-critical{color:#ef5350;font-weight:bold}\n.sev-high{color:#ff9800;font-weight:bold}\n"
    html += ".sev-medium{color:#ffeb3b}\n.sev-low{color:#9e9e9e}\n"
    html += ".disclaimer{margin-top:30px;padding:12px;background:#1a1a2a;border:1px solid #333;border-radius:8px;font-size:12px;color:#888}\n"
    html += "</style>\n</head>\n<body>\n"
    html += '<div class="safety-banner">\n'
    html += "<span>ANALYSIS ONLY</span> <span>SIMULATION ONLY</span> <span>NOT BETTING ADVICE</span> <span>REAL MONEY: FALSE</span>\n"
    html += "</div>\n"
    html += "<h1>WorldCup Campaign - Visual Command Center</h1>\n"
    html += '<div class="status-grid">\n' + cards_html + "</div>\n"
    html += "<h2>Strategy Candidates</h2>\n"
    html += "<p>Total: " + str(cc) + " | Core: " + str(ccore) + " | Edge: " + str(cedge) + " | Attack: " + str(cattack) + "</p>\n"
    html += "<table><tr><th>Match</th><th>Market</th><th>Selection</th><th>Bucket</th><th>Score</th><th>Conf</th><th>Budget (sim)</th></tr>" + candidate_rows + "</table>\n"
    html += "<h2>Review Queue</h2>\n"
    html += "<p>Total: " + str(rtotal) + " | Open: " + str(ropen) + " | Critical: " + str(rcrit) + "</p>\n"
    html += "<table><tr><th>ID</th><th>Type</th><th>Severity</th><th>Reason</th><th>Status</th></tr>" + review_rows + "</table>\n"
    html += "<h2>Bankroll Timeline</h2>\n" + bankroll_html + "\n"
    html += '<div class="disclaimer">\n'
    html += "This is a <strong>simulation/analysis-only</strong> dashboard. No real bets are placed. No real money is used. Not betting advice. real_money_execution_ready=false.\n"
    html += "</div>\n</body>\n</html>"
    return html


def validate_visual_no_forbidden(payload):
    return _scan_forbidden(payload)


def write_visual_outputs(snap, output_dir=None):
    if output_dir is None: output_dir = ROOT / "reports" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    jp = output_dir / "visual_command_center.json"
    jp.write_text(json.dumps(render_visual_json(snap), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    paths["json"] = str(jp)
    mp = output_dir / "visual_command_center.md"
    mp.write_text(render_visual_markdown(snap), encoding="utf-8")
    paths["md"] = str(mp)
    hp = output_dir / "visual_command_center.html"
    hp.write_text(render_static_html(snap), encoding="utf-8")
    paths["html"] = str(hp)
    return paths


class VisualCommandCenterRunner:
    def run(self):
        return build_visual_snapshot()
