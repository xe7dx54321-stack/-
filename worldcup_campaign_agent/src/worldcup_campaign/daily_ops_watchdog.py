"""Daily Ops Watchdog & Circuit Breaker — safety gate before daily operations."""
import json
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any


FORBIDDEN_FIELDS = [
    "stake", "stake_amount", "stake_to_match", "bet_instruction", "bet_slip",
    "bookmaker_account", "account_balance", "real_money_balance",
    "wallet_address", "private_key", "api_secret",
    "signed_order", "submit_order", "cancel_order",
    "guaranteed_profit", "chase_loss"
]

BLOCKED_EXECUTION_FLAGS = [
    "real_bet_execution", "auto_betting",
    "real_money_instruction_allowed", "external_betting_api_allowed"
]

BLOCKED_VALUES = {True, "true", 1, "1", "yes"}


# ============================================================
# Data classes
# ============================================================

@dataclass
class SourceHealthItem:
    source_name: str = ""
    available: bool = False
    valid_json: bool = False
    missing: bool = True
    stale: bool = False
    stale_hours: float = 0.0
    forbidden_fields_found: list = field(default_factory=list)
    real_execution_flag_issue: bool = False
    status: str = "unknown"  # available / missing / stale / invalid / blocked
    notes: list = field(default_factory=list)


@dataclass
class SourceHealthSummary:
    items: list = field(default_factory=list)
    source_count: int = 0
    available_count: int = 0
    missing_count: int = 0
    valid_count: int = 0
    stale_count: int = 0
    warning_count: int = 0
    degraded_count: int = 0
    blocked_count: int = 0
    overall_status: str = "PASS"


@dataclass
class ForbiddenFieldFinding:
    source: str = ""
    field: str = ""
    severity: str = "block"
    context: str = ""


@dataclass
class CircuitBreakerResult:
    overall_status: str = "PASS"  # PASS / WARN / DEGRADED / BLOCKED
    hard_block_count: int = 0
    degraded_count: int = 0
    warning_count: int = 0
    allowed_to_continue: bool = True
    blocked_from_daily_ops: bool = False
    blocked_from_strategy_upgrade: bool = False
    hard_blocks: list = field(default_factory=list)
    degradations: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    decisions: list = field(default_factory=list)


@dataclass
class ReviewItem:
    item_id: str = ""
    category: str = ""
    source: str = ""
    severity: str = "info"  # info / warn / degraded / block
    description: str = ""
    recommendation: str = ""


@dataclass
class ReviewQueue:
    items: list = field(default_factory=list)
    review_item_count: int = 0
    info_count: int = 0
    warn_count: int = 0
    degraded_count: int = 0
    block_count: int = 0


@dataclass
class QualityGate:
    status: str = "PASS"  # PASS / WARN / DEGRADED / BLOCKED
    pass_count: int = 0
    warn_count: int = 0
    degraded_count: int = 0
    block_count: int = 0
    categories: dict = field(default_factory=dict)


@dataclass
class WatchdogResult:
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


# ============================================================
# Helpers
# ============================================================

def _deep_scan_for_fields(obj: Any, fields: set, current_path: str = "", findings: list = None) -> list:
    """Recursively scan a JSON object for forbidden fields."""
    if findings is None:
        findings = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{current_path}.{k}" if current_path else k
            if k in fields:
                findings.append(ForbiddenFieldFinding(source=p, field=k, severity="block",
                                                       context=f"value={str(v)[:80]}"))
            _deep_scan_for_fields(v, fields, p, findings)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _deep_scan_for_fields(item, fields, f"{current_path}[{i}]", findings)
    return findings


def _scan_execution_flags(obj: Any, flags: set, blocked_values: set, current_path: str = "", findings: list = None) -> list:
    """Scan for real execution flags with blocked values."""
    if findings is None:
        findings = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{current_path}.{k}" if current_path else k
            if k in flags and v in blocked_values:
                findings.append(ForbiddenFieldFinding(source=p, field=k, severity="block",
                                                       context=f"real_execution_flag={v}"))
            _scan_execution_flags(v, flags, blocked_values, p, findings)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _scan_execution_flags(item, flags, blocked_values, f"{current_path}[{i}]", findings)
    return findings


def _check_score_range(data: dict, findings: list, source_name: str) -> None:
    """Check that fusion/campaign scores are in 0-1."""
    def _scan_scores(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("base_campaign_score", "upgraded_campaign_score", "fusion_score",
                         "normalized_base_campaign_score", "campaign_score"):
                    if isinstance(v, (int, float)) and (v < 0.0 or v > 1.0):
                        findings.append(f"score_out_of_range: {path}.{k}={v} in {source_name}")
                _scan_scores(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _scan_scores(item, f"{path}[{i}]")
    _scan_scores(data)


# ============================================================
# Core checks
# ============================================================

def run_source_health_check(source_paths: dict, required: list, config: dict) -> SourceHealthSummary:
    """Check all source files for availability, validity, freshness, and safety."""
    summary = SourceHealthSummary()
    stale_threshold = config.get("checks", {}).get("source_health", {}).get("stale_threshold_hours", 24)
    now = datetime.now()
    forbidden_set = set(FORBIDDEN_FIELDS)
    exec_flags_set = set(BLOCKED_EXECUTION_FLAGS)

    for name, path_str in source_paths.items():
        item = SourceHealthItem(source_name=name)
        p = Path(path_str) if isinstance(path_str, str) else path_str

        if not p.exists():
            item.missing = True
            item.status = "missing"
            summary.missing_count += 1
            if name in required:
                summary.warning_count += 1
                item.notes.append("required_source_missing")
        else:
            item.missing = False
            item.available = True
            summary.available_count += 1

            # JSON validity
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                item.valid_json = True
                summary.valid_count += 1
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                item.valid_json = False
                item.status = "invalid"
                summary.blocked_count += 1
                item.notes.append(f"malformed_json: {str(e)[:100]}")
                summary.items.append(item)
                continue

            # Forbidden field scan
            ff_findings = _deep_scan_for_fields(data, forbidden_set)
            if ff_findings:
                item.forbidden_fields_found = [f.field for f in ff_findings]
                item.status = "blocked"
                summary.blocked_count += 1
                item.notes.append(f"forbidden_fields: {item.forbidden_fields_found}")

            # Real execution flag scan
            ef_findings = _scan_execution_flags(data, exec_flags_set, BLOCKED_VALUES)
            if ef_findings:
                item.real_execution_flag_issue = True
                item.status = "blocked"
                summary.blocked_count += 1
                item.notes.append("real_execution_flag_detected")

            # Score range check
            score_issues = []
            _check_score_range(data, score_issues, name)
            if score_issues:
                item.status = "blocked"
                summary.blocked_count += 1
                item.notes.extend(score_issues)

            # Staleness check
            try:
                mtime = datetime.fromtimestamp(p.stat().st_mtime)
                age = (now - mtime).total_seconds() / 3600.0
                item.stale_hours = round(age, 1)
                if age > stale_threshold:
                    item.stale = True
                    summary.stale_count += 1
                    if item.status not in ("blocked", "invalid"):
                        item.status = "stale"
                    item.notes.append(f"stale: {age:.1f}h > {stale_threshold}h")
                else:
                    if item.status == "unknown":
                        item.status = "available"
            except Exception:
                item.stale = True
                summary.stale_count += 1

            if item.status == "unknown":
                item.status = "available"

        summary.items.append(item)

    summary.source_count = len(source_paths)

    # Determine overall status
    if summary.blocked_count > 0:
        summary.overall_status = "BLOCKED"
    elif summary.missing_count > 0 and any(n in required for n in [i.source_name for i in summary.items if i.missing]):
        summary.overall_status = "DEGRADED"
    elif summary.stale_count > 0 or summary.warning_count > 0:
        summary.overall_status = "WARN"
    else:
        summary.overall_status = "PASS"

    return summary


def run_circuit_breaker(source_health: SourceHealthSummary, signal_fusion_data: dict,
                        market_expectation_data: dict, team_news_data: dict,
                        config: dict) -> CircuitBreakerResult:
    """Run circuit breaker checks and determine overall status."""
    cb = CircuitBreakerResult()
    cb_cfg = config.get("checks", {})

    # Hard blocks from source health
    for item in source_health.items:
        if item.status == "blocked":
            cb.hard_blocks.append(f"{item.source_name}: {item.notes}")
            cb.hard_block_count += 1
        elif item.status == "invalid":
            cb.hard_blocks.append(f"{item.source_name}: malformed_json")
            cb.hard_block_count += 1

    # Score range check from signal fusion
    sf_cfg = cb_cfg.get("signal_fusion_score_guard", {})
    if sf_cfg.get("enabled", True):
        fusion = signal_fusion_data.get("fusion_summary", signal_fusion_data)
        candidates = fusion.get("candidates", [])
        for c in candidates:
            for score_field in ("base_campaign_score", "upgraded_campaign_score", "fusion_score"):
                val = c.get(score_field)
                if isinstance(val, (int, float)) and (val < 0.0 or val > 1.0):
                    cb.hard_blocks.append(f"score_out_of_range: {c.get('candidate_id','')}.{score_field}={val}")
                    cb.hard_block_count += 1

    # Review queue check
    rq_cfg = cb_cfg.get("review_queue", {})
    if rq_cfg.get("enabled", True):
        fusion = signal_fusion_data.get("fusion_summary", signal_fusion_data)
        total = fusion.get("candidate_count", 1) or 1
        review_count = fusion.get("review_required_count", 0)
        if review_count / total > rq_cfg.get("max_review_ratio", 0.8):
            cb.warnings.append(f"review_queue_large: {review_count}/{total}")
            cb.warning_count += 1

    # Unexplained disagreement check
    ud_cfg = cb_cfg.get("unexplained_disagreement", {})
    if ud_cfg.get("enabled", True):
        fusion = signal_fusion_data.get("fusion_summary", signal_fusion_data)
        total = fusion.get("candidate_count", 1) or 1
        ud_count = fusion.get("unexplained_disagreement_count", 0)
        if ud_count / total > ud_cfg.get("max_ratio", 0.9):
            cb.warnings.append(f"unexplained_disagreement_high: {ud_count}/{total}")
            cb.warning_count += 1

    # Abnormal promotion check
    ap_cfg = cb_cfg.get("abnormal_promotion", {})
    if ap_cfg.get("enabled", True):
        fusion = signal_fusion_data.get("fusion_summary", signal_fusion_data)
        total = fusion.get("candidate_count", 1) or 1
        promoted = fusion.get("promoted_count", 0)
        if promoted / total > ap_cfg.get("max_promotion_ratio", 0.5):
            cb.degradations.append(f"abnormal_promotion_ratio: {promoted}/{total}")
            cb.degraded_count += 1

    # Market expectation quality
    me_cfg = cb_cfg.get("market_expectation_quality", {})
    if me_cfg.get("enabled", True):
        me = market_expectation_data
        avg_qual = me.get("signal_quality_summary", {}).get("average_quality_score", 0.5)
        if avg_qual < me_cfg.get("min_avg_quality_score", 0.3):
            cb.degradations.append(f"low_market_expectation_quality: {avg_qual}")
            cb.degraded_count += 1

    # Team news rumor ratio
    tn_cfg = cb_cfg.get("team_news_reliability", {})
    if tn_cfg.get("enabled", True):
        tn = team_news_data
        rumor_count = tn.get("news_summary", {}).get("rumor_count", 0)
        total_news = tn.get("news_summary", {}).get("total_news_count", 1) or 1
        if rumor_count / total_news > tn_cfg.get("max_rumor_ratio", 0.5):
            cb.warnings.append(f"team_news_high_rumor: {rumor_count}/{total_news}")
            cb.warning_count += 1

    # Determine overall status
    if cb.hard_block_count > 0:
        cb.overall_status = "BLOCKED"
        cb.allowed_to_continue = False
        cb.blocked_from_daily_ops = True
        cb.blocked_from_strategy_upgrade = True
    elif cb.degraded_count > 0:
        cb.overall_status = "DEGRADED"
        cb.blocked_from_strategy_upgrade = True
    elif cb.warning_count > 0:
        cb.overall_status = "WARN"
    else:
        cb.overall_status = "PASS"

    return cb


def build_review_queue(source_health: SourceHealthSummary, circuit_breaker: CircuitBreakerResult,
                       signal_fusion_data: dict, config: dict) -> ReviewQueue:
    """Build manual review queue from all findings."""
    rq = ReviewQueue()

    # Items from source health
    for item in source_health.items:
        if item.missing:
            sev = "degraded" if item.source_name in config.get("sources", {}).get("required", []) else "warn"
            rq.items.append(ReviewItem(
                item_id=f"source_missing_{item.source_name}",
                category="source", source=item.source_name,
                severity=sev,
                description=f"Source missing: {item.source_name}",
                recommendation="Run the corresponding module to regenerate this report."
            ))
        elif item.stale:
            rq.items.append(ReviewItem(
                item_id=f"source_stale_{item.source_name}",
                category="source", source=item.source_name,
                severity="warn",
                description=f"Source stale: {item.source_name} ({item.stale_hours}h old)",
                recommendation="Re-run the module to refresh data."
            ))

    # Items from circuit breaker
    for b in circuit_breaker.hard_blocks:
        rq.items.append(ReviewItem(
            item_id=f"hard_block_{len(rq.items)}",
            category="safety", source="circuit_breaker",
            severity="block", description=str(b)[:200],
            recommendation="Fix the blocked condition before continuing."
        ))
    for d in circuit_breaker.degradations:
        rq.items.append(ReviewItem(
            item_id=f"degraded_{len(rq.items)}",
            category="signal", source="circuit_breaker",
            severity="degraded", description=str(d)[:200],
            recommendation="Review and address before strategy upgrade."
        ))
    for w in circuit_breaker.warnings:
        rq.items.append(ReviewItem(
            item_id=f"warning_{len(rq.items)}",
            category="signal", source="circuit_breaker",
            severity="warn", description=str(w)[:200],
            recommendation="Monitor and review."
        ))

    # Signal fusion review candidates
    fusion = signal_fusion_data.get("fusion_summary", signal_fusion_data)
    for c in fusion.get("candidates", []):
        if c.get("requires_review") or c.get("status") in ("review_required", "watch_only"):
            rq.items.append(ReviewItem(
                item_id=f"review_candidate_{c.get('candidate_id','')}",
                category="signal", source="signal_fusion",
                severity="warn",
                description=f"Candidate requires review: {c.get('candidate_id','')} status={c.get('status','')} reasons={c.get('review_reasons',[])}",
                recommendation="Manual review of candidate signal quality."
            ))

    # Count
    rq.review_item_count = len(rq.items)
    for item in rq.items:
        if item.severity == "info":
            rq.info_count += 1
        elif item.severity == "warn":
            rq.warn_count += 1
        elif item.severity == "degraded":
            rq.degraded_count += 1
        elif item.severity == "block":
            rq.block_count += 1

    return rq


def build_quality_gate(source_health: SourceHealthSummary, circuit_breaker: CircuitBreakerResult,
                       review_queue: ReviewQueue) -> QualityGate:
    """Build quality gate assessment across categories."""
    qg = QualityGate()
    cats = {}

    # Source category
    src_ok = source_health.available_count >= source_health.source_count * 0.5
    cats["source"] = "pass" if src_ok and source_health.blocked_count == 0 else ("block" if source_health.blocked_count > 0 else "degraded")

    # Data category
    data_ok = source_health.valid_count >= source_health.available_count * 0.8
    cats["data"] = "pass" if data_ok else ("block" if source_health.blocked_count > 0 else "degraded")

    # Signal category
    signal_ok = circuit_breaker.overall_status in ("PASS", "WARN")
    cats["signal"] = "pass" if signal_ok else ("block" if circuit_breaker.hard_block_count > 0 else "degraded")

    # Safety category
    safety_ok = circuit_breaker.hard_block_count == 0
    cats["safety"] = "pass" if safety_ok else "block"

    # Strategy category
    strategy_ok = circuit_breaker.blocked_from_strategy_upgrade == False
    cats["strategy"] = "pass" if strategy_ok else "degraded"

    qg.categories = cats

    for v in cats.values():
        if v == "pass":
            qg.pass_count += 1
        elif v == "warn":
            qg.warn_count += 1
        elif v == "degraded":
            qg.degraded_count += 1
        elif v == "block":
            qg.block_count += 1

    if qg.block_count > 0:
        qg.status = "BLOCKED"
    elif qg.degraded_count > 0:
        qg.status = "DEGRADED"
    elif qg.warn_count > 0:
        qg.status = "WARN"
    else:
        qg.status = "PASS"

    return qg


def run_watchdog(source_paths: dict, config: dict, signal_fusion_data: dict = None,
                 market_expectation_data: dict = None, team_news_data: dict = None) -> WatchdogResult:
    """Run full watchdog pipeline."""
    sf_data = signal_fusion_data or {}
    me_data = market_expectation_data or {}
    tn_data = team_news_data or {}

    required = config.get("sources", {}).get("required", [])

    # Step 1: Source health
    source_health = run_source_health_check(source_paths, required, config)

    # Step 2: Circuit breaker
    circuit_breaker = run_circuit_breaker(source_health, sf_data, me_data, tn_data, config)

    # Step 3: Review queue
    review_queue = build_review_queue(source_health, circuit_breaker, sf_data, config)

    # Step 4: Quality gate
    quality_gate = build_quality_gate(source_health, circuit_breaker, review_queue)

    result = WatchdogResult(
        generated_at=datetime.now().isoformat(),
        source_health=_to_dict(source_health),
        circuit_breaker=_to_dict(circuit_breaker),
        review_queue=_to_dict(review_queue),
        quality_gate=_to_dict(quality_gate),
    )
    return result


def _to_dict(obj):
    if hasattr(obj, '__dataclass_fields__'):
        from dataclasses import asdict
        return {k: _to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_to_dict(i) for i in obj]
    return obj
