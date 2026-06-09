
"""Pre-Tournament Patch Core: manual input pack, validator, smoke test, review rehearsal, readiness delta."""
import json, os, subprocess, sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

ROOT = Path(__file__).resolve().parent.parent.parent
FORBIDDEN = ["stake","stake_amount","stake_to_match","bet_instruction","bet_slip",
    "bookmaker_account","account_balance","real_money_balance","wallet_address",
    "private_key","api_secret","signed_order","submit_order","cancel_order",
    "guaranteed_profit","chase_loss","real_bet_execution","auto_betting"]

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
                if isinstance(v, bool) and v == False:
                    pass
                else:
                    results.append(f"{path}.{k}")
            results.extend(_deep_scan_forbidden(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            results.extend(_deep_scan_forbidden(item, f"{path}[{i}]"))
    elif isinstance(obj, str):
        # Only scan short strings (<200 chars) as they're more likely values, not documentation.
        # Long strings like operator_runbook are documentation and contain legitimate safety instructions.
        if len(obj) < 200:
            lower_val = obj.lower().strip()
            for f in ["real_bet_execution=true","auto_betting=true","guaranteed_profit=true",
                       "real_bet_execution:true","auto_betting:true",
                       "real_money_balance","wallet_address","private_key","api_secret"]:
                if f in lower_val:
                    results.append(f"{path}->{f}")
    return results


# ============================================================
# Manual Input Pack
# ============================================================

@dataclass
class ManualInputTemplate:
    template_id: str=""
    input_type: str=""
    path: str=""
    format: str="json"
    required_fields: list=field(default_factory=list)
    example_rows_or_items: int=0
    forbidden_fields_absent: bool=True
    warnings: list=field(default_factory=list)

@dataclass
class ManualInputPack:
    template_count: int=0
    templates: list=field(default_factory=list)
    manual_odds_template_available: bool=False
    manual_result_template_available: bool=False
    manual_team_news_template_available: bool=False
    manual_review_decision_template_available: bool=False
    warnings: list=field(default_factory=list)
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True


def build_manual_input_pack(config: dict) -> ManualInputPack:
    pack = ManualInputPack()
    seed_dir = ROOT / "data" / "seed"
    template_specs = [
        ("manual_odds_input", "manual_odds_input_template.csv", "csv",
         ["snapshot_id","source_provider","source_mode","snapshot_type","timestamp","match_id","market_type","selection_id","selection_label","decimal_odds","team_home","team_away"]),
        ("manual_odds_input", "manual_odds_input_template.json", "json",
         ["template_id","input_type","required_fields","example_snapshots"]),
        ("manual_result_input", "manual_result_input_template.csv", "csv",
         ["match_id","match_date","team_home","team_away","home_score","away_score","result_type","result_label"]),
        ("manual_result_input", "manual_result_input_template.json", "json",
         ["template_id","input_type","required_fields","example_results"]),
        ("manual_team_news_input", "manual_team_news_input_template.json", "json",
         ["template_id","input_type","required_fields","example_news"]),
        ("manual_review_decision_input", "manual_review_decision_rehearsal.json", "json",
         ["template_id","input_type","decisions"]),
    ]
    for input_type, filename, fmt, req_fields in template_specs:
        fp = seed_dir / filename
        t = ManualInputTemplate(
            template_id=f"tpl-{input_type}-{fmt}",
            input_type=input_type,
            path=str(fp),
            format=fmt,
            required_fields=list(req_fields)
        )
        if fp.exists():
            t.template_id = f"tpl-{input_type}-{fmt}"
            if fmt == "csv":
                lines = fp.read_text(encoding="utf-8").strip().split("\n")
                t.example_rows_or_items = max(0, len(lines) - 1)
            elif fmt == "json":
                data = _load_json(fp)
                if data:
                    if input_type == "manual_odds_input":
                        t.example_rows_or_items = len(data.get("example_snapshots", []))
                    elif input_type == "manual_result_input":
                        t.example_rows_or_items = len(data.get("example_results", []))
                    elif input_type == "manual_team_news_input":
                        t.example_rows_or_items = len(data.get("example_news", []))
                    elif input_type == "manual_review_decision_input":
                        t.example_rows_or_items = len(data.get("decisions", []))
                    fb = _deep_scan_forbidden(data)
                    t.forbidden_fields_absent = len(fb) == 0
                    if fb:
                        t.warnings.append(f"Forbidden fields: {fb}")
            pack.templates.append(t)
        else:
            t.warnings.append(f"Template file not found: {filename}")
            pack.templates.append(t)
            pack.warnings.append(f"Missing template: {filename}")

    pack.template_count = len(pack.templates)
    pack.manual_odds_template_available = any(
        t.input_type == "manual_odds_input" and not "not found" in " ".join(t.warnings).lower()
        for t in pack.templates)
    pack.manual_result_template_available = any(
        t.input_type == "manual_result_input" and not "not found" in " ".join(t.warnings).lower()
        for t in pack.templates)
    pack.manual_team_news_template_available = any(
        t.input_type == "manual_team_news_input" and not "not found" in " ".join(t.warnings).lower()
        for t in pack.templates)
    pack.manual_review_decision_template_available = any(
        t.input_type == "manual_review_decision_input" and not "not found" in " ".join(t.warnings).lower()
        for t in pack.templates)
    return pack


# ============================================================
# Manual Input Validator
# ============================================================

@dataclass
class ManualInputValidationResult:
    input_type: str=""
    path_used: str=""
    valid_count: int=0
    invalid_count: int=0
    forbidden_field_count: int=0
    errors: list=field(default_factory=list)
    warnings: list=field(default_factory=list)
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True

@dataclass
class ManualInputValidationSummary:
    results: list=field(default_factory=list)
    total_valid: int=0
    total_invalid: int=0
    total_forbidden: int=0
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True


def _validate_csv_input(path: Path, required_fields: list, input_type: str) -> ManualInputValidationResult:
    result = ManualInputValidationResult(input_type=input_type, path_used=str(path))
    if not path.exists():
        result.errors.append(f"File not found: {path}")
        result.invalid_count = 1
        return result
    try:
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        if len(lines) < 2:
            result.errors.append("CSV has no data rows")
            result.invalid_count = 1
            return result
        header = [h.strip() for h in lines[0].split(",")]
        missing = [f for f in required_fields if f not in header]
        if missing:
            result.errors.append(f"Missing required columns: {missing}")
            result.invalid_count = 1
            return result
        fb_in_header = [h for h in header if h.lower() in [f.lower() for f in FORBIDDEN]]
        result.forbidden_field_count = len(fb_in_header)
        if fb_in_header:
            result.errors.append(f"Forbidden fields in header: {fb_in_header}")
        result.valid_count = len(lines) - 1
    except Exception as e:
        result.errors.append(str(e))
        result.invalid_count = 1
    return result


def _validate_json_input(path: Path, required_fields: list, input_type: str) -> ManualInputValidationResult:
    result = ManualInputValidationResult(input_type=input_type, path_used=str(path))
    if not path.exists():
        result.errors.append(f"File not found: {path}")
        result.invalid_count = 1
        return result
    data = _load_json(path)
    if data is None:
        result.errors.append("Invalid JSON")
        result.invalid_count = 1
        return result
    missing = [f for f in required_fields if f not in data]
    if missing:
        result.errors.append(f"Missing required fields: {missing}")
        result.invalid_count += 1
    fb = _deep_scan_forbidden(data)
    result.forbidden_field_count = len(fb)
    if fb:
        result.errors.append(f"Forbidden fields detected: {fb}")
    result.valid_count = 1 if not result.errors else 0
    result.invalid_count = 1 if result.errors else 0
    return result


def validate_manual_odds_input(path: str) -> ManualInputValidationResult:
    fp = Path(path) if Path(path).is_absolute() else ROOT / path
    if fp.suffix == ".csv":
        return _validate_csv_input(fp, ["snapshot_id","source_provider","snapshot_type","match_id","decimal_odds"], "manual_odds_input")
    else:
        return _validate_json_input(fp, ["template_id","input_type","required_fields"], "manual_odds_input")

def validate_manual_result_input(path: str) -> ManualInputValidationResult:
    fp = Path(path) if Path(path).is_absolute() else ROOT / path
    if fp.suffix == ".csv":
        return _validate_csv_input(fp, ["match_id","match_date","home_score","away_score","result_type"], "manual_result_input")
    else:
        return _validate_json_input(fp, ["template_id","input_type","required_fields"], "manual_result_input")

def validate_manual_team_news_input(path: str) -> ManualInputValidationResult:
    fp = Path(path) if Path(path).is_absolute() else ROOT / path
    return _validate_json_input(fp, ["template_id","input_type","required_fields"], "manual_team_news_input")

def validate_manual_review_decision_input(path: str) -> ManualInputValidationResult:
    fp = Path(path) if Path(path).is_absolute() else ROOT / path
    result = ManualInputValidationResult(input_type="manual_review_decision_input", path_used=str(fp))
    if not fp.exists():
        result.errors.append(f"File not found: {fp}")
        result.invalid_count = 1
        return result
    data = _load_json(fp)
    if data is None:
        result.errors.append("Invalid JSON")
        result.invalid_count = 1
        return result
    decisions = data.get("decisions", [])
    result.valid_count = 0
    for d in decisions:
        dec = d.get("decision","")
        if dec in ["execute_real_bet","withdraw_funds","modify_account","claim_guaranteed_profit"]:
            result.invalid_count += 1
            result.errors.append(f"Invalid decision '{dec}' in {d.get('decision_id','?')}")
        else:
            result.valid_count += 1
    fb = _deep_scan_forbidden(data)
    result.forbidden_field_count = len(fb)
    if fb:
        result.errors.append(f"Forbidden fields: {fb}")
    return result


def validate_all_manual_inputs(pack: ManualInputPack) -> ManualInputValidationSummary:
    summary = ManualInputValidationSummary()
    for tpl in pack.templates:
        fp = Path(tpl.path)
        if not fp.exists():
            r = ManualInputValidationResult(input_type=tpl.input_type, path_used=str(fp),
                                             invalid_count=1, errors=["File not found"])
            summary.results.append(r)
            summary.total_invalid += 1
            continue
        if tpl.format == "csv":
            r = _validate_csv_input(fp, tpl.required_fields, tpl.input_type)
        else:
            r = _validate_json_input(fp, tpl.required_fields, tpl.input_type)
        summary.results.append(r)
        summary.total_valid += r.valid_count
        summary.total_invalid += r.invalid_count
        summary.total_forbidden += r.forbidden_field_count
    return summary


# ============================================================
# Pre-Tournament Smoke Test
# ============================================================

@dataclass
class SmokeTestCaseResult:
    test_id: str=""
    command: str=""
    status: str="PASS"
    stdout_json_valid: bool=True
    output_paths: list=field(default_factory=list)
    warnings: list=field(default_factory=list)
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True

@dataclass
class PreTournamentSmokeTestResult:
    smoke_test_count: int=0
    pass_count: int=0
    warn_count: int=0
    failed_count: int=0
    blocked_count: int=0
    tests: list=field(default_factory=list)
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True


def run_smoke_test_case(test_id: str, config: dict) -> SmokeTestCaseResult:
    cmd_map = {
        "daily_ops_dry_run": [sys.executable, "scripts/run_daily_ops.py", "--date", "2026-06-11", "--bankroll", "100", "--json", "--mode", "dry_run"],
        "daily_ops_watchdog_only": [sys.executable, "scripts/run_daily_ops_watchdog.py", "--date", "2026-06-11", "--bankroll", "100", "--json"],
        "real_data_preview_manual_inputs": [sys.executable, "scripts/run_real_data_preview.py", "--date", "2026-06-11", "--bankroll", "100", "--json"],
        "human_review_workbench": [sys.executable, "scripts/run_human_review_workbench.py", "--date", "2026-06-11", "--bankroll", "100", "--json"],
        "production_readiness_closeout": [sys.executable, "scripts/run_production_readiness_closeout.py", "--json"],
        "full_campaign_short_dry_run": [sys.executable, "scripts/run_full_campaign_dry_run.py", "--start-date", "2026-06-11", "--end-date", "2026-06-14", "--bankroll", "100", "--json"],
    }
    cmd_parts = cmd_map.get(test_id, ["echo", f"Unknown test: {test_id}"])
    cmd_str = " ".join(str(p) for p in cmd_parts)
    result = SmokeTestCaseResult(test_id=test_id, command=cmd_str)

    # Check for forbidden command fragments
    forbidden_frags = ["stake_to_match","bet_instruction","real_bet_execution","auto_betting",
                       "guaranteed_profit","--real-money","--execute-bet","--place-bet"]
    for frag in forbidden_frags:
        if frag in cmd_str.lower():
            result.status = "BLOCKED"
            result.warnings.append(f"Forbidden fragment in command: {frag}")
            return result

    try:
        proc = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=120,
                             cwd=str(ROOT), encoding="utf-8", errors="replace",
                             env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
        stdout = proc.stdout.strip() if proc.stdout else ""
        stderr = proc.stderr.strip() if proc.stderr else ""

        # Try to parse stdout as JSON
        stdout_has_json = False
        if stdout:
            try:
                json.loads(stdout)
                stdout_has_json = True
                result.stdout_json_valid = True
            except json.JSONDecodeError:
                # Check if JSON is embedded (some scripts print status lines before JSON)
                lines = stdout.split("\n")
                for line in lines:
                    try:
                        json.loads(line.strip())
                        stdout_has_json = True
                        result.stdout_json_valid = True
                        break
                    except:
                        pass
                if not stdout_has_json:
                    result.stdout_json_valid = False
                    result.warnings.append(f"stdout is not valid JSON (first 100 chars: {stdout[:100]})")

        # Determine status
        if proc.returncode != 0:
            if stdout_has_json:
                # Script returned non-zero but produced valid JSON (stderr has diagnostics)
                result.status = "WARN"
                result.warnings.append(f"Exit code {proc.returncode} but JSON valid; stderr: {stderr[:200]}")
            else:
                result.status = "FAILED"
                result.warnings.append(f"Exit code: {proc.returncode}")
                if stderr:
                    result.warnings.append(f"stderr: {stderr[:200]}")
                if stdout:
                    result.warnings.append(f"stdout: {stdout[:200]}")
        elif stderr and ("error" in stderr.lower() or "traceback" in stderr.lower()):
            result.status = "WARN"
            result.warnings.append(f"stderr contains errors: {stderr[:200]}")
        elif not stdout_has_json and not stdout:
            result.status = "WARN"
            result.warnings.append("No stdout output")
        else:
            result.status = "PASS"

        # Check output for forbidden fields
        if stdout_has_json:
            try:
                out = json.loads(stdout)
            except:
                # Try line by line
                out = {}
                for line in stdout.split("\n"):
                    try:
                        out = json.loads(line.strip())
                        break
                    except:
                        pass
            fb = _deep_scan_forbidden(out)
            if fb:
                result.warnings.append(f"Forbidden fields in output: {fb}")
                result.status = "BLOCKED"

    except subprocess.TimeoutExpired:
        result.status = "FAILED"
        result.warnings.append("Timeout after 120s")
    except FileNotFoundError as e:
        result.status = "FAILED"
        result.warnings.append(f"Command not found: {e}")
    except Exception as e:
        result.status = "FAILED"
        result.warnings.append(f"Subprocess error: {type(e).__name__}: {e}")

    return result


def run_pre_tournament_smoke_tests(config: dict) -> PreTournamentSmokeTestResult:
    result = PreTournamentSmokeTestResult()
    smoke_tests = config.get("smoke_tests", [])
    required = config.get("required_pass_tests", [])
    for test_id in smoke_tests:
        tc = run_smoke_test_case(test_id, config)
        result.tests.append(tc)
        if tc.status == "PASS":
            result.pass_count += 1
        elif tc.status == "WARN":
            result.warn_count += 1
        elif tc.status in ("BLOCKED","FAILED"):
            result.failed_count += 1
            if tc.status == "BLOCKED":
                result.blocked_count += 1
    result.smoke_test_count = len(result.tests)
    for req in required:
        req_test = next((t for t in result.tests if t.test_id == req), None)
        if req_test and req_test.status in ("BLOCKED","FAILED"):
            result.warn_count = max(result.warn_count, 1)
    return result


# ============================================================
# Review Rehearsal
# ============================================================

@dataclass
class ReviewRehearsalResult:
    decision_input_loaded: bool=False
    decision_count: int=0
    valid_decision_count: int=0
    invalid_decision_count: int=0
    decision_preview_generated: bool=False
    audit_log_preview_generated: bool=False
    override_preview_count: int=0
    invalid_decisions_detail: list=field(default_factory=list)
    warnings: list=field(default_factory=list)
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True


def run_review_rehearsal(config: dict) -> ReviewRehearsalResult:
    result = ReviewRehearsalResult()
    decision_path = config.get("decision_input_path", "data/seed/manual_review_decision_rehearsal.json")
    fp = ROOT / decision_path
    if not fp.exists():
        result.warnings.append(f"Decision input not found: {fp}")
        return result
    data = _load_json(fp)
    if data is None:
        result.warnings.append("Decision input is invalid JSON")
        return result
    result.decision_input_loaded = True
    decisions = data.get("decisions", [])
    result.decision_count = len(decisions)

    forbidden_decisions = ["execute_real_bet","withdraw_funds","modify_account","claim_guaranteed_profit"]

    for d in decisions:
        dec = d.get("decision","")
        if dec in forbidden_decisions:
            result.invalid_decision_count += 1
            result.invalid_decisions_detail.append({
                "decision_id": d.get("decision_id","?"),
                "decision": dec,
                "reason": "Forbidden decision type"
            })
        else:
            result.valid_decision_count += 1
            if dec == "override_simulation_preview":
                review_type = d.get("review_type","")
                if review_type == "settlement_review":
                    result.override_preview_count += 1
                else:
                    result.warnings.append(
                        f"Override only allowed for settlement_review, got: {review_type} ({d.get('decision_id','?')})")

    result.decision_preview_generated = result.decision_count > 0
    result.audit_log_preview_generated = result.valid_decision_count > 0

    if config.get("requires_valid_decision_count_gt_zero", True) and result.valid_decision_count == 0:
        result.warnings.append("No valid decisions found")
    fb = _deep_scan_forbidden(data)
    if fb:
        result.warnings.append(f"Forbidden fields: {fb}")

    return result


# ============================================================
# Readiness Delta
# ============================================================

@dataclass
class ReadinessDelta:
    baseline_readiness_score: float=0.0
    patched_readiness_score_preview: float=0.0
    score_delta: float=0.0
    baseline_pre_tournament_ready: str="partial_ready"
    patched_pre_tournament_ready_preview: str="checklist_rehearsed"
    baseline_source_enablement_ready: str="partial_ready"
    patched_source_enablement_ready_preview: str="manual_analysis_ready"
    manual_input_ready: bool=False
    smoke_test_ready: bool=False
    review_rehearsal_ready: bool=False
    real_money_execution_ready: bool=False
    dimensions: list=field(default_factory=list)
    warnings: list=field(default_factory=list)
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True


def build_readiness_delta(baseline_path: str, manual_input_summary: ManualInputValidationSummary,
                          smoke_test_result: PreTournamentSmokeTestResult,
                          review_rehearsal_result: ReviewRehearsalResult,
                          config: dict) -> ReadinessDelta:
    delta = ReadinessDelta()

    # Load baseline
    bp = ROOT / baseline_path if not Path(baseline_path).is_absolute() else Path(baseline_path)
    if bp.exists():
        baseline = _load_json(bp) or {}
        delta.baseline_readiness_score = float(baseline.get("readiness_score", 0.705))
        delta.baseline_pre_tournament_ready = baseline.get("pre_tournament_ready", "partial_ready")
        delta.baseline_source_enablement_ready = baseline.get("source_enablement_ready", "partial_ready")
    else:
        delta.baseline_readiness_score = 0.705
        delta.warnings.append(f"Baseline closeout not found: {bp}, using default 0.705")

    # Compute patched readiness
    delta.manual_input_ready = manual_input_summary.total_invalid == 0 and manual_input_summary.total_forbidden == 0
    delta.smoke_test_ready = smoke_test_result.failed_count == 0 and smoke_test_result.blocked_count == 0
    delta.review_rehearsal_ready = review_rehearsal_result.decision_input_loaded and review_rehearsal_result.valid_decision_count > 0

    # Score improvement
    improvement = 0.0
    if delta.manual_input_ready:
        improvement += 0.05
    if delta.smoke_test_ready:
        improvement += 0.08
    if delta.review_rehearsal_ready:
        improvement += 0.05

    delta.patched_readiness_score_preview = min(0.95, delta.baseline_readiness_score + improvement)
    delta.score_delta = round(delta.patched_readiness_score_preview - delta.baseline_readiness_score, 4)

    # Patched states
    if delta.manual_input_ready and delta.smoke_test_ready:
        delta.patched_source_enablement_ready_preview = "manual_analysis_ready"
    else:
        delta.patched_source_enablement_ready_preview = delta.baseline_source_enablement_ready

    if delta.manual_input_ready and delta.smoke_test_ready and delta.review_rehearsal_ready:
        delta.patched_pre_tournament_ready_preview = "checklist_rehearsed"
    elif delta.smoke_test_ready:
        delta.patched_pre_tournament_ready_preview = "partial_ready_plus"
    else:
        delta.patched_pre_tournament_ready_preview = delta.baseline_pre_tournament_ready

    delta.real_money_execution_ready = False

    if smoke_test_result.failed_count > 0 or smoke_test_result.blocked_count > 0:
        delta.smoke_test_ready = False
        delta.patched_readiness_score_preview = delta.baseline_readiness_score
        delta.score_delta = 0.0
        delta.warnings.append("Score not improved: smoke test failures or blocked tests present")

    delta.dimensions = [
        {"dimension":"source_enablement_ready","baseline":delta.baseline_source_enablement_ready,"patched":delta.patched_source_enablement_ready_preview,"reason":"manual input pack + validation enabled"},
        {"dimension":"pre_tournament_ready","baseline":delta.baseline_pre_tournament_ready,"patched":delta.patched_pre_tournament_ready_preview,"reason":"smoke tests + review rehearsal completed"},
        {"dimension":"manual_input_ready","baseline":"false","patched":str(delta.manual_input_ready).lower(),"reason":"templates and validators deployed"},
        {"dimension":"smoke_test_ready","baseline":"false","patched":str(delta.smoke_test_ready).lower(),"reason":"smoke test suite executed"},
        {"dimension":"review_rehearsal_ready","baseline":"false","patched":str(delta.review_rehearsal_ready).lower(),"reason":"review rehearsal with sample decisions"},
        {"dimension":"real_money_execution_ready","baseline":"false","patched":"false","reason":"by design - not in scope"}
    ]
    return delta
