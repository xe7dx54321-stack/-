"""Full Campaign Dry-Run v1: timeline, day runner, bankroll, settlement aggregator, runner, renderer."""
import json, sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent
FORBIDDEN = ["stake","stake_amount","stake_to_match","bet_instruction","bet_slip","bookmaker_account","account_balance","real_money_balance","wallet_address","private_key","api_secret","signed_order","submit_order","cancel_order","real_bet_execution"]

def _d(obj):
    if hasattr(obj,"__dataclass_fields__"): return {k:_d(v) for k,v in asdict(obj).items()}
    if isinstance(obj,list): return [_d(i) for i in obj]
    if isinstance(obj,dict): return {k:_d(v) for k,v in obj.items()}
    return obj

@dataclass
class DryRunDay:
    date: str=""; day_index: int=0; day_type: str="matchday"
    match_count: int=0; match_ids: list=field(default_factory=list)
    stage: str=""; expected_runner_mode: str="dry_run"
    warnings: list=field(default_factory=list)

@dataclass
class DryRunTimeline:
    campaign_start_date: str=""; campaign_end_date: str=""
    day_count: int=0; matchday_count: int=0; rest_day_count: int=0
    transition_day_count: int=0; final_day_count: int=0
    days: list=field(default_factory=list)

def build_full_campaign_timeline(start_date: str, end_date: str, config: dict) -> DryRunTimeline:
    tl = DryRunTimeline(campaign_start_date=start_date, campaign_end_date=end_date)
    sd = ROOT / "data" / "seed"
    seed_path = sd / "full_campaign_result_timeline_seed.json"
    if seed_path.exists():
        seed = json.loads(seed_path.read_text(encoding="utf-8"))
        matchdays = seed.get("matchdays", [])
    else:
        start = datetime.strptime(start_date,"%Y-%m-%d")
        end = datetime.strptime(end_date,"%Y-%m-%d")
        matchdays = []
        current = start
        while current <= end:
            ds = current.strftime("%Y-%m-%d")
            matchdays.append({"date": ds, "day_type": "matchday", "stage": "group_stage", "match_count": 4})
            current += timedelta(days=1)
    matchdays = [md for md in matchdays if start_date <= md["date"] <= end_date]
    for i, md in enumerate(matchdays):
        dt = md.get("day_type","matchday")
        mids = md.get("match_ids",[])
        day = DryRunDay(date=md["date"], day_index=i, day_type=dt,
                        match_count=md.get("match_count", len(mids)),
                        match_ids=mids, stage=md.get("stage",""),
                        expected_runner_mode="dry_run")
        tl.days.append(day)
        if dt == "matchday": tl.matchday_count += 1
        elif dt == "rest_day": tl.rest_day_count += 1
        elif dt == "transition_day": tl.transition_day_count += 1
        elif dt == "final_day": tl.final_day_count += 1
    tl.day_count = len(tl.days)
    return tl

def classify_dry_run_day(day: DryRunDay, config: dict) -> str:
    if day.day_type == "final_day": return config.get("final_day_policy","run_full_daily_ops_and_closeout")
    if day.day_type == "rest_day": return config.get("rest_day_policy","run_light_watchdog_only")
    if day.day_type == "transition_day": return config.get("transition_day_policy","run_light_daily_ops")
    return config.get("matchday_policy","run_full_daily_ops")

@dataclass
class DryRunDayResult:
    date: str=""; day_type: str=""; starting_bankroll: float=100.0
    ending_bankroll_preview: float=100.0
    daily_ops_status: str="SKIPPED"; watchdog_status: str="UNKNOWN"
    package_type: str="none"; real_data_status: str="SKIPPED"
    settlement_status: str="SKIPPED"; review_item_count: int=0
    day_status: str="SKIPPED"; artifacts: list=field(default_factory=list)
    warnings: list=field(default_factory=list)

def run_dry_run_day(day: DryRunDay, current_bankroll: float, config: dict, day_policy: dict) -> DryRunDayResult:
    result = DryRunDayResult(date=day.date, day_type=day.day_type, starting_bankroll=current_bankroll)
    policy = classify_dry_run_day(day, config)
    if day.day_type == "rest_day":
        result.daily_ops_status = "SKIPPED"
        result.watchdog_status = "PASS"
        result.day_status = "SUCCESS"
        result.ending_bankroll_preview = current_bankroll
        return result
    result.daily_ops_status = "SUCCESS"
    result.watchdog_status = _simulate_watchdog(day)
    result.package_type = _determine_package_type(day, result)
    result.real_data_status = "SUCCESS" if day.day_type != "rest_day" else "SKIPPED"
    result.settlement_status = "SUCCESS"
    result.day_status = _determine_day_status(result)
    result.ending_bankroll_preview = _simulate_bankroll_change(current_bankroll, day, result)
    result.review_item_count = _estimate_review_items(day, result)
    return result

def _simulate_watchdog(day: DryRunDay) -> str:
    m = day.match_count
    if m > 6: return "WARN"
    if m > 3: return "WARN"
    return "PASS"

def _determine_package_type(day: DryRunDay, result: DryRunDayResult) -> str:
    if result.watchdog_status == "BLOCKED": return "none"
    if result.watchdog_status == "WARN": return "review_required_package"
    if day.match_count >= 4: return "full_daily_package"
    return "light_daily_package"

def _determine_day_status(result: DryRunDayResult) -> str:
    if result.watchdog_status == "BLOCKED": return "BLOCKED"
    if result.watchdog_status == "WARN": return "WARN"
    return "SUCCESS"

def _simulate_bankroll_change(current: float, day: DryRunDay, result: DryRunDayResult) -> float:
    if day.day_type == "rest_day": return current
    if result.watchdog_status == "BLOCKED": return current
    drift = 0.0
    if day.stage == "group_stage": drift = day.match_count * 0.3
    elif day.stage in ("round_of_32","round_of_16"): drift = day.match_count * 0.5
    elif day.stage in ("quarter_final","semi_final","third_place","final"): drift = day.match_count * 0.8
    return max(0, current + drift)

def _estimate_review_items(day: DryRunDay, result: DryRunDayResult) -> int:
    if day.day_type == "rest_day": return 0
    if result.watchdog_status == "BLOCKED": return 0
    return min(day.match_count * 2, 10)

@dataclass
class DryRunBankrollUpdate:
    starting_bankroll: float=100.0; settlement_applied_count: int=0
    settlement_skipped_review_count: int=0; simulated_profit_loss: float=0.0
    ending_bankroll_preview: float=100.0; starting_state: str="S2"
    ending_state: str="S2"; warnings: list=field(default_factory=list)

def calculate_bankroll_update(starting: float, settlement: dict, policy: dict) -> DryRunBankrollUpdate:
    u = DryRunBankrollUpdate(starting_bankroll=starting)
    entries = settlement.get("matches",[])
    for e in entries:
        if e.get("requires_review") or e.get("confidence",0) < policy.get("settlement_confidence_required_for_update",0.80):
            u.settlement_skipped_review_count += 1; continue
        u.settlement_applied_count += 1
        st = e.get("auto_outcome_status","")
        if st == "hit": u.simulated_profit_loss += 0.5
        elif st == "miss": u.simulated_profit_loss -= 0.5
    u.ending_bankroll_preview = max(0, starting + u.simulated_profit_loss)
    u.starting_state = classify_bankroll_state(starting, policy)
    u.ending_state = classify_bankroll_state(u.ending_bankroll_preview, policy)
    return u

def classify_bankroll_state(bankroll: float, policy: dict=None) -> str:
    if bankroll >= 1000000: return "TARGET_REACHED"
    if bankroll >= 100000: return "S7"
    if bankroll >= 20000: return "S6"
    if bankroll >= 5000: return "S5"
    if bankroll >= 1000: return "S4"
    if bankroll >= 300: return "S3"
    if bankroll >= 100: return "S2"
    if bankroll >= 50: return "S1"
    return "S0"

@dataclass
class DryRunStateHistory:
    initial_bankroll: float=100.0; final_bankroll_preview: float=100.0
    initial_state: str="S2"; final_state: str="S2"
    state_changes: int=0; days: list=field(default_factory=list)
    target_reached: bool=False

def build_bankroll_state_history(day_results: list, initial_bankroll: float, policy: dict) -> DryRunStateHistory:
    h = DryRunStateHistory(initial_bankroll=initial_bankroll)
    current = initial_bankroll
    prev_state = classify_bankroll_state(current, policy)
    for dr in day_results:
        current = dr.ending_bankroll_preview
        state = classify_bankroll_state(current, policy)
        if state != prev_state:
            h.state_changes += 1; prev_state = state
        h.days.append({"date": dr.date, "bankroll": round(current,2), "state": state, "day_status": dr.day_status})
    h.final_bankroll_preview = round(current,2)
    h.initial_state = classify_bankroll_state(initial_bankroll, policy)
    h.final_state = classify_bankroll_state(current, policy)
    h.target_reached = current >= 1000000
    return h

@dataclass
class DryRunSettlementSummary:
    total_ledger_entries: int=0; auto_settled_count: int=0
    manual_review_count: int=0; pending_count: int=0
    hit_count: int=0; miss_count: int=0; push_count: int=0
    void_count: int=0; unknown_count: int=0
    bucket_summary: dict=field(default_factory=dict)
    market_type_summary: dict=field(default_factory=dict)

def summarize_dry_run_settlement(day_results: list) -> DryRunSettlementSummary:
    s = DryRunSettlementSummary()
    for dr in day_results:
        s.total_ledger_entries += 1
        if dr.settlement_status == "SUCCESS": s.auto_settled_count += 1
        if dr.review_item_count > 0: s.manual_review_count += dr.review_item_count
        if dr.day_type == "matchday": s.hit_count += 1
    s.bucket_summary = {"core":0,"edge":0,"attack":0,"futures":0,"parlay":0}
    s.market_type_summary = {"1x2":0,"over_under":0,"correct_score":0,"futures":0}
    return s

@dataclass
class DryRunReviewSummary:
    total_review_items: int=0; by_reason: dict=field(default_factory=dict)
    by_day_type: dict=field(default_factory=dict); top_reasons: list=field(default_factory=list)
    watchdog_review_count: int=0; signal_fusion_review_count: int=0
    settlement_review_count: int=0

def aggregate_dry_run_reviews(day_results: list) -> DryRunReviewSummary:
    r = DryRunReviewSummary()
    for dr in day_results:
        r.total_review_items += dr.review_item_count
        dt = dr.day_type
        r.by_day_type[dt] = r.by_day_type.get(dt,0) + dr.review_item_count
        if dr.watchdog_status == "WARN": r.watchdog_review_count += 1
        if dr.package_type == "review_required_package": r.signal_fusion_review_count += dr.review_item_count
        if dr.settlement_status == "SUCCESS": r.settlement_review_count += 1
    r.by_reason = {
        "watchdog_warn": r.watchdog_review_count,
        "signal_fusion_review": r.signal_fusion_review_count,
        "settlement_review": r.settlement_review_count
    }
    r.top_reasons = sorted(r.by_reason.keys(), key=lambda k: r.by_reason[k], reverse=True)
    return r

@dataclass
class DryRunArtifactManifest:
    total_artifacts: int=0; available_artifact_count: int=0
    missing_artifact_count: int=0; forbidden_field_count: int=0
    artifacts: list=field(default_factory=list)
    missing_artifacts_list: list=field(default_factory=list)
    forbidden_field_details: list=field(default_factory=list)

def build_artifact_manifest(day_results: list, config: dict) -> DryRunArtifactManifest:
    m = DryRunArtifactManifest()
    generated_dir = ROOT / "reports" / "generated"
    expected_artifacts = [
        "campaign_dashboard.json", "daily_brief.md", "daily_ops_run.json",
        "daily_ops_watchdog.json", "postmatch_settlement.json",
        "integrated_daily_strategy.json", "signal_fusion_preview.json",
        "real_data_preview.json", "market_expectation.json",
        "model_calibration_review.json"
    ]
    for fname in expected_artifacts:
        fp = generated_dir / fname
        status = "available" if fp.exists() else "missing"
        art = {"name": fname, "status": status, "path": str(fp)}
        m.artifacts.append(art)
        if status == "available":
            m.available_artifact_count += 1
            fc = _scan_forbidden_fields(fp, config.get("forbidden_artifact_fields", FORBIDDEN))
            if fc:
                m.forbidden_field_count += len(fc)
                m.forbidden_field_details.append({"file": fname, "fields": fc})
        else:
            m.missing_artifact_count += 1
            m.missing_artifacts_list.append(fname)
    m.total_artifacts = len(expected_artifacts)
    return m

def _scan_forbidden_fields(path: Path, forbidden: list) -> list:
    found = []
    try:
        data = path.read_text(encoding="utf-8").lower()
        for f in forbidden:
            if f.lower() in data: found.append(f)
    except Exception:
        pass
    return found

@dataclass
class FullCampaignDryRunResult:
    campaign_name: str="worldcup_2026_high_odds_campaign"
    start_date: str=""; end_date: str=""; initial_bankroll: float=100.0
    final_bankroll_preview: float=100.0; target_reached: bool=False
    day_count: int=0; matchday_count: int=0
    completed_day_count: int=0; blocked_day_count: int=0
    warn_day_count: int=0; degraded_day_count: int=0
    skipped_day_count: int=0
    timeline: Optional[DryRunTimeline]=None
    day_results: list=field(default_factory=list)
    state_history: Optional[DryRunStateHistory]=None
    settlement_summary: Optional[DryRunSettlementSummary]=None
    review_summary: Optional[DryRunReviewSummary]=None
    artifact_manifest: Optional[DryRunArtifactManifest]=None
    bottleneck_analysis: dict=field(default_factory=dict)
    warnings: list=field(default_factory=list)
    errors: list=field(default_factory=list)
    safety: dict=field(default_factory=dict)
    generated_at: str=""
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True

class FullCampaignDryRunRunner:
    def __init__(self, config_dir: str=None):
        cd = Path(config_dir) if config_dir else ROOT / "config"
        self.config_dir = cd
        self.main_config = self._load_json(cd / "full_campaign_dry_run_config.json")
        self.timeline_config = self._load_json(cd / "dry_run_timeline_config.json")
        self.day_policy = self._load_json(cd / "dry_run_day_policy.json")
        self.bankroll_policy = self._load_json(cd / "dry_run_bankroll_policy.json")
        self.report_config = self._load_json(cd / "dry_run_report_config.json")
        self.artifact_policy = self._load_json(cd / "dry_run_artifact_policy.json")

    def _load_json(self, path: Path) -> dict:
        if path.exists(): return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def run(self, start_date: str, end_date: str, initial_bankroll: float) -> FullCampaignDryRunResult:
        result = FullCampaignDryRunResult(
            start_date=start_date, end_date=end_date, initial_bankroll=initial_bankroll,
            safety={"analysis_only":True,"simulation_only":True,"not_betting_advice":True,
                     "real_bet_execution":False,"auto_betting":False,
                     "external_betting_api_allowed":False,"network_fetch_default_enabled":False},
            generated_at=datetime.now().isoformat()
        )
        tl = build_full_campaign_timeline(start_date, end_date, self.timeline_config)
        result.timeline = tl; result.day_count = tl.day_count; result.matchday_count = tl.matchday_count
        current_bankroll = initial_bankroll
        for day in tl.days:
            dr = run_dry_run_day(day, current_bankroll, self.timeline_config, self.day_policy)
            result.day_results.append(dr); current_bankroll = dr.ending_bankroll_preview
            if dr.day_status == "SUCCESS": result.completed_day_count += 1
            elif dr.day_status == "BLOCKED": result.blocked_day_count += 1
            elif dr.day_status == "WARN": result.warn_day_count += 1
            elif dr.day_status == "DEGRADED": result.degraded_day_count += 1
            elif dr.day_status == "SKIPPED": result.skipped_day_count += 1
        result.final_bankroll_preview = current_bankroll
        result.target_reached = current_bankroll >= self.bankroll_policy.get("target_bankroll", 1000000)
        result.state_history = build_bankroll_state_history(result.day_results, initial_bankroll, self.bankroll_policy)
        result.settlement_summary = summarize_dry_run_settlement(result.day_results)
        result.review_summary = aggregate_dry_run_reviews(result.day_results)
        result.artifact_manifest = build_artifact_manifest(result.day_results, self.artifact_policy)
        result.bottleneck_analysis = self._analyze_bottlenecks(result)
        return result

    def _analyze_bottlenecks(self, result: FullCampaignDryRunResult) -> dict:
        ba = {"total_blocked_days":result.blocked_day_count,"total_warn_days":result.warn_day_count,
              "total_degraded_days":result.degraded_day_count,"most_common_warning_reasons":[],
              "degraded_reasons":[],"pipeline_bottleneck_days":[]}
        warn_reasons = {}
        for dr in result.day_results:
            for w in dr.warnings: warn_reasons[w] = warn_reasons.get(w, 0) + 1
            if dr.watchdog_status == "WARN": ba["pipeline_bottleneck_days"].append(dr.date)
        ba["most_common_warning_reasons"] = sorted(warn_reasons.keys(), key=lambda k: warn_reasons[k], reverse=True)[:5]
        ba["pipeline_bottleneck_days"] = ba["pipeline_bottleneck_days"][:10]
        return ba

def render_dry_run_json(result: FullCampaignDryRunResult) -> dict:
    return _d(result)

def render_dry_run_markdown(result: FullCampaignDryRunResult) -> str:
    sh = result.state_history; ss = result.settlement_summary
    rs = result.review_summary; am = result.artifact_manifest; ba = result.bottleneck_analysis
    lines = [
        f"# Full Campaign Dry-Run Report",
        f"",
        f"## 1. Campaign Context",
        f"- **Campaign**: {result.campaign_name}",
        f"- **Period**: {result.start_date} -> {result.end_date}",
        f"- **Initial Bankroll**: {result.initial_bankroll}",
        f"- **Final Bankroll Preview**: {result.final_bankroll_preview}",
        f"- **Target Reached**: {result.target_reached}",
        f"- **Days**: {result.day_count} total ({result.matchday_count} matchdays)",
        f"",
        f"## 2. Day Status Summary",
        f"| Status | Count |",
        f"|--------|-------|",
        f"| Completed | {result.completed_day_count} |",
        f"| Blocked | {result.blocked_day_count} |",
        f"| Warn | {result.warn_day_count} |",
        f"| Degraded | {result.degraded_day_count} |",
        f"| Skipped | {result.skipped_day_count} |",
        f"",
    ]
    if sh:
        lines += [
            f"## 3. Bankroll State History",
            f"- **Initial State**: {sh.initial_state}",
            f"- **Final State**: {sh.final_state}",
            f"- **State Changes**: {sh.state_changes}",
            f"- **Min Bankroll**: {min((d['bankroll'] for d in sh.days), default=result.initial_bankroll)}",
            f"- **Max Bankroll**: {max((d['bankroll'] for d in sh.days), default=result.initial_bankroll)}",
            f"- **Target Reached**: {sh.target_reached}",
            f"",
        ]
    if ss:
        lines += [
            f"## 4. Settlement Summary",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Ledger Entries | {ss.total_ledger_entries} |",
            f"| Auto Settled | {ss.auto_settled_count} |",
            f"| Manual Review | {ss.manual_review_count} |",
            f"| Pending | {ss.pending_count} |",
            f"| Hit | {ss.hit_count} |",
            f"| Miss | {ss.miss_count} |",
            f"| Push | {ss.push_count} |",
            f"| Void | {ss.void_count} |",
            f"",
        ]
    if rs:
        lines += [
            f"## 5. Review Queue Summary",
            f"- **Total Review Items**: {rs.total_review_items}",
            f"- **Watchdog Reviews**: {rs.watchdog_review_count}",
            f"- **Signal Fusion Reviews**: {rs.signal_fusion_review_count}",
            f"- **Settlement Reviews**: {rs.settlement_review_count}",
            f"- **Top Reasons**: {', '.join(rs.top_reasons[:5])}",
            f"",
        ]
    if am:
        lines += [
            f"## 6. Artifact Manifest",
            f"- **Total Artifacts**: {am.total_artifacts}",
            f"- **Available**: {am.available_artifact_count}",
            f"- **Missing**: {am.missing_artifact_count}",
            f"- **Forbidden Fields Found**: {am.forbidden_field_count}",
            f"",
        ]
        if am.missing_artifacts_list:
            lines.append(f"**Missing**: {', '.join(am.missing_artifacts_list)}")
            lines.append("")
    if ba:
        lines += [
            f"## 7. Bottleneck Analysis",
            f"- **Blocked Days**: {ba.get('total_blocked_days',0)}",
            f"- **Warn Days**: {ba.get('total_warn_days',0)}",
            f"- **Degraded Days**: {ba.get('total_degraded_days',0)}",
            f"- **Top Warning Reasons**: {', '.join(ba.get('most_common_warning_reasons',[]))}",
            f"",
        ]
    lines += [
        f"## 8. Safety Boundary",
        f"- **Analysis Only**: {result.safety.get('analysis_only',True)}",
        f"- **Simulation Only**: {result.safety.get('simulation_only',True)}",
        f"- **Not Betting Advice**: {result.safety.get('not_betting_advice',True)}",
        f"- **Real Bet Execution**: {result.safety.get('real_bet_execution',False)}",
        f"- **Auto Betting**: {result.safety.get('auto_betting',False)}",
        f"- **Network Fetch**: {result.safety.get('network_fetch_default_enabled',False)}",
        f"",
        f"---",
        f"*Generated: {result.generated_at}*",
        f"",
        f"> This is a simulation dry-run only. Not betting advice. No real money used. No real bets placed.",
    ]
    return '\n'.join(lines)

def write_dry_run_outputs(result: FullCampaignDryRunResult, out_dir: str=None):
    od = Path(out_dir) if out_dir else ROOT / "reports" / "generated"
    od.mkdir(parents=True, exist_ok=True)
    jp = od / "full_campaign_dry_run.json"
    jp.write_text(json.dumps(render_dry_run_json(result), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    mp = od / "full_campaign_dry_run.md"
    mp.write_text(render_dry_run_markdown(result), encoding="utf-8")
    shp = od / "full_campaign_state_history.json"
    if result.state_history:
        shp.write_text(json.dumps(_d(result.state_history), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return {"json": str(jp), "markdown": str(mp), "state_history": str(shp)}

def validate_no_forbidden(result: FullCampaignDryRunResult) -> list:
    """Check core data sections only, skip legit safety metadata."""
    d = _d(result)
    check_sections = {}
    for key in ["day_results","state_history","settlement_summary","review_summary","bottleneck_analysis"]:
        if key in d: check_sections[key] = d[key]
    s = json.dumps(check_sections).lower()
    found = []
    for f in FORBIDDEN:
        if f.lower() in s: found.append(f)
    return found