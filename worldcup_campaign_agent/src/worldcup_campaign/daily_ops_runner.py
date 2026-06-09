"""Daily Ops Runner - orchestrates the daily pipeline."""
import json, sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'src'))

from worldcup_campaign.daily_ops_core import (
    create_daily_ops_manifest, execute_daily_ops_steps,
    run_pre_watchdog, run_post_watchdog, build_final_daily_package,
    build_operator_checklist, render_daily_ops_markdown, _d
)

ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class DailyOpsRunResult:
    campaign_name: str = 'worldcup_2026_high_odds_campaign'
    current_date: str = ''
    current_bankroll: float = 100.0
    mode: str = 'dry_run'
    overall_status: str = 'UNKNOWN'
    manifest: dict = field(default_factory=dict)
    final_daily_package: dict = field(default_factory=dict)
    operator_checklist: dict = field(default_factory=dict)
    watchdog_pre_data: dict = field(default_factory=dict)
    watchdog_post_data: dict = field(default_factory=dict)
    blocked_from_strategy_upgrade: bool = False
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    generated_at: str = ''
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


class DailyOpsRunner:
    def __init__(self, config_dir: str = None):
        cd = Path(config_dir) if config_dir else ROOT / 'config'
        self.runner_config = json.loads((cd / 'daily_ops_runner_config.json').read_text(encoding='utf-8-sig'))
        self.pipeline_config = json.loads((cd / 'daily_ops_pipeline_config.json').read_text(encoding='utf-8-sig'))
        self.step_policy = json.loads((cd / 'daily_ops_step_policy.json').read_text(encoding='utf-8-sig'))
        self.package_config = json.loads((cd / 'daily_package_config.json').read_text(encoding='utf-8-sig'))
        self.checklist_config = json.loads((cd / 'operator_checklist_daily_ops_config.json').read_text(encoding='utf-8-sig'))

    def run(self, date: str, bankroll: float, mode: str = 'dry_run') -> DailyOpsRunResult:
        result = DailyOpsRunResult(
            current_date=date, current_bankroll=bankroll, mode=mode,
            generated_at=datetime.now().isoformat()
        )

        if mode == 'watchdog_only':
            pre_ok, pre_data = run_pre_watchdog(date, bankroll)
            blocked_up, post_data = run_post_watchdog(date, bankroll)
            result.watchdog_pre_data = pre_data
            result.watchdog_post_data = post_data
            result.blocked_from_strategy_upgrade = blocked_up
            cb = post_data.get('circuit_breaker', {})
            result.overall_status = cb.get('overall_status', 'WARN')
            self._write_outputs(result)
            return result

        # Pre-watchdog
        pre_ok, pre_data = run_pre_watchdog(date, bankroll)
        result.watchdog_pre_data = pre_data
        if not pre_ok and self.runner_config.get('stop_if_pre_watchdog_blocked', True):
            result.overall_status = 'BLOCKED_BY_PRE_WATCHDOG'
            result.errors.append('Pre-watchdog BLOCKED')
            self._write_outputs(result)
            return result

        # Build manifest
        manifest = create_daily_ops_manifest(date, bankroll, self.pipeline_config)
        steps_cfg = self.pipeline_config.get('steps', [])

        if mode == 'dry_run':
            from worldcup_campaign.daily_ops_core import build_daily_ops_step
            for sc in steps_cfg:
                step = build_daily_ops_step(sc, date, bankroll)
                step.status = 'PENDING'
                manifest.steps.append(step)
            from worldcup_campaign.daily_ops_core import summarize_manifest
            summarize_manifest(manifest)
            result.manifest = _d(manifest)
            result.overall_status = 'DRY_RUN'
        else:
            exec_result = execute_daily_ops_steps(
                manifest, self.runner_config, self.step_policy, steps_cfg, pre_ok, False
            )
            result.manifest = exec_result.manifest
            result.errors.extend(exec_result.errors)
            result.warnings.extend(exec_result.warnings)
            result.overall_status = exec_result.overall_status

        # Post-watchdog
        blocked_up, post_data = run_post_watchdog(date, bankroll)
        result.watchdog_post_data = post_data
        result.blocked_from_strategy_upgrade = blocked_up

        # Final package
        if self.runner_config.get('generate_final_package', True):
            FakeExecResult = type('FakeExecResult', (), {
                'blocked_from_strategy_upgrade': blocked_up,
                'pipeline_blocked': result.overall_status == 'BLOCKED',
                'watchdog_post_passed': True
            })
            pkg = build_final_daily_package(date, bankroll, manifest, FakeExecResult(),
                                             self.package_config, post_data)
            result.final_daily_package = _d(pkg)

        # Operator checklist
        result.operator_checklist = build_operator_checklist(post_data, manifest, self.checklist_config)
        self._write_outputs(result)
        return result

    def _write_outputs(self, result: DailyOpsRunResult):
        rp = ROOT / 'reports' / 'generated'
        rp.mkdir(parents=True, exist_ok=True)
        output = _d(result)
        (rp / 'daily_ops_run.json').write_text(
            json.dumps(output, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
        (rp / 'daily_ops_run.md').write_text(render_daily_ops_markdown(output), encoding='utf-8')
        (rp / 'daily_ops_manifest.json').write_text(
            json.dumps(result.manifest, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
        (rp / 'final_daily_package.json').write_text(
            json.dumps(result.final_daily_package, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
        (rp / 'final_daily_package.md').write_text(self._render_pkg_md(result), encoding='utf-8')
        (rp / 'operator_checklist.json').write_text(
            json.dumps(result.operator_checklist, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
        (rp / 'operator_checklist.md').write_text(self._render_checklist_md(result), encoding='utf-8')

    def _render_pkg_md(self, r) -> str:
        pkg = r.final_daily_package
        pkg_type = pkg.get('package_type', '?')
        lines = [
            '# Final Daily Package', '',
            f'**Date:** {r.current_date} | **Type:** {pkg_type}', '',
            f'- Blocked from strategy upgrade: {r.blocked_from_strategy_upgrade}', '',
            '## Operator Next Steps', '',
        ]
        for s in pkg.get('operator_next_steps', []):
            lines.append(f'- {s}')
        lines.extend([
            '', '## Safety', '',
            '- Analysis only: True', '- Not betting advice: True', '',
            '---', '*Not betting advice. Analysis package only.*'
        ])
        return '\n'.join(lines)

    def _render_checklist_md(self, r) -> str:
        cl = r.operator_checklist
        lines = ['# Operator Checklist', '', f'**Date:** {r.current_date}', '']
        for item in cl.get('items', []):
            status = item.get('status', '')
            item_id = item.get('item_id', '')
            detail = item.get('detail', '')
            lines.append(f'- [{status}] {item_id}: {detail}')
        lines.append('')
        lines.append('## Forbidden Actions')
        lines.append('')
        for a in cl.get('forbidden_actions', []):
            lines.append(f'- {a}')
        lines.extend(['', '---', '*Operator checklist. Not betting advice.*'])
        return '\n'.join(lines)
