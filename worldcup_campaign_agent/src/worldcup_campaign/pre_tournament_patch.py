
"""Pre-Tournament Patch: aggregator, renderer, runner."""
import json, sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from worldcup_campaign.pre_tournament_patch_core import (
    ManualInputPack, ManualInputValidationSummary,
    PreTournamentSmokeTestResult, ReviewRehearsalResult, ReadinessDelta,
    build_manual_input_pack, validate_all_manual_inputs,
    run_pre_tournament_smoke_tests, run_review_rehearsal, build_readiness_delta,
    _d, _load_json, _deep_scan_forbidden, ROOT, FORBIDDEN
)

# ============================================================
# PreTournamentPatch Aggregator
# ============================================================

@dataclass
class PreTournamentPatch:
    campaign_name: str="worldcup_2026_high_odds_campaign"
    patch_version: str="v1.0"
    manual_input_pack: Optional[ManualInputPack]=None
    manual_input_validation: Optional[ManualInputValidationSummary]=None
    smoke_test_result: Optional[PreTournamentSmokeTestResult]=None
    review_rehearsal_result: Optional[ReviewRehearsalResult]=None
    readiness_delta: Optional[ReadinessDelta]=None
    patch_status: str="PASS"
    remaining_gaps: list=field(default_factory=list)
    safety: dict=field(default_factory=dict)
    warnings: list=field(default_factory=list)
    generated_at: str=""
    analysis_only: bool=True
    simulation_only: bool=True
    not_betting_advice: bool=True
    real_money_execution_ready: bool=False


def build_pre_tournament_patch(config_paths: dict) -> PreTournamentPatch:
    patch = PreTournamentPatch(generated_at=datetime.now().isoformat())

    # Load configs
    patch_cfg = _load_json(ROOT / "config" / "pre_tournament_patch_config.json") or {}
    manual_cfg = _load_json(ROOT / "config" / "manual_input_pack_config.json") or {}
    smoke_cfg = _load_json(ROOT / "config" / "pre_tournament_smoke_test_config.json") or {}
    rehearsal_cfg = _load_json(ROOT / "config" / "review_rehearsal_config.json") or {}
    delta_cfg = _load_json(ROOT / "config" / "readiness_delta_config.json") or {}

    # 1. Manual Input Pack
    pack = build_manual_input_pack(manual_cfg)
    patch.manual_input_pack = pack

    # 2. Manual Input Validation
    validation = validate_all_manual_inputs(pack)
    patch.manual_input_validation = validation

    # 3. Smoke Test
    smoke = run_pre_tournament_smoke_tests(smoke_cfg)
    patch.smoke_test_result = smoke

    # 4. Review Rehearsal
    rehearsal = run_review_rehearsal(rehearsal_cfg)
    patch.review_rehearsal_result = rehearsal

    # 5. Readiness Delta
    baseline_path = delta_cfg.get("baseline_closeout", "reports/generated/production_readiness_closeout.json")
    delta = build_readiness_delta(baseline_path, validation, smoke, rehearsal, delta_cfg)
    patch.readiness_delta = delta

    # Determine patch status
    required_tests = smoke_cfg.get("required_pass_tests", [])
    required_failed = any(
        t.status in ("BLOCKED","FAILED")
        for t in smoke.tests if t.test_id in required_tests
    )
    has_forbidden = validation.total_forbidden > 0
    real_money_true = not delta.real_money_execution_ready

    if has_forbidden or not real_money_true:
        patch.patch_status = "BLOCKED"
        patch.warnings.append("Forbidden fields detected or real_money_execution_ready violation")
    elif required_failed:
        patch.patch_status = "FAILED"
        patch.warnings.append("Required smoke tests failed")
    elif smoke.failed_count > 0 or smoke.blocked_count > 0:
        patch.patch_status = "DEGRADED"
        patch.warnings.append("Some smoke tests failed or blocked")
    elif rehearsal.invalid_decision_count > 0:
        patch.patch_status = "WARN"
        patch.warnings.append("Review rehearsal has invalid decisions")
    else:
        patch.patch_status = "PASS"

    # Remaining gaps
    patch.remaining_gaps = [
        {"gap":"Real network sources still disabled","severity":"medium","status":"deferred","next_action":"Enable after manual rehearsal confirmed"},
        {"gap":"Human review writeback not connected","severity":"high","status":"deferred","next_action":"Connect writeback after rehearsal passes"},
        {"gap":"Real-money execution not allowed","severity":"info","status":"by_design","next_action":"N/A - not in scope"},
        {"gap":"Live tournament operation not tested","severity":"high","status":"pending","next_action":"Run dress rehearsal with real data before first matchday"},
    ]

    # Safety
    patch.safety = {
        "analysis_only": True,
        "simulation_only": True,
        "not_betting_advice": True,
        "real_bet_execution": False,
        "auto_betting": False,
        "real_money_execution_ready": False,
        "network_fetch_default_enabled": False,
        "external_betting_api_allowed": False,
        "bookmaker_account_access_allowed": False,
        "wallet_connection_allowed": False,
    }

    return patch


# ============================================================
# Renderer
# ============================================================

def render_pre_tournament_patch_json(patch: PreTournamentPatch) -> dict:
    out = {
        "campaign_name": patch.campaign_name,
        "patch_version": patch.patch_version,
        "patch_status": patch.patch_status,
        "generated_at": patch.generated_at,
        "analysis_only": True,
        "simulation_only": True,
        "not_betting_advice": True,
        "real_money_execution_ready": False,
    }
    if patch.manual_input_pack:
        out["manual_input_pack"] = _d(patch.manual_input_pack)
    if patch.manual_input_validation:
        out["manual_input_validation"] = _d(patch.manual_input_validation)
    if patch.smoke_test_result:
        out["smoke_test_result"] = _d(patch.smoke_test_result)
    if patch.review_rehearsal_result:
        out["review_rehearsal_result"] = _d(patch.review_rehearsal_result)
    if patch.readiness_delta:
        out["readiness_delta"] = _d(patch.readiness_delta)
    out["remaining_gaps"] = patch.remaining_gaps
    out["safety"] = patch.safety
    out["warnings"] = patch.warnings
    return out


def render_pre_tournament_patch_markdown(patch: PreTournamentPatch) -> str:
    lines = []
    lines.append("# Pre-Tournament Patch Window")
    lines.append("")
    lines.append("## 1. Patch Summary")
    lines.append("")
    lines.append(f"- **Patch status:** {patch.patch_status}")
    delta = patch.readiness_delta
    if delta:
        lines.append(f"- **Baseline readiness:** {delta.baseline_readiness_score:.3f}")
        lines.append(f"- **Patched readiness preview:** {delta.patched_readiness_score_preview:.3f}")
        lines.append(f"- **Score delta:** {delta.score_delta:+.3f}")
    lines.append("- **Real-money execution ready:** false")
    lines.append("")

    # Manual Input Pack
    lines.append("## 2. Manual Input Pack")
    lines.append("")
    lines.append("| Input Type | Template | Format | Valid | Warning |")
    lines.append("|---|---|---|---|---|")
    pack = patch.manual_input_pack
    if pack:
        for t in pack.templates:
            warn_str = "; ".join(t.warnings) if t.warnings else "none"
            valid_str = "yes" if t.forbidden_fields_absent else "FORBIDDEN"
            lines.append(f"| {t.input_type} | {Path(t.path).name} | {t.format} | {valid_str} | {warn_str} |")
    lines.append("")

    # Validation
    lines.append("## 3. Manual Input Validation")
    lines.append("")
    val = patch.manual_input_validation
    if val:
        lines.append(f"- **Total valid:** {val.total_valid}")
        lines.append(f"- **Total invalid:** {val.total_invalid}")
        lines.append(f"- **Forbidden fields:** {val.total_forbidden}")
    lines.append("")

    # Smoke Test
    lines.append("## 4. Smoke Test Result")
    lines.append("")
    lines.append("| Test | Status | Output | Warning |")
    lines.append("|---|---|---|---|")
    smoke = patch.smoke_test_result
    if smoke:
        for t in smoke.tests:
            warn_str = "; ".join(t.warnings[:2]) if t.warnings else "none"
            json_str = "valid" if t.stdout_json_valid else "invalid"
            lines.append(f"| {t.test_id} | {t.status} | {json_str} | {warn_str} |")
    lines.append("")

    # Review Rehearsal
    lines.append("## 5. Human Review Rehearsal")
    lines.append("")
    rr = patch.review_rehearsal_result
    if rr:
        lines.append(f"- **Decision count:** {rr.decision_count}")
        lines.append(f"- **Valid:** {rr.valid_decision_count}")
        lines.append(f"- **Invalid:** {rr.invalid_decision_count}")
        lines.append(f"- **Audit preview:** {rr.audit_log_preview_generated}")
        lines.append(f"- **Override preview:** {rr.override_preview_count}")
    lines.append("")

    # Readiness Delta
    lines.append("## 6. Readiness Delta")
    lines.append("")
    lines.append("| Dimension | Baseline | Patched Preview | Delta | Reason |")
    lines.append("|---|---|---|---|---|")
    if delta:
        for d in delta.dimensions:
            lines.append(f"| {d.get('dimension','')} | {d.get('baseline','')} | {d.get('patched','')} | N/A | {d.get('reason','')} |")
    lines.append("")

    # Remaining Gaps
    lines.append("## 7. Remaining Gaps")
    lines.append("")
    lines.append("| Gap | Severity | Status | Next Action |")
    lines.append("|---|---|---|---|")
    for g in patch.remaining_gaps:
        lines.append(f"| {g.get('gap','')} | {g.get('severity','')} | {g.get('status','')} | {g.get('next_action','')} |")
    lines.append("")

    # Safety Boundary
    lines.append("## 8. Safety Boundary")
    lines.append("")
    lines.append("- **Analysis only:** true")
    lines.append("- **Simulation only:** true")
    lines.append("- **Not betting advice:** true")
    lines.append("- **Real bet execution:** false")
    lines.append("- **Auto betting:** false")
    lines.append("- **Account / wallet access:** false")
    lines.append("")

    # Final Recommendation
    lines.append("## 9. Final Recommendation")
    lines.append("")
    lines.append("* Current patch only improves analysis/simulation operational readiness.")
    lines.append("* Real network sources are still disabled by default.")
    lines.append("* Real-money execution remains false by design.")
    lines.append("* Before first matchday, manually confirm data sources and review workflow.")
    lines.append("* Do not skip Watchdog and Human Review steps.")
    lines.append("")
    return "\n".join(lines)


def validate_no_forbidden_pre_tournament_patch_fields(payload: dict) -> list:
    return _deep_scan_forbidden(payload)


def write_pre_tournament_patch_outputs(patch: PreTournamentPatch, output_dir: Optional[Path]=None) -> dict:
    if output_dir is None:
        output_dir = ROOT / "reports" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {}

    # Main patch JSON
    patch_json_path = output_dir / "pre_tournament_patch.json"
    patch_json_path.write_text(
        json.dumps(render_pre_tournament_patch_json(patch), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")
    paths["patch_json"] = str(patch_json_path)

    # Main patch MD
    patch_md_path = output_dir / "pre_tournament_patch.md"
    patch_md_path.write_text(render_pre_tournament_patch_markdown(patch), encoding="utf-8")
    paths["patch_md"] = str(patch_md_path)

    # Manual input validation report
    if patch.manual_input_validation:
        val_path = output_dir / "manual_input_validation_report.json"
        val_path.write_text(
            json.dumps(_d(patch.manual_input_validation), indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")
        paths["manual_input_validation"] = str(val_path)

    # Smoke test
    if patch.smoke_test_result:
        st_path = output_dir / "pre_tournament_smoke_test.json"
        st_path.write_text(
            json.dumps(_d(patch.smoke_test_result), indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")
        paths["smoke_test"] = str(st_path)

    # Review rehearsal
    if patch.review_rehearsal_result:
        rr_path = output_dir / "review_rehearsal_report.json"
        rr_path.write_text(
            json.dumps(_d(patch.review_rehearsal_result), indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")
        paths["review_rehearsal"] = str(rr_path)

    # Readiness delta
    if patch.readiness_delta:
        rd_path = output_dir / "readiness_delta_report.json"
        rd_path.write_text(
            json.dumps(_d(patch.readiness_delta), indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")
        paths["readiness_delta"] = str(rd_path)

    return paths


# ============================================================
# Runner
# ============================================================

@dataclass
class PreTournamentPatchRunner:
    config_dir: str=""

    def run(self) -> PreTournamentPatch:
        return build_pre_tournament_patch({})


def run_pre_tournament_patch_preview(config_paths: Optional[dict]=None) -> PreTournamentPatch:
    return build_pre_tournament_patch(config_paths or {})
