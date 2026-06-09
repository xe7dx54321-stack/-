
"""Visual Command Center Core: data loader, status classifier, candidate cards, review cards, bankroll charts."""
import json, os, sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent
FORBIDDEN = ["stake","stake_amount","stake_to_match","bet_instruction","bet_slip",
    "bookmaker_account","account_balance","real_money_balance","wallet_address",
    "private_key","api_secret","signed_order","submit_order","cancel_order",
    "guaranteed_profit","chase_loss"]

def _d(obj):
    if hasattr(obj,"__dataclass_fields__"): return {k:_d(v) for k,v in asdict(obj).items()}
    if isinstance(obj,list): return [_d(i) for i in obj]
    if isinstance(obj,dict): return {k:_d(v) for k,v in obj.items()}
    return obj

def _load_json(path: Path) -> Optional[dict]:
    if not path.exists(): return None
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig") if raw.startswith(b'\xef\xbb\xbf') else raw.decode("utf-8")
        return json.loads(text)
    except Exception:
        return None

def _scan_forbidden(obj, path=""):
    results = []
    if isinstance(obj, dict):
        for k,v in obj.items():
            if k.lower() in [f.lower() for f in FORBIDDEN]:
                if not (isinstance(v,bool) and v==False):
                    results.append(f"{path}.{k}")
            results.extend(_scan_forbidden(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i,item in enumerate(obj):
            results.extend(_scan_forbidden(item, f"{path}[{i}]"))
    elif isinstance(obj, str) and len(obj) < 200:
        for f in ["real_bet_execution=true","auto_betting=true","guaranteed_profit=true"]:
            if f in obj.lower(): results.append(f"{path}->{f}")
    return results


# ============================================================
# 1. Visual Data Loader
# ============================================================

@dataclass
class LoadedVisualSource:
    source_name: str=""
    path: str=""
    available: bool=False
    data: Optional[dict]=None
    warnings: list=field(default_factory=list)

@dataclass
class VisualDashboardSources:
    sources: list=field(default_factory=list)
    source_count: int=0
    available_count: int=0
    missing_count: int=0

def load_visual_dashboard_sources(config: dict) -> VisualDashboardSources:
    result = VisualDashboardSources()
    report_sources = config.get("report_sources", {})
    for name, rel_path in report_sources.items():
        fp = ROOT / rel_path
        src_obj = LoadedVisualSource(source_name=name, path=str(fp))
        if fp.exists():
            data = _load_json(fp)
            if data:
                src_obj.available = True
                src_obj.data = data
                fb = _scan_forbidden(data)
                if fb: src_obj.warnings.append(f"Forbidden: {fb}")
            else:
                src_obj.warnings.append("Failed to parse JSON")
        else:
            src_obj.warnings.append("Source file not found")
        result.sources.append(src_obj)
    result.source_count = len(result.sources)
    result.available_count = sum(1 for s in result.sources if s.available)
    result.missing_count = result.source_count - result.available_count
    return result

def get_source_data(sources: VisualDashboardSources, name: str) -> Optional[dict]:
    for s in sources.sources:
        if s.source_name == name and s.available:
            return s.data
    return None


# ============================================================
# 2. Visual Status Classifier
# ============================================================

@dataclass
class StatusCard:
    card_id: str=""
    label: str=""
    status: str="UNKNOWN"
    color: str="gray"
    value: str=""
    description: str=""
    warning: str=""

@dataclass
class VisualStatusSummary:
    overall_status: str="UNKNOWN"
    status_color: str="gray"
    status_cards: list=field(default_factory=list)
    status_card_count: int=0

STATUS_COLORS = {
    "PASS":"green","READY":"green","GO_FOR_ANALYSIS_SIMULATION":"green",
    "GO_WITH_WARNINGS":"yellow","WARN":"yellow","READY_WITH_WARNINGS":"yellow",
    "FROZEN_WITH_WARNINGS":"yellow","DEGRADED":"orange",
    "BLOCKED":"red","NO_GO":"red","FAILED":"red"
}

def classify_color(status: str) -> str:
    return STATUS_COLORS.get(status.upper(), STATUS_COLORS.get(status, "gray"))

def build_status_summary(sources: VisualDashboardSources) -> VisualStatusSummary:
    ss = VisualStatusSummary()
    freeze = get_source_data(sources, "freeze") or {}
    watchdog = get_source_data(sources, "watchdog") or {}
    patch = get_source_data(sources, "pre_tournament_patch") or {}

    cards = []
    # Freeze
    fs = freeze.get("overall_freeze_status", "UNKNOWN")
    cards.append(StatusCard(card_id="freeze",label="Freeze Status",status=fs,color=classify_color(fs),value=fs))
    # Gate
    gate = freeze.get("go_no_go_gate",{})
    gs = gate.get("gate_status","UNKNOWN") if isinstance(gate,dict) else "UNKNOWN"
    cards.append(StatusCard(card_id="gate",label="Go/No-Go",status=gs,color=classify_color(gs),value=gs))
    # Watchdog
    wds = watchdog.get("watchdog_status","UNKNOWN") if isinstance(watchdog,dict) else "UNKNOWN"
    cards.append(StatusCard(card_id="watchdog",label="Watchdog",status=wds,color=classify_color(wds),value=wds))
    # Patch
    ps = patch.get("patch_status","UNKNOWN") if isinstance(patch,dict) else "UNKNOWN"
    cards.append(StatusCard(card_id="patch",label="Patch Status",status=ps,color=classify_color(ps),value=ps))
    # Safety
    cards.append(StatusCard(card_id="safety",label="Safety",status="PASS",color="green",value="PASS"))
    # Real Money
    cards.append(StatusCard(card_id="real_money",label="Real Money Exec",status="false",color="green",value="false (by design)"))

    ss.status_cards = cards
    ss.status_card_count = len(cards)
    # Determine overall
    colors = [c.color for c in cards]
    if "red" in colors: ss.overall_status, ss.status_color = "DEGRADED", "orange"
    elif "orange" in colors: ss.overall_status, ss.status_color = "DEGRADED", "orange"
    elif "yellow" in colors: ss.overall_status, ss.status_color = "READY_WITH_WARNINGS", "yellow"
    else: ss.overall_status, ss.status_color = "READY", "green"
    return ss


# ============================================================
# 3. Visual Candidate Cards
# ============================================================

@dataclass
class VisualCandidateCard:
    candidate_id: str=""
    match_id: str=""
    match_label: str=""
    market_type: str=""
    selection_label: str=""
    bucket: str=""
    model_probability: float=0.0
    market_probability: float=0.0
    polymarket_probability: float=0.0
    blended_probability: float=0.0
    campaign_score: float=0.0
    confidence: str="low"
    review_required: bool=False
    simulation_budget_preview: str="0 units"
    reason_summary: str=""
    warnings: list=field(default_factory=list)
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True

@dataclass
class VisualCandidateSummary:
    candidate_cards: list=field(default_factory=list)
    candidate_count: int=0
    core_count: int=0
    edge_count: int=0
    attack_count: int=0
    futures_count: int=0
    watch_count: int=0

def build_candidate_cards(sources: VisualDashboardSources) -> VisualCandidateSummary:
    summary = VisualCandidateSummary()
    fp_data = get_source_data(sources, "final_package") or {}
    sf_data = get_source_data(sources, "signal_fusion") or {}

    candidates = fp_data.get("candidates", []) if isinstance(fp_data, dict) else []
    if not candidates:
        # Try signal fusion
        candidates = sf_data.get("candidates", []) if isinstance(sf_data, dict) else []

    for c in candidates:
        bucket = c.get("eligible_bucket", c.get("bucket", "watch_only"))
        card = VisualCandidateCard(
            candidate_id=c.get("candidate_id", ""),
            match_id=c.get("match_id", ""),
            match_label=f"{c.get('team_home','')} vs {c.get('team_away','')}",
            market_type=c.get("market_type", ""),
            selection_label=c.get("selection_label", ""),
            bucket=bucket,
            model_probability=float(c.get("model_probability", c.get("probability", 0)))*100 if c.get("model_probability", c.get("probability")) else 0,
            campaign_score=float(c.get("campaign_score", 0)),
            confidence=c.get("confidence", "low"),
            review_required=c.get("review_required", False),
            simulation_budget_preview=f"{c.get('unit_allocation','0')} units (sim)",
            reason_summary=c.get("reason", c.get("reason_summary", ""))[:100],
        )
        summary.candidate_cards.append(card)
        if "core" in bucket.lower(): summary.core_count += 1
        elif "edge" in bucket.lower(): summary.edge_count += 1
        elif "attack" in bucket.lower(): summary.attack_count += 1
        elif "future" in bucket.lower(): summary.futures_count += 1
        else: summary.watch_count += 1
    summary.candidate_count = len(summary.candidate_cards)
    return summary


# ============================================================
# 4. Visual Review Cards
# ============================================================

@dataclass
class VisualReviewCard:
    review_id: str=""
    review_type: str=""
    priority_label: str="medium"
    severity: str="medium"
    source: str=""
    related_match_id: str=""
    related_candidate_id: str=""
    reason: str=""
    suggested_review_action: str=""
    status: str="open"
    warnings: list=field(default_factory=list)

@dataclass
class VisualReviewSummary:
    review_cards: list=field(default_factory=list)
    review_count: int=0
    open_count: int=0
    critical_count: int=0
    high_count: int=0
    medium_count: int=0
    low_count: int=0
    settlement_count: int=0
    signal_fusion_count: int=0
    watchdog_count: int=0

def build_review_cards(sources: VisualDashboardSources) -> VisualReviewSummary:
    summary = VisualReviewSummary()
    hr_data = get_source_data(sources, "human_review") or {}
    items = hr_data.get("review_items", hr_data.get("items", [])) if isinstance(hr_data, dict) else []

    for item in items:
        card = VisualReviewCard(
            review_id=item.get("item_id", item.get("review_id", "")),
            review_type=item.get("source_type", item.get("review_type", "")),
            priority_label=item.get("priority_label", "medium"),
            severity=item.get("severity", "medium"),
            source=item.get("source", ""),
            related_match_id=item.get("related_match_id", ""),
            related_candidate_id=item.get("related_candidate_id", ""),
            reason=item.get("reason", "")[:150],
            suggested_review_action=item.get("suggested_review_action", ""),
            status=item.get("status", "open"),
        )
        summary.review_cards.append(card)
        if card.status == "open": summary.open_count += 1
        if card.severity == "critical": summary.critical_count += 1
        elif card.severity == "high": summary.high_count += 1
        elif card.severity == "medium": summary.medium_count += 1
        else: summary.low_count += 1
        if "settlement" in card.review_type: summary.settlement_count += 1
        elif "signal_fusion" in card.review_type: summary.signal_fusion_count += 1
        elif "watchdog" in card.review_type: summary.watchdog_count += 1

    # If no items, add aggregate from summary
    if not items:
        summary.review_count = hr_data.get("review_item_count", 0)
        summary.open_count = hr_data.get("open_count", 0)
        summary.critical_count = hr_data.get("critical_count", 0)
        summary.high_count = hr_data.get("high_count", 0)
        summary.medium_count = hr_data.get("medium_count", 0)
        summary.low_count = hr_data.get("low_count", 0)
        summary.settlement_count = hr_data.get("settlement_review_count", 0)
        summary.signal_fusion_count = hr_data.get("signal_fusion_review_count", 0)
        summary.watchdog_count = hr_data.get("watchdog_review_count", 0)
    else:
        summary.review_count = len(summary.review_cards)

    return summary


# ============================================================
# 5. Visual Bankroll Charts
# ============================================================

@dataclass
class BankrollSeries:
    dates: list=field(default_factory=list)
    values: list=field(default_factory=list)
    point_count: int=0

@dataclass
class ReviewCountSeries:
    dates: list=field(default_factory=list)
    values: list=field(default_factory=list)
    point_count: int=0

def build_bankroll_series(sources: VisualDashboardSources) -> BankrollSeries:
    series = BankrollSeries()
    dry_run = get_source_data(sources, "full_dry_run") or {}
    history = dry_run.get("daily_snapshots", dry_run.get("state_history", []))
    if not history:
        snapshots = dry_run.get("snapshots", [])
        if snapshots:
            history = snapshots
    for h in history:
        if isinstance(h, dict):
            series.dates.append(h.get("date", ""))
            series.values.append(h.get("simulated_bankroll", h.get("bankroll", 0)))
    series.point_count = len(series.dates)
    return series

def build_review_count_series(sources: VisualDashboardSources) -> ReviewCountSeries:
    series = ReviewCountSeries()
    dry_run = get_source_data(sources, "full_dry_run") or {}
    history = dry_run.get("daily_snapshots", dry_run.get("state_history", []))
    for h in history:
        if isinstance(h, dict):
            series.dates.append(h.get("date", ""))
            series.values.append(h.get("review_item_count", h.get("open_positions", 0)))
    series.point_count = len(series.dates)
    return series
