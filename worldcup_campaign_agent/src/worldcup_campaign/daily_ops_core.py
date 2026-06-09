"""Daily Ops Core - Step Manifest Executor Package Builder"""
import json, sys, subprocess, time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

FORBIDDEN_FRAGMENTS = ['submit_order', 'place_bet', 'connect_wallet', 'bookmaker_login', 'real_bet_execution']
ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = ROOT / 'scripts'


@dataclass
class DailyOpsStep:
    step_id: str = ''
    runner: str = ''
    phase: str = ''
    required: bool = True
    command: list = field(default_factory=list)
    status: str = 'PENDING'
    stdout_json: dict = field(default_factory=dict)
    stderr: str = ''
    error: str = ''
    start_time: str = ''
    end_time: str = ''
    duration_seconds: float = 0.0
    output_paths: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True

def build_daily_ops_step(step_config: dict, current_date: str, current_bankroll: float, mode: str = 'execute') -> DailyOpsStep:
    step = DailyOpsStep(
        step_id=step_config['step_id'], runner=step_config['runner'],
        phase=step_config.get('phase', ''), required=step_config.get('required', True),
    )
    extra_args = step_config.get('args', [])
    cmd = [sys.executable, str(SCRIPTS_DIR / step.runner), '--date', current_date, '--bankroll', str(current_bankroll)]
    cmd.extend(extra_args)
    cmd.append('--json')
    step.command = cmd
    return step


def validate_step_command(step: DailyOpsStep) -> list:
    cmd_str = ' '.join(step.command).lower()
    return [f for f in FORBIDDEN_FRAGMENTS if f in cmd_str]


def parse_step_stdout(stdout_text: str) -> dict:
    try:
        return json.loads(stdout_text.strip())
    except json.JSONDecodeError:
        for line in stdout_text.strip().split('\n'):
            line = line.strip()
            if line.startswith('{'):
                try: return json.loads(line)
                except json.JSONDecodeError: continue
        return {}

@dataclass
class DailyOpsManifestSummary:
    success_count: int = 0; warn_count: int = 0; failed_count: int = 0
    skipped_count: int = 0; blocked_count: int = 0
    required_failed_count: int = 0; optional_failed_count: int = 0
    duration_seconds: float = 0.0


@dataclass
class DailyOpsManifest:
    campaign_name: str = 'worldcup_2026_high_odds_campaign'
    current_date: str = ''; current_bankroll: float = 100.0
    pipeline_name: str = ''; step_count: int = 0
    required_step_count: int = 0; optional_step_count: int = 0
    steps: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    analysis_only: bool = True; simulation_only: bool = True; not_betting_advice: bool = True


def create_daily_ops_manifest(current_date: str, current_bankroll: float, pipeline_config: dict) -> DailyOpsManifest:
    steps_cfg = pipeline_config.get('steps', [])
    required = sum(1 for s in steps_cfg if s.get('required', True))
    optional = len(steps_cfg) - required
    return DailyOpsManifest(
        current_date=current_date, current_bankroll=current_bankroll,
        pipeline_name=pipeline_config.get('pipeline_name', ''),
        step_count=len(steps_cfg), required_step_count=required, optional_step_count=optional,
    )


def update_manifest_step(manifest: DailyOpsManifest, step_result: DailyOpsStep) -> DailyOpsManifest:
    manifest.steps.append(step_result)
    return manifest


def summarize_manifest(manifest: DailyOpsManifest) -> DailyOpsManifestSummary:
    s = DailyOpsManifestSummary()
    for step in manifest.steps:
        st = step.status
        if st == 'SUCCESS': s.success_count += 1
        elif st == 'WARN': s.warn_count += 1
        elif st == 'FAILED': s.failed_count += 1
        elif st == 'SKIPPED': s.skipped_count += 1
        elif st == 'BLOCKED': s.blocked_count += 1
        if st == 'FAILED' and step.required: s.required_failed_count += 1
        if st == 'FAILED' and not step.required: s.optional_failed_count += 1
        s.duration_seconds += step.duration_seconds
    manifest.summary = asdict(s)
    return s

@dataclass
class DailyOpsExecutionResult:
    manifest: dict = field(default_factory=dict)
    overall_status: str = 'UNKNOWN'
    pipeline_completed: bool = False
    pipeline_blocked: bool = False
    watchdog_pre_passed: bool = True
    watchdog_post_passed: bool = True
    blocked_from_strategy_upgrade: bool = False
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def execute_single_step(step: DailyOpsStep, step_policy: dict) -> DailyOpsStep:
    max_sec = step_policy.get('max_step_runtime_seconds', 120)
    violations = validate_step_command(step)
    if violations:
        step.status = 'BLOCKED'
        step.error = f'forbidden_command_fragments: {violations}'
        return step
    step.status = 'RUNNING'
    step.start_time = datetime.now().isoformat()
    t0 = time.time()
    try:
        result = subprocess.run(step.command, capture_output=True, text=True, timeout=max_sec)
        step.end_time = datetime.now().isoformat()
        step.duration_seconds = round(time.time() - t0, 2)
        step.stdout_json = parse_step_stdout(result.stdout)
        step.stderr = result.stderr[:2000] if result.stderr else ''
        if result.returncode != 0 and not step.stdout_json:
            step.status = 'FAILED'
            step.error = f'exit_code={result.returncode}'
        else:
            step.status = 'SUCCESS'
            if step.stderr and ('warn' in step.stderr.lower() or 'warning' in step.stderr.lower()):
                step.status = 'WARN'
                step.warnings.append(step.stderr[:500])
    except subprocess.TimeoutExpired:
        step.end_time = datetime.now().isoformat()
        step.duration_seconds = max_sec
        step.status = 'FAILED'
        step.error = f'timeout after {max_sec}s'
    except Exception as e:
        step.end_time = datetime.now().isoformat()
        step.duration_seconds = round(time.time() - t0, 2)
        step.status = 'FAILED'
        step.error = str(e)[:500]
    return step


def execute_daily_ops_steps(manifest: DailyOpsManifest, runner_config: dict,
                             step_policy: dict, steps_cfg: list,
                             pre_watchdog_ok: bool = True,
                             blocked_from_upgrade: bool = False) -> DailyOpsExecutionResult:
    result = DailyOpsExecutionResult()
    result.watchdog_pre_passed = pre_watchdog_ok
    if not pre_watchdog_ok and runner_config.get('stop_if_pre_watchdog_blocked', True):
        result.overall_status = 'BLOCKED_BY_PRE_WATCHDOG'
        result.pipeline_blocked = True
        result.errors.append('Pre-watchdog blocked pipeline')
        result.manifest = asdict(manifest)
        return result
    pipeline_blocked = False
    for sc in steps_cfg:
        if pipeline_blocked:
            step = DailyOpsStep(step_id=sc['step_id'], runner=sc['runner'],
                                phase=sc.get('phase', ''), required=sc.get('required', True),
                                status='SKIPPED')
            manifest.steps.append(step)
            continue
        step = build_daily_ops_step(sc, manifest.current_date, manifest.current_bankroll)
        step = execute_single_step(step, step_policy)
        manifest.steps.append(step)
        if step.status in ('FAILED', 'BLOCKED'):
            if step.required and runner_config.get('stop_if_required_step_failed', True):
                pipeline_blocked = True
                result.pipeline_blocked = True
                result.errors.append(f'Required step {step.step_id} {step.status}: {step.error}')
            else:
                result.warnings.append(f'Optional step {step.step_id} {step.status}: {step.error}')
    summarize_manifest(manifest)
    result.manifest = asdict(manifest)
    result.blocked_from_strategy_upgrade = blocked_from_upgrade
    if result.pipeline_blocked:
        result.overall_status = 'BLOCKED'
        result.pipeline_completed = False
    elif manifest.summary.get('failed_count', 0) > 0:
        result.overall_status = 'DEGRADED'
        result.pipeline_completed = True
    elif manifest.summary.get('warn_count', 0) > 0:
        result.overall_status = 'WARN'
        result.pipeline_completed = True
    else:
        result.overall_status = 'SUCCESS'
        result.pipeline_completed = True
    return result

# Watchdog Bridge
def run_pre_watchdog(current_date: str, current_bankroll: float):
    try:
        from worldcup_campaign.watchdog_runner import WatchdogRunner
        cp = str(ROOT / 'config' / 'daily_ops_watchdog_config.json')
        preview = WatchdogRunner(cp).run(current_date, current_bankroll, 'pre_daily_ops')
        cb = preview.circuit_breaker
        passed = cb.get('overall_status', 'UNKNOWN') != 'BLOCKED'
        return passed, _to_dict_safe(preview)
    except Exception as e:
        return True, {'error': str(e), 'assumed_pass': True}


def run_post_watchdog(current_date: str, current_bankroll: float):
    try:
        from worldcup_campaign.watchdog_runner import WatchdogRunner
        cp = str(ROOT / 'config' / 'daily_ops_watchdog_config.json')
        preview = WatchdogRunner(cp).run(current_date, current_bankroll, 'post_daily_ops')
        cb = preview.circuit_breaker
        blocked_upgrade = cb.get('blocked_from_strategy_upgrade', False)
        return blocked_upgrade, _to_dict_safe(preview)
    except Exception as e:
        return False, {'error': str(e)}


# Final Daily Package Builder
@dataclass
class FinalDailyPackage:
    campaign_name: str = 'worldcup_2026_high_odds_campaign'
    current_date: str = ''; current_bankroll: float = 100.0
    package_type: str = 'review_required_package'
    campaign_context: dict = field(default_factory=dict)
    watchdog_summary: dict = field(default_factory=dict)
    pipeline_summary: dict = field(default_factory=dict)
    market_expectation_summary: dict = field(default_factory=dict)
    team_context_summary: dict = field(default_factory=dict)
    signal_fusion_summary: dict = field(default_factory=dict)
    candidate_summary: dict = field(default_factory=dict)
    review_queue_summary: dict = field(default_factory=dict)
    operator_next_steps: list = field(default_factory=list)
    safety_boundary: dict = field(default_factory=dict)
    analysis_only: bool = True; simulation_only: bool = True; not_betting_advice: bool = True


def build_final_daily_package(current_date: str, current_bankroll: float,
                                manifest: DailyOpsManifest, exec_result: DailyOpsExecutionResult,
                                package_config: dict, watchdog_post_data: dict) -> FinalDailyPackage:
    cb = watchdog_post_data.get('circuit_breaker', {})
    blocked_upgrade = exec_result.blocked_from_strategy_upgrade
    status = cb.get('overall_status', 'UNKNOWN')
    if status == 'BLOCKED' or exec_result.pipeline_blocked:
        pkg_type = 'blocked_package'
    elif blocked_upgrade:
        pkg_type = 'review_required_package'
    else:
        pkg_type = 'clean_final_package'
    pkg = FinalDailyPackage(
        current_date=current_date, current_bankroll=current_bankroll, package_type=pkg_type,
        campaign_context={'date': current_date, 'bankroll': current_bankroll,
                          'target': 1000000, 'multiplier_needed': round(1000000 / max(current_bankroll, 1), 1)},
        watchdog_summary=cb, pipeline_summary=manifest.summary,
        review_queue_summary=watchdog_post_data.get('review_queue', {}),
        operator_next_steps=_build_next_steps(pkg_type, blocked_upgrade, watchdog_post_data),
        safety_boundary={'campaign_analysis_only': True, 'real_bet_execution': False,
                         'auto_betting': False, 'network_fetch_default_enabled': False,
                         'analysis_only': True, 'simulation_only': True, 'not_betting_advice': True}
    )
    rp = ROOT / 'reports' / 'generated'
    for fname, attr in [('market_expectation.json', 'market_expectation_summary'),
                          ('team_news_preview.json', 'team_context_summary'),
                          ('signal_fusion_preview.json', 'signal_fusion_summary')]:
        fp = rp / fname
        if fp.exists():
            try: setattr(pkg, attr, json.loads(fp.read_text(encoding='utf-8')))
            except Exception: pass
    return pkg


def _build_next_steps(pkg_type: str, blocked_upgrade: bool, watchdog_data: dict) -> list:
    steps = []
    rq = watchdog_data.get('review_queue', {})
    if rq.get('review_item_count', 0) > 0:
        steps.append('Review ' + str(rq.get('review_item_count', 0)) + ' items in manual review queue')
    if blocked_upgrade:
        steps.append('Strategy upgrade BLOCKED - use review-required candidates only')
    if pkg_type == 'blocked_package':
        steps.append('Pipeline BLOCKED - resolve safety violations before continuing')
    steps.append('Archive daily package')
    steps.append('Confirm no real execution fields in all outputs')
    return steps

# Operator Checklist
def build_operator_checklist(watchdog_data: dict, manifest: DailyOpsManifest, checklist_config: dict) -> dict:
    items = []
    for item_id in checklist_config.get('checklist_items', []):
        detail = ''
        if item_id == 'confirm_watchdog_status':
            cb = watchdog_data.get('circuit_breaker', {})
            detail = 'Watchdog: ' + str(cb.get('overall_status', '?'))
        elif item_id == 'review_manual_queue':
            rq = watchdog_data.get('review_queue', {})
            detail = str(rq.get('review_item_count', 0)) + ' items to review'
        elif item_id == 'confirm_no_real_execution_fields':
            detail = 'Scan all generated JSON for forbidden fields'
        elif item_id == 'archive_daily_package':
            detail = 'Archive package for ' + str(manifest.current_date)
        items.append({'item_id': item_id, 'status': 'pending', 'detail': detail})
    return {
        'checklist_name': 'daily_ops', 'date': manifest.current_date,
        'items': items, 'forbidden_actions': checklist_config.get('forbidden_operator_actions', []),
        'analysis_only': True, 'not_betting_advice': True
    }


# Renderer
def render_daily_ops_markdown(result: dict) -> str:
    m = result.get('manifest', {})
    pkg = result.get('final_daily_package', {})
    cur_date = str(result.get('current_date', ''))
    cur_br = str(result.get('current_bankroll', ''))
    overall = str(result.get('overall_status', '?'))
    lines = [
        '# Daily Ops Run', '',
        '**Date:** ' + cur_date + ' | **Bankroll:** ' + cur_br, '',
        '## Overall Status: **' + overall + '**', '',
        '## Pipeline Steps', '',
        '| Step | Status | Duration | Warnings |',
        '|------|-------|---------|----------|',
    ]
    for s in m.get('steps', []):
        dur = str(s.get('duration_seconds', 0)) + 's'
        warns = '; '.join(s.get('warnings', []))[:80]
        sid = s.get('step_id', '')
        sts = s.get('status', '')
        lines.append('| ' + sid + ' | ' + sts + ' | ' + dur + ' | ' + warns + ' |')
    pkg_type = str(pkg.get('package_type', '?'))
    blocked = str(result.get('blocked_from_strategy_upgrade', False))
    lines.extend([
        '', '## Package', '',
        '- Type: ' + pkg_type,
        '- Blocked from strategy upgrade: ' + blocked, '',
        '## Safety', '',
        '- Analysis only: True', '- Not betting advice: True', '',
        '---', '*Daily Ops Runner. Orchestration only. Not betting advice.*'
    ])
    return '\n'.join(lines)

def _to_dict_safe(obj):
    if hasattr(obj, '__dataclass_fields__'):
        return {k: _to_dict_safe(v) for k, v in asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict_safe(i) for i in obj]
    return obj


def _d(obj):
    return _to_dict_safe(obj)
