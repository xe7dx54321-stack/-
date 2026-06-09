"""Real Data Runner + Renderer."""
import json, sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'src'))
from worldcup_campaign.real_data_adapter import (
    check_source_policy, scan_for_forbidden, FORBIDDEN,
    load_match_results_json, load_match_results_csv, normalize_match_results,
    load_group_table_results, load_knockout_results,
    load_real_odds_snapshot_json, load_real_odds_snapshot_csv,
    match_ledger_to_results, AutoSettlementPreview, _d
)

ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class RealDataPreview:
    campaign_name: str = 'worldcup_2026_high_odds_campaign'
    current_date: str = ''; current_bankroll: float = 100.0
    source_policy_status: dict = field(default_factory=dict)
    match_results: dict = field(default_factory=dict)
    group_table: dict = field(default_factory=dict)
    knockout_results: dict = field(default_factory=dict)
    odds_snapshots: dict = field(default_factory=dict)
    auto_settlement: dict = field(default_factory=dict)
    manual_review_queue: list = field(default_factory=list)
    safety: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    generated_at: str = ''
    analysis_only: bool = True; simulation_only: bool = True; not_betting_advice: bool = True


class RealDataRunner:
    def __init__(self, config_dir: str = None):
        cd = Path(config_dir) if config_dir else ROOT / 'config'
        self.policy = json.loads((cd / 'real_data_source_policy.json').read_text(encoding='utf-8-sig'))
        self.result_cfg = json.loads((cd / 'match_result_config.json').read_text(encoding='utf-8-sig'))
        self.settlement_cfg = json.loads((cd / 'auto_settlement_match_config.json').read_text(encoding='utf-8-sig'))
        self.odds_policy = json.loads((cd / 'real_odds_snapshot_policy.json').read_text(encoding='utf-8-sig'))

    def run(self, date: str, bankroll: float, match_results_path: str = None,
            group_table_path: str = None, knockout_path: str = None,
            odds_snapshot_path: str = None, odds_snapshot_csv: str = None) -> RealDataPreview:
        preview = RealDataPreview(current_date=date, current_bankroll=bankroll,
                                   generated_at=datetime.now().isoformat())
        # Source policy check
        sp = check_source_policy(self.policy)
        preview.source_policy_status = _d(sp)
        if not sp.all_clear:
            preview.warnings.extend(sp.warnings)

        sd = ROOT / 'data' / 'seed'
        rp = ROOT / 'reports' / 'generated'

        # Match results
        mr_path = match_results_path or str(sd / 'match_results_seed.json')
        try:
            if mr_path.endswith('.csv'):
                raw = load_match_results_csv(mr_path, self.policy)
            else:
                raw = load_match_results_json(mr_path, self.policy)
            normalized = normalize_match_results(raw, self.result_cfg)
            preview.match_results = {'count': len(normalized), 'results': _d(normalized)}
        except Exception as e:
            preview.warnings.append(f'match_results_load_error: {e}')
            preview.match_results = {'count': 0, 'error': str(e)}

        # Group table
        gt_path = group_table_path or str(sd / 'group_table_results_seed.json')
        try:
            preview.group_table = load_group_table_results(gt_path, self.policy)
        except Exception as e:
            preview.warnings.append(f'group_table_load_error: {e}')

        # Knockout
        ko_path = knockout_path or str(sd / 'knockout_results_seed.json')
        try:
            preview.knockout_results = load_knockout_results(ko_path, self.policy)
        except Exception as e:
            preview.warnings.append(f'knockout_load_error: {e}')

        # Odds snapshots
        os_path = odds_snapshot_path or str(sd / 'real_odds_snapshot_seed.json')
        os_csv = odds_snapshot_csv or str(sd / 'real_odds_snapshot_seed.csv')
        try:
            snaps = load_real_odds_snapshot_json(os_path, self.odds_policy)
            preview.odds_snapshots = {'count': len(snaps), 'snapshots': _d(snaps)}
        except Exception:
            try:
                snaps = load_real_odds_snapshot_csv(os_csv, self.odds_policy)
                preview.odds_snapshots = {'count': len(snaps), 'snapshots': _d(snaps)}
            except Exception as e:
                preview.warnings.append(f'odds_snapshot_load_error: {e}')

        # Auto settlement
        ledger_path = rp / 'simulation_ledger.json'
        if ledger_path.exists():
            try:
                ledger = json.loads(ledger_path.read_text(encoding='utf-8'))
                settlement = match_ledger_to_results(
                    ledger, normalized if 'normalized' in dir() else [], preview.group_table or {},
                    preview.knockout_results or {}, self.settlement_cfg
                )
                preview.auto_settlement = _d(settlement)
                for m in settlement.matches:
                    if m.requires_review:
                        preview.manual_review_queue.append({
                            'ledger_entry_id': m.ledger_entry_id, 'reason': m.review_reason,
                            'market_type': m.market_type
                        })
            except Exception as e:
                preview.warnings.append(f'auto_settlement_error: {e}')

        # Self-check: no forbidden fields
        output = _d(preview)
        ff = scan_for_forbidden(output, FORBIDDEN)
        if ff: preview.warnings.append(f'Self-check forbidden fields: {ff}')

        preview.safety = {'campaign_analysis_only':True,'real_bet_execution':False,'auto_betting':False,
                           'network_fetch_default_enabled':False,'analysis_only':True,'simulation_only':True,'not_betting_advice':True}

        # Write reports
        rp.mkdir(parents=True, exist_ok=True)
        (rp / 'real_data_preview.json').write_text(json.dumps(output, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
        (rp / 'real_data_preview.md').write_text(self._render_md(preview), encoding='utf-8')
        if preview.auto_settlement:
            (rp / 'auto_settlement_preview.json').write_text(json.dumps(preview.auto_settlement, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
        if preview.manual_review_queue:
            (rp / 'manual_settlement_review_queue.json').write_text(json.dumps(preview.manual_review_queue, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
        return preview

    def _render_md(self, p) -> str:
        lines = ['# Real Data Preview', '', f'**Date:** {p.current_date}', '',
                  '## Source Policy', f'- Network enabled: {p.source_policy_status.get("network_enabled")}',
                  f'- All clear: {p.source_policy_status.get("all_clear")}', '',
                  '## Match Results', f'- Count: {p.match_results.get("count",0)}', '',
                  '## Auto Settlement', '']
        s = p.auto_settlement
        if s:
            lines.append(f'- Ledger entries: {s.get("ledger_entry_count",0)}')
            lines.append(f'- Auto settled: {s.get("auto_settled_count",0)}')
            lines.append(f'- Manual review: {s.get("manual_review_count",0)}')
            lines.append(f'- Hit/Miss/Push: {s.get("hit_count",0)}/{s.get("miss_count",0)}/{s.get("push_count",0)}')
        lines.extend(['', '## Safety', '- Analysis only: True', '- Not betting advice: True',
                        '', '---', '*Real data analysis. Not betting advice.*'])
        return '\n'.join(lines)
