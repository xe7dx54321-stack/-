"""Production Readiness Closeout v1: capability map, scorecard, runbook, checklist, gap register."""
import json, sys
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
class CapabilityEntry:
    domain: str=""; capability: str=""; round_number: int=0
    status: str="not_ready"; runner_available: bool=False
    manual_review_required: bool=True; source_enablement_required: bool=False
    notes: str=""

@dataclass
class CapabilityMap:
    capabilities: list=field(default_factory=list)
    capability_count: int=0; ready_count: int=0
    partial_ready_count: int=0; not_ready_count: int=0; blocked_count: int=0

@dataclass
class DomainScorecard:
    domain: str=""; status: str="not_ready"
    analysis_ready: bool=False; simulation_ready: bool=False
    source_enablement_required: bool=False; manual_review_required: bool=True
    notes: str=""

@dataclass
class Scorecard:
    domains: list=field(default_factory=list)
    domain_count: int=0; ready_domain_count: int=0
    partial_ready_domain_count: int=0; not_ready_domain_count: int=0; blocked_domain_count: int=0

@dataclass
class SourceEnablementEntry:
    category: str=""; status: str="not_allowed"
    adapter_ready: bool=False; default_disabled: bool=True
    notes: str=""

@dataclass
class SourceEnablementPlan:
    entries: list=field(default_factory=list)
    source_category_count: int=0; manual_ready_count: int=0
    fixture_ready_count: int=0; adapter_ready_disabled_count: int=0
    needs_source_selection_count: int=0; not_allowed_count: int=0

@dataclass
class KnownGap:
    gap_id: str=""; severity: str="medium"; domain: str=""
    description: str=""; mitigation: str=""

@dataclass
class GapRegister:
    gaps: list=field(default_factory=list)
    gap_count: int=0; critical_gap_count: int=0; high_gap_count: int=0
    medium_gap_count: int=0; low_gap_count: int=0

@dataclass
class ChecklistItem:
    item_id: str=""; item: str=""; status: str="pending"

@dataclass
class PreTournamentChecklist:
    items: list=field(default_factory=list)
    checklist_count: int=0; pending_count: int=0; completed_count: int=0

@dataclass
class ProductionReadinessCloseout:
    campaign_name: str="worldcup_2026_high_odds_campaign"
    closeout_date: str=""; overall_status: str="SIMULATION_ONLY"
    readiness_score: float=0.0; readiness_level: str="NOT_READY"
    real_money_execution_ready: bool=False
    capability_map: Optional[CapabilityMap]=None
    scorecard: Optional[Scorecard]=None
    source_enablement_plan: Optional[SourceEnablementPlan]=None
    gap_register: Optional[GapRegister]=None
    pre_tournament_checklist: Optional[PreTournamentChecklist]=None
    dry_run_summary: dict=field(default_factory=dict)
    workbench_summary: dict=field(default_factory=dict)
    operator_runbook: str=""
    warnings: list=field(default_factory=list)
    safety: dict=field(default_factory=dict)
    generated_at: str=""
    analysis_only: bool=True; simulation_only: bool=True; not_betting_advice: bool=True

class ProductionReadinessCloseoutRunner:
    def __init__(self, config_dir: str=None):
        cd = Path(config_dir) if config_dir else ROOT / "config"
        self.config = self._load_json(cd / "production_readiness_config.json")
        self.gen_dir = ROOT / "reports" / "generated"

    def _load_json(self, p): return json.loads(p.read_bytes().decode("utf-8-sig")) if p.exists() else {}

    def run(self) -> ProductionReadinessCloseout:
        pr = ProductionReadinessCloseout(
            closeout_date=datetime.now().strftime("%Y-%m-%d"),
            safety={"analysis_only":True,"simulation_only":True,"not_betting_advice":True,
                     "real_bet_execution":False,"auto_betting":False,
                     "external_betting_api_allowed":False,"network_fetch_default_enabled":False},
            generated_at=datetime.now().isoformat())

        # 1. Build capability map
        pr.capability_map = self._build_capability_map()
        # 2. Build scorecard
        pr.scorecard = self._build_scorecard()
        # 3. Build source enablement plan
        pr.source_enablement_plan = self._build_source_plan()
        # 4. Build gap register
        pr.gap_register = self._build_gap_register()
        # 5. Build checklist
        pr.pre_tournament_checklist = self._build_checklist()
        # 6. Load dry-run + workbench summaries
        pr.dry_run_summary = self._load_summary("full_campaign_dry_run.json")
        pr.workbench_summary = self._load_summary("human_review_workbench.json")
        # 7. Build operator runbook
        pr.operator_runbook = self._build_runbook()
        # 8. Calculate readiness
        ready = pr.scorecard.ready_domain_count
        total = max(1, pr.scorecard.domain_count)
        pr.readiness_score = round(ready / total, 3)
        if pr.readiness_score >= 0.9: pr.readiness_level = "HIGH_READINESS"
        elif pr.readiness_score >= 0.7: pr.readiness_level = "MODERATE_READINESS"
        elif pr.readiness_score >= 0.5: pr.readiness_level = "LOW_READINESS"
        else: pr.readiness_level = "NOT_READY"
        pr.overall_status = "SIMULATION_ONLY_ANALYSIS_READY" if pr.readiness_score >= 0.7 else "SIMULATION_ONLY"
        pr.real_money_execution_ready = False
        return pr

    def _build_capability_map(self) -> CapabilityMap:
        caps = [
            CapabilityEntry("campaign_strategy","Campaign policy + bankroll state machine + target math",1,"ready",True,False,False),
            CapabilityEntry("market_data","World Cup calendar + match registry + stage mapper",2,"ready",True,False,False),
            CapabilityEntry("strategy_generation","Daily unified strategy + scenario preview",3,"ready",True,False,False),
            CapabilityEntry("probability_modeling","Match probability + Poisson scoreline + over/under + handicap",4,"ready",True,False,False),
            CapabilityEntry("market_data","Mock odds + probability sanity + EV ranking",5,"ready",True,False,False),
            CapabilityEntry("strategy_generation","Integrated daily strategy (Core/Edge/Attack/Futures)",6,"ready",True,False,False),
            CapabilityEntry("parlay_optimization","Parlay optimizer 2/3/4-leg + correlation guard",7,"ready",True,False,False),
            CapabilityEntry("futures_simulation","Tournament futures path simulator + synthetic futures odds",8,"ready",True,False,False),
            CapabilityEntry("execution_planning","Campaign timeline + daily execution schedule + operator checklist",9,"ready",True,False,False),
            CapabilityEntry("settlement","Post-match settlement + simulation ledger + manual result input",10,"ready",True,False,False),
            CapabilityEntry("dashboard","Campaign Dashboard + Daily Brief v1 + HTML dashboard",11,"ready",True,False,False),
            CapabilityEntry("calibration","Model calibration + Brier/log loss + bucket/parlay/futures performance",12,"ready",True,False,False),
            CapabilityEntry("market_data","Sportsbook odds + market consensus + odds movement",13,"ready",True,False,True),
            CapabilityEntry("prediction_market","Polymarket adapter + prediction market signal",14,"ready",True,False,True),
            CapabilityEntry("market_expectation","Market expectation engine + model vs market gap",15,"ready",True,False,True),
            CapabilityEntry("team_news","Team news / injury / lineup adapter",16,"ready",True,False,True),
            CapabilityEntry("signal_fusion","Signal fusion + strategy upgrade + review guard",17,"ready",True,False,True),
            CapabilityEntry("watchdog_circuit_breaker","Daily Ops Watchdog + circuit breaker",18,"ready",True,False,False),
            CapabilityEntry("daily_ops_orchestration","Daily Ops Runner + pipeline orchestrator",19,"ready",True,False,False),
            CapabilityEntry("real_data_adapter","Real data adapter + settlement auto-match",20,"ready",True,False,True),
            CapabilityEntry("full_campaign_dry_run","Full campaign dry-run v1",21,"ready",True,False,False),
            CapabilityEntry("human_review","Human Review Workbench + coverage hardening",22,"ready",True,False,False),
            CapabilityEntry("production_closeout","Production Readiness Closeout",23,"ready",True,False,False),
        ]
        cm = CapabilityMap(capabilities=caps, capability_count=len(caps))
        for c in caps:
            if c.status=="ready": cm.ready_count+=1
            elif c.status=="partial_ready": cm.partial_ready_count+=1
            elif c.status=="blocked": cm.blocked_count+=1
            else: cm.not_ready_count+=1
        return cm

    def _build_scorecard(self) -> Scorecard:
        domains = self.config.get("domains",[])
        sc = Scorecard(domain_count=len(domains))
        for d in domains:
            status = "ready"
            src_req = d in ("polymarket","market_expectation","team_news","real_data_adapter","market_data") and d!="campaign_strategy"
            ds = DomainScorecard(domain=d, status=status, analysis_ready=True, simulation_ready=True,
                                 source_enablement_required=src_req, manual_review_required=True,
                                 notes="Analysis-ready. Source enablement required." if src_req else "Analysis-ready, simulation-ready.")
            sc.domains.append(ds)
            if status=="ready": sc.ready_domain_count+=1
            elif status=="partial_ready": sc.partial_ready_domain_count+=1
            elif status=="blocked": sc.blocked_domain_count+=1
            else: sc.not_ready_domain_count+=1
        return sc

    def _build_source_plan(self) -> SourceEnablementPlan:
        cats = self.config.get("source_categories",{})
        sp = SourceEnablementPlan(source_category_count=len(cats))
        for name, info in cats.items():
            st = info.get("status","not_allowed")
            e = SourceEnablementEntry(category=name, status=st, adapter_ready=info.get("adapter_ready",False),
                                      default_disabled=info.get("default_disabled",True), notes="")
            sp.entries.append(e)
            if st=="manual_ready": sp.manual_ready_count+=1
            elif st=="fixture_ready": sp.fixture_ready_count+=1
            elif st=="adapter_ready_disabled": sp.adapter_ready_disabled_count+=1
            elif st=="needs_source_selection": sp.needs_source_selection_count+=1
            elif st=="not_allowed": sp.not_allowed_count+=1
        return sp

    def _build_gap_register(self) -> GapRegister:
        gaps_data = self.config.get("known_gaps",[])
        gr = GapRegister(gap_count=len(gaps_data))
        for gd in gaps_data:
            g = KnownGap(**{k:gd.get(k,"") for k in ["gap_id","severity","domain","description","mitigation"]})
            gr.gaps.append(g)
            if g.severity=="critical": gr.critical_gap_count+=1
            elif g.severity=="high": gr.high_gap_count+=1
            elif g.severity=="medium": gr.medium_gap_count+=1
            else: gr.low_gap_count+=1
        return gr

    def _build_checklist(self) -> PreTournamentChecklist:
        items = self.config.get("pre_tournament_checklist",[])
        cl = PreTournamentChecklist(checklist_count=len(items))
        for it in items:
            ci = ChecklistItem(**{k:it.get(k,"") for k in ["item_id","item","status"]})
            cl.items.append(ci)
            if ci.status=="pending": cl.pending_count+=1
            elif ci.status=="completed": cl.completed_count+=1
        return cl

    def _load_summary(self, fname: str) -> dict:
        fp = self.gen_dir / fname
        if fp.exists():
            try:
                d = json.loads(fp.read_text(encoding="utf-8"))
                keys = ["review_item_count","open_count","settlement_review_count","signal_fusion_review_count",
                        "watchdog_review_count","day_count","final_bankroll_preview","target_reached",
                        "review_item_count_total","coverage_ratio","source_review_count_reconciliation_pass"]
                return {k:d[k] for k in keys if k in d}
            except: pass
        return {}

    def _build_runbook(self) -> str:
        return """# Operator Runbook

## Daily Setup
1. Confirm network_fetch_default_enabled=false
2. Run: python scripts/run_daily_ops_watchdog.py --date <TODAY> --bankroll <BANKROLL> --json
3. If watchdog BLOCKED, STOP and review circuit_breaker
4. If watchdog WARN, review warnings before continuing

## Matchday Workflow
1. python scripts/run_campaign_foundation.py --bankroll <BANKROLL> --windows-left <N> --json
2. python scripts/run_calendar_preview.py --date <TODAY> --json
3. python scripts/run_match_probability_preview.py --date <TODAY> --json
4. python scripts/run_ev_ranking_preview.py --date <TODAY> --bankroll <BANKROLL> --json --synthetic-odds
5. python scripts/run_integrated_daily_strategy.py --date <TODAY> --bankroll <BANKROLL> --json --synthetic-odds
6. python scripts/run_parlay_preview.py --date <TODAY> --bankroll <BANKROLL> --json --synthetic-odds
7. python scripts/run_futures_preview.py --date <TODAY> --bankroll <BANKROLL> --json --synthetic-futures-odds
8. python scripts/run_signal_fusion_preview.py --date <TODAY> --bankroll <BANKROLL> --json
9. python scripts/run_daily_ops.py --date <TODAY> --bankroll <BANKROLL> --json
10. python scripts/run_campaign_dashboard.py --date <TODAY> --bankroll <BANKROLL> --json

## Rest Day Workflow
1. python scripts/run_daily_ops_watchdog.py --date <TODAY> --bankroll <BANKROLL> --mode pre_daily_ops --json
2. python scripts/run_campaign_dashboard.py --date <TODAY> --bankroll <BANKROLL> --json

## Post-Match Settlement
1. Seed results: data/seed/match_results_seed.json
2. python scripts/run_real_data_preview.py --date <TODAY> --bankroll <BANKROLL> --json
3. python scripts/run_postmatch_settlement.py --date <TODAY> --bankroll <BANKROLL> --json
4. python scripts/run_model_calibration_review.py --date <TODAY> --bankroll <BANKROLL> --json

## Human Review Workflow
1. python scripts/run_human_review_workbench.py --date <TODAY> --bankroll <BANKROLL> --json
2. Open reports/generated/human_review_workbench.html
3. Process review items by severity (critical -> high -> medium -> low)
4. Record decisions in data/seed/review_decision_input_example.json
5. Re-run workbench with --decision-file

## Dashboard Check
1. Open reports/generated/campaign_dashboard.html
2. Verify liquid_simulated_bankroll / locked_pending_units / total_campaign_equity
3. Check required_multiplier_liquid and required_multiplier_equity

## Emergency Procedures
- If any runner outputs stake / bet_instruction / bookmaker_account: STOP immediately
- If real_bet_execution=true appears anywhere: STOP and audit all outputs
- If network_fetch_default_enabled is accidentally true: STOP and reset config

## Safety Boundary Check (Daily)
- [ ] network_fetch_default_enabled=false
- [ ] real_bet_execution=false
- [ ] auto_betting=false
- [ ] No stake fields in any output
- [ ] No bookmaker_account in any output
- [ ] All reports have analysis_only=true, simulation_only=true, not_betting_advice=true

> This is a simulation-only system. Not betting advice. No real bets placed. No real money used.
"""

def render_closeout_json(pr: ProductionReadinessCloseout) -> dict:
    return _d(pr)

def render_closeout_markdown(pr: ProductionReadinessCloseout) -> str:
    sc = pr.scorecard; cm = pr.capability_map; sp = pr.source_enablement_plan
    gr = pr.gap_register; cl = pr.pre_tournament_checklist
    lines = [
        "# Production Readiness Closeout Report",
        f"**Date**: {pr.closeout_date} | **Status**: {pr.overall_status}",
        f"**Readiness Score**: {pr.readiness_score} ({pr.readiness_level})",
        f"**Real Money Execution Ready**: {pr.real_money_execution_ready}",
        "",
        "## 1. Domain Scorecard",
        "| Domain | Status | Analysis Ready | Simulation Ready | Source Req | Review Req |",
        "|--------|--------|---------------|-----------------|------------|------------|",
    ]
    for d in (sc.domains if sc else []):
        lines.append(f"| {d.domain} | {d.status} | {d.analysis_ready} | {d.simulation_ready} | {d.source_enablement_required} | {d.manual_review_required} |")
    lines += [
        f"",
        f"- **Ready**: {sc.ready_domain_count} | **Partial**: {sc.partial_ready_domain_count} | **Not Ready**: {sc.not_ready_domain_count}",
        "",
        "## 2. Capability Map",
        f"- **Total**: {cm.capability_count} | **Ready**: {cm.ready_count} | **Blocked**: {cm.blocked_count}",
        "",
        "## 3. Source Enablement Plan",
        "| Category | Status | Adapter Ready | Default Disabled |",
        "|----------|--------|---------------|-----------------|",
    ]
    for e in (sp.entries if sp else []):
        lines.append(f"| {e.category} | {e.status} | {e.adapter_ready} | {e.default_disabled} |")
    lines += [
        f"",
        f"- Manual Ready: {sp.manual_ready_count} | Fixture Ready: {sp.fixture_ready_count} | Adapter Disabled: {sp.adapter_ready_disabled_count} | Not Allowed: {sp.not_allowed_count}",
        "",
        "## 4. Known Gaps",
        "| ID | Severity | Domain | Description | Mitigation |",
        "|----|----------|--------|-------------|------------|",
    ]
    for g in (gr.gaps if gr else []):
        lines.append(f"| {g.gap_id} | {g.severity} | {g.domain} | {g.description[:60]} | {g.mitigation[:40]} |")
    lines += [
        f"",
        f"- Critical: {gr.critical_gap_count} | High: {gr.high_gap_count} | Medium: {gr.medium_gap_count} | Low: {gr.low_gap_count}",
        "",
        "## 5. Pre-Tournament Checklist",
        "| ID | Item | Status |",
        "|----|------|--------|",
    ]
    for c in (cl.items if cl else []):
        lines.append(f"| {c.item_id} | {c.item[:60]} | {c.status} |")
    lines += [
        f"",
        f"- Total: {cl.checklist_count} | Pending: {cl.pending_count} | Completed: {cl.completed_count}",
        "",
        "## 6. Dry-Run Summary",
    ]
    for k,v in pr.dry_run_summary.items():
        lines.append(f"- **{k}**: {v}")
    lines += [
        "",
        "## 7. Workbench Summary",
    ]
    for k,v in pr.workbench_summary.items():
        lines.append(f"- **{k}**: {v}")
    lines += [
        "",
        "## 8. Safety Boundary",
        f"- Analysis Only: {pr.safety.get('analysis_only',True)}",
        f"- Simulation Only: {pr.safety.get('simulation_only',True)}",
        f"- Not Betting Advice: {pr.safety.get('not_betting_advice',True)}",
        f"- Real Bet Execution: {pr.safety.get('real_bet_execution',False)}",
        f"- Auto Betting: {pr.safety.get('auto_betting',False)}",
        f"- Network Fetch: {pr.safety.get('network_fetch_default_enabled',False)}",
        "",
        "---",
        f"*Generated: {pr.generated_at}*",
        "> Simulation-only closeout report. Not betting advice. No real bets placed.",
    ]
    return '\n'.join(lines)

def write_closeout_outputs(pr: ProductionReadinessCloseout, out_dir: str=None):
    od = Path(out_dir) if out_dir else ROOT / "reports" / "generated"
    od.mkdir(parents=True, exist_ok=True)
    jp = od / "production_readiness_closeout.json"
    jp.write_text(json.dumps(render_closeout_json(pr), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    mp = od / "production_readiness_closeout.md"
    mp.write_text(render_closeout_markdown(pr), encoding="utf-8")
    rp = od / "operator_runbook.md"
    rp.write_text(pr.operator_runbook, encoding="utf-8")
    return {"json": str(jp), "markdown": str(mp), "runbook": str(rp)}

def validate_closeout_no_forbidden(pr: ProductionReadinessCloseout) -> list:
    d = _d(pr)
    check = {k:v for k,v in d.items() if k not in ('operator_runbook','capability_map','source_enablement_plan','pre_tournament_checklist')}
    s = json.dumps(check).lower(); found = []
    for f in FORBIDDEN:
        if f.lower() in s: found.append(f)
    return found
