"""Human Review Workbench v1: source loader, normalizer, deduplicator, priority, decision, audit, renderer."""

import json, hashlib, copy

from dataclasses import dataclass, field, asdict

from datetime import datetime

from pathlib import Path

from typing import Optional



ROOT = Path(__file__).resolve().parent.parent.parent

FORBIDDEN = ["stake","stake_amount","stake_to_match","bet_instruction","bet_slip",

    "bookmaker_account","account_balance","real_money_balance","wallet_address",

    "private_key","api_secret","signed_order","submit_order","cancel_order"]



def _d(obj):

    if hasattr(obj,"__dataclass_fields__"): return {k:_d(v) for k,v in asdict(obj).items()}

    if isinstance(obj,list): return [_d(i) for i in obj]

    if isinstance(obj,dict): return {k:_d(v) for k,v in obj.items()}

    return obj



@dataclass

class ReviewItem:

    item_id: str=""

    source_type: str=""

    source_date: str=""

    match_id: str=""

    review_reason: str=""

    severity: str="medium"

    priority: int=50

    status: str="open"

    description: str=""

    details: dict=field(default_factory=dict)

    created_at: str=""

    updated_at: str=""

    decision: str=""

    decision_reason: str=""

    decision_timestamp: str=""

    warnings: list=field(default_factory=list)



@dataclass

class ReviewSourceResult:

    source_name: str=""

    items: list=field(default_factory=list)

    raw_count: int=0

    status: str="SKIPPED"

    error: str=""



class ReviewSourceLoader:

    def __init__(self, config_dir=None):

        cd = Path(config_dir) if config_dir else ROOT / "config"

        self.gen_dir = ROOT / "reports" / "generated"

        self.policy = self._load_json(cd / "review_item_priority_policy.json")



    def _load_json(self, p): return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}



    def load_all_sources(self, current_date: str, bankroll: float) -> list:

        sources = []

        for src_name in ["watchdog_review","signal_fusion_review","settlement_review","daily_ops_review","dry_run_review"]:

            r = self._load_source(src_name, current_date, bankroll)

            sources.append(r)

        return sources



    def _load_source(self, name: str, date: str, bankroll: float) -> ReviewSourceResult:

        result = ReviewSourceResult(source_name=name)

        try:

            if name == "watchdog_review": result = self._load_watchdog(date, bankroll)

            elif name == "signal_fusion_review": result = self._load_signal_fusion(date, bankroll)

            elif name == "settlement_review": result = self._load_settlement(date, bankroll)

            elif name == "daily_ops_review": result = self._load_daily_ops(date, bankroll)

            elif name == "dry_run_review": result = self._load_dry_run(date, bankroll)

        except Exception as e:

            result.status = "ERROR"; result.error = str(e)

        return result



    def _load_watchdog(self, date, br) -> ReviewSourceResult:

        r = ReviewSourceResult(source_name="watchdog_review", status="SUCCESS")

        fp = self.gen_dir / "daily_ops_watchdog.json"

        if fp.exists():

            data = json.loads(fp.read_text(encoding="utf-8"))

            r.raw_count = 1

            sev = "high" if data.get("overall_status","")=="BLOCKED" else ("medium" if data.get("overall_status","")=="WARN" else "low")

            r.items = [ReviewItem(

                item_id=f"wd-{date}-001", source_type="watchdog_review", source_date=date,

                review_reason="watchdog_review", severity=sev,

                description=f"Watchdog: {data.get('overall_status','UNKNOWN')}",

                details=data, created_at=datetime.now().isoformat())]

        return r



    def _load_signal_fusion(self, date, br) -> ReviewSourceResult:

        r = ReviewSourceResult(source_name="signal_fusion_review", status="SUCCESS")

        fp = self.gen_dir / "signal_fusion_preview.json"

        if fp.exists():

            data = json.loads(fp.read_text(encoding="utf-8"))

            candidates = data.get("upgraded_candidates",[]) or data.get("fused_signals",[])

            if not candidates: candidates = data.get("candidates",[])

            r.raw_count = len(candidates)

            for i, c in enumerate(candidates[:20]):

                ri = ReviewItem(

                    item_id=f"sf-{date}-{i:03d}", source_type="signal_fusion_review",

                    source_date=date, match_id=c.get("match_id",""),

                    review_reason="signal_fusion_review",

                    severity="high" if c.get("requires_review") else "medium",

                    description=f"Signal: {c.get('selection_label','?')} score={c.get('upgraded_campaign_score',0):.3f}",

                    details=c, created_at=datetime.now().isoformat())

                r.items.append(ri)

        return r



    def _load_settlement(self, date, br) -> ReviewSourceResult:

        r = ReviewSourceResult(source_name="settlement_review", status="SUCCESS")

        fp = self.gen_dir / "postmatch_settlement.json"

        if fp.exists():

            data = json.loads(fp.read_text(encoding="utf-8"))

            matches = data.get("matches", data.get("ledger",[]))

            r.raw_count = len(matches) if isinstance(matches,list) else 0

            if isinstance(matches, list):

                for i, m in enumerate(matches[:20]):

                    ri = ReviewItem(

                        item_id=f"st-{date}-{i:03d}", source_type="settlement_review",

                        source_date=date, match_id=m.get("match_id",""),

                        review_reason="settlement_review",

                        severity="high" if m.get("requires_review") else "low",

                        description=f"Settlement: {m.get('match_id','?')} status={m.get('auto_outcome_status','pending')}",

                        details=m, created_at=datetime.now().isoformat())

                    r.items.append(ri)

        return r



    def _load_daily_ops(self, date, br) -> ReviewSourceResult:

        r = ReviewSourceResult(source_name="daily_ops_review", status="SUCCESS")

        fp = self.gen_dir / "daily_ops_run.json"

        if fp.exists():

            data = json.loads(fp.read_text(encoding="utf-8"))

            r.raw_count = 1

            deg = data.get("overall_status","") == "DEGRADED"

            r.items = [ReviewItem(

                item_id=f"do-{date}-001", source_type="daily_ops_review", source_date=date,

                review_reason="daily_ops_review",

                severity="medium" if deg else "low",

                description=f"Daily Ops: {data.get('overall_status','UNKNOWN')}",

                details=data, created_at=datetime.now().isoformat())]

        return r



    def _load_dry_run(self, date, br) -> ReviewSourceResult:

        r = ReviewSourceResult(source_name="dry_run_review", status="SUCCESS")

        fp = self.gen_dir / "full_campaign_dry_run.json"

        if fp.exists():

            data = json.loads(fp.read_text(encoding="utf-8"))

            r.raw_count = data.get("warn_day_count",0) + data.get("degraded_day_count",0)

            r.items = [ReviewItem(

                item_id=f"dr-{date}-001", source_type="dry_run_review", source_date=date,

                review_reason="dry_run_review", severity="low",

                description=f"Dry-run: blocked={data.get('blocked_day_count',0)} warn={data.get('warn_day_count',0)}",

                details=data, created_at=datetime.now().isoformat())]

        return r



class ReviewItemNormalizer:

    def __init__(self, policy: dict=None): self.policy = policy or {}

    def normalize(self, items: list) -> list:

        normalized = []

        for item in items:

            n = copy.deepcopy(item)

            if not n.item_id: n.item_id = hashlib.md5(f"{n.source_type}:{n.source_date}:{n.review_reason}".encode()).hexdigest()[:12]

            if not n.created_at: n.created_at = datetime.now().isoformat()

            if not n.status: n.status = "open"

            n.description = n.description[:500]

            normalized.append(n)

        return normalized



class ReviewItemDeduplicator:

    def __init__(self, policy: dict=None):

        self.policy = policy or {}

        self.dedup_keys = self.policy.get("deduplicate_by", ["source_type","match_id","review_reason"])

    def deduplicate(self, items: list) -> tuple:

        seen = {}; kept = []; dups = 0

        for item in items:

            key = "|".join(str(getattr(item, k, "")) for k in self.dedup_keys)

            if key in seen: dups += 1; continue

            seen[key] = True; kept.append(item)

        return kept, dups



class PriorityClassifier:

    def __init__(self, policy: dict=None):

        self.policy = policy or {}

        self.severity_rules = self.policy.get("severity_rules", {})

        self.source_order = self.policy.get("source_priority_order", [])



    def classify(self, items: list) -> list:

        for item in items:

            sev = self.severity_rules.get(item.review_reason) or item.severity

            item.severity = sev

            sev_score = {"critical":100,"high":75,"medium":50,"low":25}.get(sev, 50)

            src_idx = self.source_order.index(item.source_type) if item.source_type in self.source_order else 99

            src_score = max(0, 20 - src_idx * 4)

            item.priority = sev_score + src_score

        items.sort(key=lambda x: x.priority, reverse=True)

        return items



@dataclass

class DecisionValidationResult:

    decision: dict=field(default_factory=dict)

    is_valid: bool=True

    errors: list=field(default_factory=list)



class DecisionValidator:

    def __init__(self, config_dir=None):

        cd = Path(config_dir) if config_dir else ROOT / "config"

        self.policy = self._load_json(cd / "manual_decision_policy.json")

    def _load_json(self, p): return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}



    def validate(self, decision: dict) -> DecisionValidationResult:

        result = DecisionValidationResult(decision=decision)

        dt = decision.get("decision_type","")

        allowed = self.policy.get("allowed_decision_types",[])

        if dt not in allowed:

            result.is_valid = False; result.errors.append(f"Invalid type: {dt}")

        forbidden = self.policy.get("forbidden_fields_in_decision",[])

        ds = json.dumps(decision).lower()

        for f in forbidden:

            if f.lower() in ds:

                result.is_valid = False; result.errors.append(f"Forbidden: {f}")

        if dt in self.policy.get("reason_required_for",[]):

            reason = decision.get("reason","")

            if len(reason) < self.policy.get("min_reason_length",10):

                result.is_valid = False; result.errors.append("Reason too short")

        if dt == "override_simulation_preview":

            allowed_src = self.policy.get("override_restricted_to_sources",[])

            if decision.get("source_type","") not in allowed_src:

                result.is_valid = False; result.errors.append("Override not allowed for this source")

        return result



    def apply_decision(self, item: ReviewItem, decision: dict) -> ReviewItem:

        item.decision = decision.get("decision_type","")

        item.decision_reason = decision.get("reason","")

        item.decision_timestamp = datetime.now().isoformat()

        dt = decision.get("decision_type","")

        if dt == "confirm": item.status = "resolved"

        elif dt == "reject": item.status = "rejected"

        elif dt == "defer": item.status = "deferred"

        elif dt == "request_more_data": item.status = "pending_data"

        elif dt == "override_simulation_preview": item.status = "resolved"; item.details["simulation_override_applied"] = True

        item.updated_at = datetime.now().isoformat()

        return item



class AuditLogger:

    def __init__(self, audit_path: str=None):

        self.path = Path(audit_path) if audit_path else ROOT / "reports" / "generated" / "review_audit_log.jsonl"

        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.entries = []

        self.append_only = True



    def log_decision(self, item: ReviewItem, decision: dict, validator_result: DecisionValidationResult):

        entry = {"timestamp":datetime.now().isoformat(),"item_id":item.item_id,"source_type":item.source_type,

                 "decision_type":decision.get("decision_type",""),"reason":decision.get("reason",""),

                 "valid":validator_result.is_valid,"reviewer":"human_operator",

                 "previous_status":item.status,"previous_severity":item.severity}

        self.entries.append(entry)

        with open(self.path, "a", encoding="utf-8") as f:

            f.write(json.dumps(entry, ensure_ascii=False) + "\n")



    def read_all(self) -> list:

        entries = []

        if self.path.exists():

            for line in self.path.read_text(encoding="utf-8").strip().split("\n"):

                if line.strip():

                    try: entries.append(json.loads(line))

                    except: pass

        return entries



@dataclass

class HumanReviewWorkbench:

    campaign_name: str="worldcup_2026_high_odds_campaign"

    current_date: str=""; current_bankroll: float=100.0

    review_item_count: int=0; open_count: int=0

    critical_count: int=0; high_count: int=0; medium_count: int=0; low_count: int=0

    settlement_review_count: int=0; signal_fusion_review_count: int=0

    watchdog_review_count: int=0; daily_ops_review_count: int=0; dry_run_review_count: int=0

    deduplicated_count: int=0

    items: list=field(default_factory=list)

    decisions: list=field(default_factory=list)

    audit_entries: list=field(default_factory=list)

    source_statuses: list=field(default_factory=list)

    warnings: list=field(default_factory=list)

    safety: dict=field(default_factory=dict)

    generated_at: str=""

    analysis_only: bool=True; simulation_only: bool=True; not_betting_advice: bool=True



def render_workbench_json(wb: HumanReviewWorkbench) -> dict:

    return _d(wb)



def render_workbench_markdown(wb: HumanReviewWorkbench) -> str:

    lines = [

        "# Human Review Workbench",

        f"**Date**: {wb.current_date} | **Bankroll**: {wb.current_bankroll}",

        f"**Items**: {wb.review_item_count} total ({wb.open_count} open)",

        "",

        "## 1. Review Summary",

        "| Severity | Count |",

        "|----------|-------|",

        f"| Critical | {wb.critical_count} |",

        f"| High | {wb.high_count} |",

        f"| Medium | {wb.medium_count} |",

        f"| Low | {wb.low_count} |",

        "",

        "## 2. By Source",

        "| Source | Count |",

        "|--------|-------|",

        f"| Settlement | {wb.settlement_review_count} |",

        f"| Signal Fusion | {wb.signal_fusion_review_count} |",

        f"| Watchdog | {wb.watchdog_review_count} |",

        f"| Daily Ops | {wb.daily_ops_review_count} |",

        f"| Dry Run | {wb.dry_run_review_count} |",

        f"| Deduplicated | {wb.deduplicated_count} |",

        "",

        "## 3. Review Items (Top)",

        "| P | Severity | Source | Reason | Status |",

        "|----|----------|--------|--------|--------|",

    ]

    for item in sorted(wb.items, key=lambda x: x.priority, reverse=True)[:20]:

        lines.append(f"| {item.priority} | {item.severity} | {item.source_type} | {item.review_reason[:40]} | {item.status} |")

    lines += [

        "",

        "## 4. Source Health",

        "| Source | Status | Raw Count |",

        "|--------|--------|-----------|",

    ]

    for ss in wb.source_statuses:

        lines.append(f"| {ss.get('source_name','?')} | {ss.get('status','?')} | {ss.get('raw_count',0)} |")

    lines += [

        "",

        "## 5. Safety Boundary",

        f"- Analysis Only: {wb.safety.get('analysis_only',True)}",

        f"- Simulation Only: {wb.safety.get('simulation_only',True)}",

        f"- Not Betting Advice: {wb.safety.get('not_betting_advice',True)}",

        "",

        "---",

        f"*Generated: {wb.generated_at}*",

        "> Analysis-only review workbench. Not betting advice.",

    ]

    return '\n'.join(lines)



def render_workbench_html(wb: HumanReviewWorkbench) -> str:

    rows = ""

    for item in sorted(wb.items, key=lambda x: x.priority, reverse=True)[:30]:

        sev = item.severity

        sc = {"critical":"#dc3545","high":"#fd7e14","medium":"#ffc107","low":"#28a745"}.get(sev,"#6c757d")

        rows += f"<tr><td>{item.priority}</td><td style='color:{sc};font-weight:bold'>{sev.upper()}</td><td>{item.source_type}</td><td>{item.review_reason[:50]}</td><td>{item.status}</td></tr>"

    return f"""<!DOCTYPE html>

<html lang="zh-CN">

<head><meta charset="utf-8"><title>Human Review Workbench</title>

<style>

body{{font-family:system-ui,sans-serif;margin:20px;background:#f5f5f5;color:#333}}

h1{{border-bottom:2px solid #333;padding-bottom:10px}}

table{{border-collapse:collapse;width:100%;margin:10px 0;background:#fff}}

th,td{{border:1px solid #ddd;padding:8px;font-size:14px}}

th{{background:#333;color:#fff}}

.card{{background:#fff;border-radius:8px;padding:16px;margin:12px 0;box-shadow:0 1px 3px rgba(0,0,0,0.1)}}

.badge{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:bold;color:#fff;margin:0 4px}}

.bg-crit{{background:#dc3545}}.bg-high{{background:#fd7e14}}.bg-med{{background:#ffc107;color:#333}}.bg-low{{background:#28a745}}

.footer{{margin-top:20px;padding:10px;background:#333;color:#fff;font-size:12px;text-align:center}}

</style></head>

<body>

<h1>Human Review Workbench</h1>

<div class="card">

<strong>{wb.current_date}</strong> | Bankroll: {wb.current_bankroll} | Items: {wb.review_item_count} ({wb.open_count} open)

<span class="badge bg-crit">Critical: {wb.critical_count}</span>

<span class="badge bg-high">High: {wb.high_count}</span>

<span class="badge bg-med">Medium: {wb.medium_count}</span>

<span class="badge bg-low">Low: {wb.low_count}</span>

</div>

<div class="card"><h3>By Source</h3>

<table><tr><th>Source</th><th>Count</th></tr>

<tr><td>Settlement</td><td>{wb.settlement_review_count}</td></tr>

<tr><td>Signal Fusion</td><td>{wb.signal_fusion_review_count}</td></tr>

<tr><td>Watchdog</td><td>{wb.watchdog_review_count}</td></tr>

<tr><td>Daily Ops</td><td>{wb.daily_ops_review_count}</td></tr>

<tr><td>Dry Run</td><td>{wb.dry_run_review_count}</td></tr>

</table></div>

<div class="card"><h3>Review Items</h3>

<table><tr><th>P</th><th>Severity</th><th>Source</th><th>Reason</th><th>Status</th></tr>

{rows}</table></div>

<div class="footer">Analysis Only | Simulation Only | Not Betting Advice<br>Generated: {wb.generated_at}</div>

</body></html>"""



def write_workbench_outputs(wb: HumanReviewWorkbench, out_dir: str=None):

    od = Path(out_dir) if out_dir else ROOT / "reports" / "generated"

    od.mkdir(parents=True, exist_ok=True)

    jp = od / "human_review_workbench.json"

    jp.write_text(json.dumps(render_workbench_json(wb), indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    mp = od / "human_review_workbench.md"

    mp.write_text(render_workbench_markdown(wb), encoding="utf-8")

    hp = od / "human_review_workbench.html"

    hp.write_text(render_workbench_html(wb), encoding="utf-8")

    return {"json": str(jp), "markdown": str(mp), "html": str(hp)}



class HumanReviewWorkbenchRunner:

    def __init__(self, config_dir: str=None):

        cd = Path(config_dir) if config_dir else ROOT / "config"

        self.config = self._load(cd / "human_review_workbench_config.json")

        self.pp = self._load(cd / "review_item_priority_policy.json")

        self.dp = self._load(cd / "manual_decision_policy.json")

        self.loader = ReviewSourceLoader(str(cd))

        self.normalizer = ReviewItemNormalizer(self.pp)

        self.deduplicator = ReviewItemDeduplicator(self.pp)

        self.classifier = PriorityClassifier(self.pp)

        self.validator = DecisionValidator(str(cd))

        self.audit = AuditLogger()



    def _load(self, p): return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}



    def run(self, current_date: str, current_bankroll: float, decisions: list=None) -> HumanReviewWorkbench:

        wb = HumanReviewWorkbench(

            current_date=current_date, current_bankroll=current_bankroll,

            safety={"analysis_only":True,"simulation_only":True,"not_betting_advice":True,

                     "real_bet_execution":False,"auto_betting":False,

                     "external_betting_api_allowed":False,"network_fetch_default_enabled":False},

            generated_at=datetime.now().isoformat())

        sources = self.loader.load_all_sources(current_date, current_bankroll)

        wb.source_statuses = [_d(s) for s in sources]

        all_items = []

        for s in sources: all_items.extend(s.items)

        all_items = self.normalizer.normalize(all_items)

        all_items, dedup = self.deduplicator.deduplicate(all_items)

        wb.deduplicated_count = dedup

        all_items = self.classifier.classify(all_items)

        if decisions:

            for dec in decisions:

                vresult = self.validator.validate(dec)

                target = next((it for it in all_items if it.item_id == dec.get("item_id","")), None)

                if target and vresult.is_valid:

                    self.validator.apply_decision(target, dec)

                    self.audit.log_decision(target, dec, vresult)

                wb.decisions.append({"decision": dec, "valid": vresult.is_valid, "errors": vresult.errors})

        wb.items = all_items

        wb.review_item_count = len(all_items)

        wb.open_count = sum(1 for i in all_items if i.status == "open")

        wb.critical_count = sum(1 for i in all_items if i.severity == "critical")

        wb.high_count = sum(1 for i in all_items if i.severity == "high")

        wb.medium_count = sum(1 for i in all_items if i.severity == "medium")

        wb.low_count = sum(1 for i in all_items if i.severity == "low")

        wb.settlement_review_count = sum(1 for i in all_items if i.source_type == "settlement_review")

        wb.signal_fusion_review_count = sum(1 for i in all_items if i.source_type == "signal_fusion_review")

        wb.watchdog_review_count = sum(1 for i in all_items if i.source_type == "watchdog_review")

        wb.daily_ops_review_count = sum(1 for i in all_items if i.source_type == "daily_ops_review")

        wb.dry_run_review_count = sum(1 for i in all_items if i.source_type == "dry_run_review")

        wb.audit_entries = self.audit.read_all()

        return wb



def validate_workbench_no_forbidden(wb: HumanReviewWorkbench) -> list:

    d = _d(wb)

    s = json.dumps({"items": d.get("items",[]), "decisions": d.get("decisions",[])}).lower()

    found = []

    for f in FORBIDDEN:

        if f.lower() in s: found.append(f)

    return found

