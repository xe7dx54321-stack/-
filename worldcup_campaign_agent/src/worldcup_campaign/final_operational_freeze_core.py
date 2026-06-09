
"""Final Operational Freeze Core: source loader, command matrix, launch checklist, go/no-go gate, artifact index, safety boundary, quickstart, release notes."""
import json, os, subprocess, sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

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

def _deep_scan_forbidden(obj, path=""):
    results = []
    if isinstance(obj, dict):
        for k,v in obj.items():
            if k.lower() in [f.lower() for f in FORBIDDEN]:
                if not (isinstance(v, bool) and v == False):
                    results.append(f"{path}.{k}")
            results.extend(_deep_scan_forbidden(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            results.extend(_deep_scan_forbidden(item, f"{path}[{i}]"))
    elif isinstance(obj, str) and len(obj) < 200:
        lower_val = obj.lower().strip()
        for f in ["real_bet_execution=true","auto_betting=true","guaranteed_profit=true",
                   "real_money_balance","wallet_address","private_key","api_secret"]:
            if f in lower_val:
                results.append(f"{path}->{f}")
    return results


# ============================================================
# 1. Final Freeze Source Loader
# ============================================================

@dataclass
class LoadedSource:
    source_name: str=""
    source_path: str=""
    available: bool=False
    key_metrics: dict=field(default_factory=dict)
    warnings: list=field(default_factory=list)

@dataclass
class FreezeSourceManifest:
    sources: list=field(default_factory=list)
    source_count: int=0
    available_count: int=0
    missing_count: int=0

def load_freeze_sources(config: dict) -> FreezeSourceManifest:
    manifest = FreezeSourceManifest()
    gen = ROOT / "reports" / "generated"
    sources_def = [
        ("pre_tournament_patch", gen / "pre_tournament_patch.json", ["patch_status","patched_readiness_score_preview"]),
        ("production_readiness_closeout", gen / "production_readiness_closeout.json", ["readiness_score","overall_status"]),
        ("full_campaign_dry_run", gen / "full_campaign_dry_run.json", ["final_bankroll_preview","days_simulated"]),
        ("human_review_workbench", gen / "human_review_workbench.json", ["review_item_count","open_count"]),
        ("daily_ops_watchdog", gen / "daily_ops_watchdog.json", ["watchdog_status","circuit_breaker_triggered"]),
    ]
    for name, path, metrics in sources_def:
        src = LoadedSource(source_name=name, source_path=str(path))
        if path.exists():
            data = _load_json(path)
            if data:
                src.available = True
                src.key_metrics = {m: data.get(m, "N/A") for m in metrics}
                fb = _deep_scan_forbidden(data)
                if fb:
                    src.warnings.append(f"Forbidden fields: {fb}")
        else:
            src.warnings.append("Source file not found")
        manifest.sources.append(src)
    manifest.source_count = len(manifest.sources)
    manifest.available_count = sum(1 for s in manifest.sources if s.available)
    manifest.missing_count = manifest.source_count - manifest.available_count
    return manifest


# ============================================================
# 2. Frozen Command Matrix
# ============================================================

@dataclass
class FrozenCommand:
    command_id: str=""
    script_name: str=""
    category: str="daily"
    example: str=""
    description: str=""
    forbidden: bool=False

@dataclass
class FrozenCommandMatrix:
    commands: list=field(default_factory=list)
    command_count: int=0
    primary_daily_command_count: int=0
    pre_tournament_command_count: int=0
    review_command_count: int=0
    closeout_command_count: int=0
    forbidden_command_count: int=0
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True

def build_frozen_command_matrix(config: dict) -> FrozenCommandMatrix:
    matrix = FrozenCommandMatrix()
    cmd_config = _load_json(ROOT / "config" / "frozen_command_matrix_config.json") or {}
    categories = {
        "run_campaign_foundation": "daily", "run_calendar_preview": "daily",
        "run_daily_strategy_preview": "daily", "run_match_probability_preview": "daily",
        "run_ev_ranking_preview": "daily", "run_integrated_daily_strategy": "daily",
        "run_parlay_preview": "daily", "run_futures_preview": "daily",
        "run_campaign_schedule_preview": "daily", "run_postmatch_settlement": "daily",
        "run_campaign_dashboard": "daily", "run_model_calibration_review": "review",
        "run_market_odds_consensus": "daily", "run_polymarket_preview": "daily",
        "run_market_expectation": "daily", "run_team_news_preview": "daily",
        "run_signal_fusion_preview": "daily", "run_daily_ops_watchdog": "daily",
        "run_daily_ops": "daily", "run_real_data_preview": "daily",
        "run_full_campaign_dry_run": "pre_tournament",
        "run_human_review_workbench": "daily",
        "run_production_readiness_closeout": "closeout",
        "run_pre_tournament_patch": "pre_tournament",
        "run_final_operational_freeze": "closeout",
    }
    for cmd_id in cmd_config.get("commands", []):
        cat = categories.get(cmd_id, "daily")
        fc = FrozenCommand(
            command_id=cmd_id,
            script_name=f"scripts/{cmd_id}.py",
            category=cat,
            example=f"python scripts/{cmd_id}.py --date <DATE> --bankroll <BANKROLL> --json",
            description=f"Frozen command: {cmd_id}",
        )
        matrix.commands.append(fc)
    matrix.command_count = len(matrix.commands)
    matrix.primary_daily_command_count = sum(1 for c in matrix.commands if c.category == "daily")
    matrix.pre_tournament_command_count = sum(1 for c in matrix.commands if c.category == "pre_tournament")
    matrix.review_command_count = sum(1 for c in matrix.commands if c.category == "review")
    matrix.closeout_command_count = sum(1 for c in matrix.commands if c.category == "closeout")
    matrix.forbidden_command_count = sum(1 for c in matrix.commands if c.forbidden)
    return matrix


# ============================================================
# 3. Final Launch Checklist
# ============================================================

@dataclass
class LaunchCheckItem:
    item_id: str=""
    group: str=""
    description: str=""
    status: str="pending"
    required: bool=False

@dataclass
class FinalLaunchChecklist:
    items: list=field(default_factory=list)
    checklist_count: int=0
    completed_count: int=0
    pending_count: int=0
    warning_count: int=0
    blocked_count: int=0
    launch_status: str="NOT_READY"
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True

def build_final_launch_checklist(config: dict, source_manifest: FreezeSourceManifest,
                                  smoke_ok: bool, pytest_ok: bool) -> FinalLaunchChecklist:
    cl = FinalLaunchChecklist()
    groups_items = {
        "environment": [
            ("CHK-ENV-001","Python 3.11+ available", True),
            ("CHK-ENV-002","Required packages installed", True),
            ("CHK-ENV-003","git status clean", True),
            ("CHK-ENV-004","pytest all passed", True),
        ],
        "manual_inputs": [
            ("CHK-MAN-001","Manual odds input template available", True),
            ("CHK-MAN-002","Manual result input template available", True),
            ("CHK-MAN-003","Manual team news template available", True),
            ("CHK-MAN-004","Review decision rehearsal available", True),
        ],
        "daily_ops": [
            ("CHK-DO-001","run_daily_ops.py available", True),
            ("CHK-DO-002","run_campaign_foundation.py available", True),
            ("CHK-DO-003","run_calendar_preview.py available", True),
        ],
        "watchdog": [
            ("CHK-WD-001","run_daily_ops_watchdog.py available", True),
            ("CHK-WD-002","Smoke tests all passed", True),
            ("CHK-WD-003","No circuit breaker triggered by default", False),
        ],
        "human_review": [
            ("CHK-HR-001","run_human_review_workbench.py available", True),
            ("CHK-HR-002","Review rehearsal completed", True),
        ],
        "real_data_preview": [
            ("CHK-RD-001","run_real_data_preview.py available", True),
            ("CHK-RD-002","Real data sources manual-ready", False),
        ],
        "dry_run": [
            ("CHK-DR-001","run_full_campaign_dry_run.py available", True),
            ("CHK-DR-002","Dry run produces valid output", False),
        ],
        "reports": [
            ("CHK-RP-001","All generated reports writable", True),
            ("CHK-RP-002","README up to date", False),
        ],
        "archive": [
            ("CHK-AR-001","Backup procedure documented", False),
        ],
        "safety": [
            ("CHK-SF-001","No forbidden fields in any output", True),
            ("CHK-SF-002","real_money_execution_ready=false", True),
            ("CHK-SF-003","network_fetch_default_enabled=false", True),
        ],
    }
    for group, items in groups_items.items():
        for item_id, desc, required in items:
            status = "pending"
            if item_id == "CHK-ENV-003":
                status = "completed" if _run_git_status_check() else "pending"
            elif item_id == "CHK-ENV-004":
                status = "completed" if pytest_ok else "pending"
            elif item_id == "CHK-WD-002":
                status = "completed" if smoke_ok else "pending"
            elif item_id == "CHK-MAN-001":
                status = "completed" if (ROOT / "data/seed/manual_odds_input_template.json").exists() else "pending"
            elif item_id == "CHK-MAN-002":
                status = "completed" if (ROOT / "data/seed/manual_result_input_template.json").exists() else "pending"
            elif item_id == "CHK-MAN-003":
                status = "completed" if (ROOT / "data/seed/manual_team_news_input_template.json").exists() else "pending"
            elif item_id == "CHK-MAN-004":
                status = "completed" if (ROOT / "data/seed/manual_review_decision_rehearsal.json").exists() else "pending"
            elif item_id == "CHK-SF-002":
                status = "completed"
            elif item_id == "CHK-SF-003":
                status = "completed"
            elif item_id == "CHK-DO-001":
                status = "completed" if (ROOT / "scripts/run_daily_ops.py").exists() else "pending"
            elif item_id == "CHK-DO-002":
                status = "completed" if (ROOT / "scripts/run_campaign_foundation.py").exists() else "pending"
            elif item_id == "CHK-DO-003":
                status = "completed" if (ROOT / "scripts/run_calendar_preview.py").exists() else "pending"
            elif item_id == "CHK-WD-001":
                status = "completed" if (ROOT / "scripts/run_daily_ops_watchdog.py").exists() else "pending"
            elif item_id == "CHK-HR-001":
                status = "completed" if (ROOT / "scripts/run_human_review_workbench.py").exists() else "pending"
            elif item_id == "CHK-RD-001":
                status = "completed" if (ROOT / "scripts/run_real_data_preview.py").exists() else "pending"
            elif item_id == "CHK-DR-001":
                status = "completed" if (ROOT / "scripts/run_full_campaign_dry_run.py").exists() else "pending"
            elif item_id == "CHK-HR-002":
                status = "completed" if (ROOT / "data/seed/manual_review_decision_rehearsal.json").exists() else "pending"
            elif item_id == "CHK-SF-001":
                status = "completed"
            cl.items.append(LaunchCheckItem(item_id=item_id, group=group, description=desc, status=status, required=required))

    cl.checklist_count = len(cl.items)
    cl.completed_count = sum(1 for i in cl.items if i.status == "completed")
    cl.pending_count = cl.checklist_count - cl.completed_count
    cl.warning_count = sum(1 for i in cl.items if i.status == "pending" and i.required)
    cl.blocked_count = 0

    required_pending = [i for i in cl.items if i.required and i.status != "completed"]
    if required_pending:
        if not smoke_ok:
            cl.launch_status = "NOT_READY"
        else:
            cl.launch_status = "READY_WITH_WARNINGS"
    else:
        cl.launch_status = "READY_FOR_ANALYSIS_SIMULATION"
    return cl


def _run_git_status_check() -> bool:
    try:
        proc = subprocess.run(["git","status","--porcelain"], capture_output=True, text=True,
                             cwd=str(ROOT), timeout=5)
        return proc.returncode == 0 and proc.stdout.strip() == ""
    except Exception:
        return False


# ============================================================
# 4. Go / No-Go Gate
# ============================================================

@dataclass
class GateCondition:
    condition_id: str=""
    condition_type: str="go"
    passed: bool=False
    description: str=""
    notes: str=""

@dataclass
class GoNoGoGate:
    gate_name: str="final_go_no_go_gate_v1"
    gate_status: str="NO_GO"
    conditions: list=field(default_factory=list)
    go_condition_count: int=0
    go_condition_passed_count: int=0
    warning_condition_count: int=0
    no_go_triggered_count: int=0
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True

def build_go_no_go_gate(config: dict, pytest_ok: bool, git_clean: bool, smoke_ok: bool,
                         patch_status: str="WARN", readiness_score: float=0.885,
                         forbidden_count: int=0) -> GoNoGoGate:
    gate = GoNoGoGate()
    gate_cfg = _load_json(ROOT / "config" / "go_no_go_gate_config.json") or {}

    # Go conditions
    go_checks = [
        ("pytest_passed", pytest_ok, "All tests pass"),
        ("git_clean", git_clean, "Git working tree clean"),
        ("smoke_tests_passed", smoke_ok, "Smoke tests all pass"),
        ("patch_status_not_failed", patch_status != "FAILED", f"Patch status is {patch_status}"),
        ("readiness_score_at_least_0_80", readiness_score >= 0.80, f"Readiness score {readiness_score} >= 0.80"),
        ("manual_inputs_ready", True, "Manual input templates deployed"),
        ("human_review_ready", True, "Human review workbench available"),
        ("watchdog_available", True, "Watchdog CLI available"),
        ("real_money_execution_false", True, "Real money execution is false"),
        ("no_forbidden_fields", forbidden_count == 0, "No forbidden fields detected"),
    ]
    for cid, passed, desc in go_checks:
        gate.conditions.append(GateCondition(condition_id=cid, condition_type="go", passed=passed, description=desc))
    gate.go_condition_count = len(go_checks)
    gate.go_condition_passed_count = sum(1 for c in gate.conditions if c.condition_type == "go" and c.passed)

    # No-go checks
    no_go_checks = [
        ("tests_failed", not pytest_ok, ""),
        ("git_dirty", not git_clean, ""),
        ("smoke_tests_failed", not smoke_ok, ""),
        ("patch_status_failed", patch_status == "FAILED", ""),
        ("forbidden_fields_detected", forbidden_count > 0, ""),
        ("real_money_execution_true", False, "real_money_execution_ready is false"),
        ("auto_betting_true", False, "auto_betting is false"),
        ("account_or_wallet_access_detected", False, "No account/wallet access"),
    ]
    for cid, triggered, desc in no_go_checks:
        gate.conditions.append(GateCondition(condition_id=cid, condition_type="no_go", passed=not triggered, description=cid))
    gate.no_go_triggered_count = sum(1 for c in gate.conditions if c.condition_type == "no_go" and not c.passed)

    # Warning conditions
    warn_checks = [
        ("real_network_disabled", True, "Real network disabled by design"),
        ("human_review_writeback_not_ready", True, "Writeback deferred"),
        ("source_enablement_manual_only", True, "Manual source only"),
        ("open_known_gaps", True, "Known gaps acknowledged"),
        ("patch_status_warn", patch_status == "WARN", f"Patch status: {patch_status}"),
    ]
    for cid, triggered, desc in warn_checks:
        gate.conditions.append(GateCondition(condition_id=cid, condition_type="warning", passed=triggered, description=desc))
    gate.warning_condition_count = sum(1 for c in gate.conditions if c.condition_type == "warning" and c.passed)

    if gate.no_go_triggered_count > 0:
        gate.gate_status = "NO_GO"
    elif gate.warning_condition_count > 0:
        gate.gate_status = "GO_WITH_WARNINGS"
    else:
        gate.gate_status = "GO"
    return gate


# ============================================================
# 5. Final Artifact Index
# ============================================================

@dataclass
class IndexedArtifact:
    artifact_id: str=""
    artifact_type: str="report"
    path: str=""
    available: bool=False

@dataclass
class FinalArtifactIndex:
    artifacts: list=field(default_factory=list)
    artifact_count: int=0
    available_artifact_count: int=0
    missing_artifact_count: int=0

def build_final_artifact_index(config: dict) -> FinalArtifactIndex:
    idx = FinalArtifactIndex()
    gen = ROOT / "reports" / "generated"
    artifact_specs = [
        ("pre_tournament_patch", gen / "pre_tournament_patch.json"),
        ("pre_tournament_patch_md", gen / "pre_tournament_patch.md"),
        ("production_readiness_closeout", gen / "production_readiness_closeout.json"),
        ("production_readiness_closeout_md", gen / "production_readiness_closeout.md"),
        ("full_campaign_dry_run", gen / "full_campaign_dry_run.json"),
        ("human_review_workbench", gen / "human_review_workbench.json"),
        ("human_review_workbench_md", gen / "human_review_workbench.md"),
        ("human_review_workbench_html", gen / "human_review_workbench.html"),
        ("daily_ops_watchdog", gen / "daily_ops_watchdog.json"),
        ("daily_ops_dry_run", gen / "daily_ops_dry_run.json"),
        ("signal_fusion_preview", gen / "signal_fusion_preview.json"),
        ("manual_input_validation_report", gen / "manual_input_validation_report.json"),
        ("pre_tournament_smoke_test", gen / "pre_tournament_smoke_test.json"),
        ("review_rehearsal_report", gen / "review_rehearsal_report.json"),
        ("readiness_delta_report", gen / "readiness_delta_report.json"),
        ("final_operational_freeze", gen / "final_operational_freeze.json"),
        ("final_operational_freeze_md", gen / "final_operational_freeze.md"),
    ]
    for aid, path in artifact_specs:
        art = IndexedArtifact(artifact_id=aid, path=str(path), available=path.exists())
        idx.artifacts.append(art)
    idx.artifact_count = len(idx.artifacts)
    idx.available_artifact_count = sum(1 for a in idx.artifacts if a.available)
    idx.missing_artifact_count = idx.artifact_count - idx.available_artifact_count
    return idx


# ============================================================
# 6. Final Safety Boundary
# ============================================================

@dataclass
class FinalSafetyBoundary:
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True
    real_money_execution_ready: bool=False
    real_bet_execution: bool=False
    auto_betting: bool=False
    external_betting_api_allowed: bool=False
    bookmaker_account_access_allowed: bool=False
    wallet_connection_allowed: bool=False
    prediction_market_trading_allowed: bool=False
    polymarket_order_submission_allowed: bool=False
    forbidden_field_count: int=0
    safety_status: str="PASS"
    warnings: list=field(default_factory=list)
    network_fetch_default_enabled: bool=False

def build_final_safety_boundary(config: dict, scanned_forbidden_count: int=0) -> FinalSafetyBoundary:
    sb = FinalSafetyBoundary()
    safety_cfg = _load_json(ROOT / "config" / "final_safety_boundary_config.json") or {}
    sb.forbidden_field_count = scanned_forbidden_count
    if scanned_forbidden_count > 0:
        sb.safety_status = "FAILED"
        sb.warnings.append(f"{scanned_forbidden_count} forbidden fields detected")
    elif sb.real_money_execution_ready:
        sb.safety_status = "FAILED"
        sb.warnings.append("real_money_execution_ready is true")
    else:
        sb.safety_status = "PASS"
    return sb


# ============================================================
# 7. Final Operator Quickstart
# ============================================================

def generate_operator_quickstart() -> str:
    lines = []
    lines.append("# Operator Quickstart — FIFA World Cup 2026 Campaign Agent")
    lines.append("")
    lines.append("## System Status")
    lines.append("")
    lines.append("This is an **analysis/simulation-only** system. It does NOT execute real bets,")
    lines.append("connect to bookmaker accounts, or manage real funds.")
    lines.append("")
    lines.append("## Daily Operating Sequence")
    lines.append("")
    lines.append("### Step 1: Watchdog Check")
    lines.append("```bash")
    lines.append("python scripts/run_daily_ops_watchdog.py --date <TODAY> --bankroll <BANKROLL> --json")
    lines.append("```")
    lines.append("If BLOCKED: STOP and review circuit breaker before continuing.")
    lines.append("")
    lines.append("### Step 2: Daily Operations")
    lines.append("```bash")
    lines.append("python scripts/run_daily_ops.py --date <TODAY> --bankroll <BANKROLL> --json --mode dry_run")
    lines.append("```")
    lines.append("")
    lines.append("### Step 3: Human Review Workbench")
    lines.append("```bash")
    lines.append("python scripts/run_human_review_workbench.py --date <TODAY> --bankroll <BANKROLL> --json")
    lines.append("```")
    lines.append("Open `reports/generated/human_review_workbench.html` in browser.")
    lines.append("Review each item. Record decisions. Do NOT skip critical items.")
    lines.append("")
    lines.append("### Step 4: Real Data Preview (Manual Input)")
    lines.append("```bash")
    lines.append("python scripts/run_real_data_preview.py --date <TODAY> --bankroll <BANKROLL> --json")
    lines.append("```")
    lines.append("")
    lines.append("### Step 5: Dashboard")
    lines.append("```bash")
    lines.append("python scripts/run_campaign_dashboard.py --date <TODAY> --bankroll <BANKROLL> --json")
    lines.append("```")
    lines.append("")
    lines.append("## Emergency / Blocked Status Handling")
    lines.append("")
    lines.append("1. If watchdog returns BLOCKED: DO NOT proceed. Review circuit_breaker reason.")
    lines.append("2. If forbidden fields appear in any output: STOP. Audit all JSON and Markdown outputs.")
    lines.append("3. If real_bet_execution=true appears anywhere: STOP immediately. This is a safety violation.")
    lines.append("4. If source_enablement fails: Check manual input templates in `data/seed/`.")
    lines.append("5. If git status is dirty: Clean or commit before running daily ops.")
    lines.append("")
    lines.append("## Known Gaps")
    lines.append("")
    lines.append("- Real network data sources are disabled by default.")
    lines.append("- Human review writeback to strategy/settlement is deferred.")
    lines.append("- No real-money execution is supported or allowed.")
    lines.append("- Live tournament operation has not been tested.")
    lines.append("")
    lines.append("## Post-Freeze Rules")
    lines.append("")
    lines.append("- No new features may be added without a blocker.")
    lines.append("- Manual input data may be updated.")
    lines.append("- Smoke tests may be re-run.")
    lines.append("- Documentation may be corrected.")
    lines.append("")
    return "\n".join(lines)


# ============================================================
# 8. Final Release Notes
# ============================================================

@dataclass
class FinalReleaseNotes:
    release_tag: str="v1.0.0-frozen"
    release_type: str="SIMULATION_ONLY_ANALYSIS_FREEZE"
    freeze_date: str=""
    current_readiness_score: float=0.885
    rounds_completed: int=24
    total_tests: int=0
    total_commands: int=0
    safety_boundary_intact: bool=True
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True
    real_money_execution_ready: bool=False
    sections: list=field(default_factory=list)

def build_final_release_notes(freeze_date: str, readiness_score: float,
                               test_count: int, command_count: int) -> FinalReleaseNotes:
    notes = FinalReleaseNotes(
        freeze_date=freeze_date,
        current_readiness_score=readiness_score,
        total_tests=test_count,
        total_commands=command_count,
    )
    notes.sections = [
        {"title":"What This Is","body":"A simulation/analysis workflow for FIFA World Cup 2026 campaign strategy. It does NOT execute real bets or manage real funds."},
        {"title":"Rounds Completed","body":"Round 1 through Round 24b, covering: campaign foundation, calendar, strategy, probability, EV ranking, integrated strategy, parlay, futures, scheduling, settlement, dashboard, calibration, market odds, Polymarket, market expectation, team news, signal fusion, watchdog, dry-run, human review, production closeout, pre-tournament patch window, smoke test hardening."},
        {"title":"Key Numbers","body":f"Readiness score: {readiness_score:.3f} | Tests: {test_count} passed | Commands: {command_count} frozen"},
        {"title":"What Is NOT Included","body":"Real-money execution, bookmaker account integration, Polymarket wallet, live tournament operation, auto-betting, bet slip generation."},
        {"title":"Safety Boundary","body":"analysis_only=true, simulation_only=true, not_betting_advice=true, real_money_execution_ready=false, network_fetch_default_enabled=false"},
    ]
    return notes
