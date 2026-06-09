"""Real Data Adapter: source policy, result loader, normalizers, odds importer, settlement engine."""
import json, csv
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent
FORBIDDEN = ['stake','stake_amount','stake_to_match','bet_instruction','bet_slip','bookmaker_account','account_balance','real_money_balance','wallet_address','private_key','api_secret','signed_order','submit_order','cancel_order','real_bet_execution']

def _d(obj):
    if hasattr(obj,'__dataclass_fields__'): return {k:_d(v) for k,v in asdict(obj).items()}
    if isinstance(obj,list): return [_d(i) for i in obj]
    return obj

# ===== Source Policy =====
@dataclass
class SourcePolicyCheck:
    network_enabled: bool = False; login_allowed: bool = False
    wallet_allowed: bool = False; bookmaker_allowed: bool = False
    forbidden_fields_found: list = field(default_factory=list)
    all_clear: bool = True; warnings: list = field(default_factory=list)

def check_source_policy(config: dict) -> SourcePolicyCheck:
    c = SourcePolicyCheck(
        network_enabled=config.get('network_fetch_default_enabled',False),
        login_allowed=config.get('login_required_source_allowed',False),
        wallet_allowed=config.get('wallet_connection_allowed',False),
        bookmaker_allowed=config.get('bookmaker_account_access_allowed',False),
    )
    if c.login_allowed: c.all_clear=False; c.warnings.append('login_allowed_violation')
    if c.wallet_allowed: c.all_clear=False; c.warnings.append('wallet_allowed_violation')
    if c.bookmaker_allowed: c.all_clear=False; c.warnings.append('bookmaker_allowed_violation')
    return c

def scan_for_forbidden(data: dict, fields: list) -> list:
    findings=[]
    def _scan(obj,path=''):
        if isinstance(obj,dict):
            for k,v in obj.items():
                if k in fields: findings.append(f'{path}.{k}')
                _scan(v,f'{path}.{k}' if path else k)
        elif isinstance(obj,list):
            for i,item in enumerate(obj): _scan(item,f'{path}[{i}]')
    _scan(data)
    return findings

# ===== Match Result Loader =====
@dataclass
class RawMatchResult:
    match_id: str=''; date: str=''; stage: str=''
    home_team_id: str=''; away_team_id: str=''
    home_score_90: int=0; away_score_90: int=0
    home_score_extra: int=0; away_score_extra: int=0
    home_penalties: int=0; away_penalties: int=0
    result_status: str='unknown'; raw: dict=field(default_factory=dict)

def load_match_results_json(path: str, policy: dict) -> list:
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    ff = scan_for_forbidden(data, FORBIDDEN)
    if ff: raise ValueError(f'Forbidden fields: {ff}')
    results = data.get('results', data.get('matches', []))
    return [_parse_raw_result(r) for r in results]

def load_match_results_csv(path: str, policy: dict) -> list:
    results = []
    with open(path,'r',encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(RawMatchResult(
                match_id=row.get('match_id',''), date=row.get('date',''),
                stage=row.get('stage',''), home_team_id=row.get('home_team_id',''),
                away_team_id=row.get('away_team_id',''),
                home_score_90=int(row.get('home_score_90',0)), away_score_90=int(row.get('away_score_90',0)),
                result_status=row.get('result_status','unknown'), raw=dict(row)
            ))
    return results

def _parse_raw_result(r: dict) -> RawMatchResult:
    return RawMatchResult(
        match_id=r.get('match_id',''), date=r.get('date',''), stage=r.get('stage',''),
        home_team_id=r.get('home_team_id',''), away_team_id=r.get('away_team_id',''),
        home_score_90=int(r.get('home_score_90',0)), away_score_90=int(r.get('away_score_90',0)),
        home_score_extra=int(r.get('home_score_extra',0)), away_score_extra=int(r.get('away_score_extra',0)),
        home_penalties=int(r.get('home_penalties',0)), away_penalties=int(r.get('away_penalties',0)),
        result_status=r.get('result_status','unknown'), raw=r
    )

def load_group_table_results(path: str, policy: dict) -> dict:
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    ff = scan_for_forbidden(data, FORBIDDEN)
    if ff: raise ValueError(f'Forbidden fields: {ff}')
    return data.get('groups', data)

def load_knockout_results(path: str, policy: dict) -> dict:
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    return data.get('rounds', data)

# ===== Match Result Normalizer =====
@dataclass
class NormalizedMatchResult:
    match_id: str=''; date: str=''; stage: str=''
    home_team_id: str=''; away_team_id: str=''
    home_score_90: int=0; away_score_90: int=0
    home_score_extra: int=0; away_score_extra: int=0
    home_penalties: int=0; away_penalties: int=0
    result_status: str='unknown'
    winner_90: str=''; winner_after_penalties: str=''; qualified_team: str=''
    normalization_status: str='ok'; confidence: float=1.0
    warnings: list=field(default_factory=list)

def normalize_match_results(raw_results: list, config: dict) -> list:
    normalized = []
    for r in raw_results:
        n = NormalizedMatchResult(
            match_id=r.match_id, date=r.date, stage=r.stage,
            home_team_id=r.home_team_id, away_team_id=r.away_team_id,
            home_score_90=r.home_score_90, away_score_90=r.away_score_90,
            home_score_extra=r.home_score_extra, away_score_extra=r.away_score_extra,
            home_penalties=r.home_penalties, away_penalties=r.away_penalties,
            result_status=r.result_status,
        )
        if r.result_status == 'completed':
            if r.home_score_90 > r.away_score_90: n.winner_90 = 'home'
            elif r.away_score_90 > r.home_score_90: n.winner_90 = 'away'
            else: n.winner_90 = 'draw'
            if n.home_penalties > n.away_penalties: n.winner_after_penalties = 'home'
            elif n.away_penalties > n.home_penalties: n.winner_after_penalties = 'away'
        elif r.result_status in ('unknown',''):
            n.normalization_status='review'; n.confidence=0.3; n.warnings.append('unknown_status')
        normalized.append(n)
    return normalized

# ===== Odds Snapshot Importer =====
@dataclass
class RealOddsSnapshot:
    snapshot_id: str=''; source_provider: str=''; snapshot_type: str=''
    timestamp: str=''; match_id: str=''; market_type: str=''
    selection_id: str=''; selection_label: str=''; decimal_odds: float=1.0

def load_real_odds_snapshot_json(path: str, policy: dict) -> list:
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    ff = scan_for_forbidden(data, FORBIDDEN)
    if ff: raise ValueError(f'Forbidden fields: {ff}')
    snaps = data.get('snapshots', data if isinstance(data,list) else [])
    return [_parse_odds_snapshot(s) for s in snaps]

def load_real_odds_snapshot_csv(path: str, policy: dict) -> list:
    snaps=[]
    with open(path,'r',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            snaps.append(RealOddsSnapshot(
                snapshot_id=row.get('snapshot_id',''), source_provider=row.get('source_provider',''),
                snapshot_type=row.get('snapshot_type',''), timestamp=row.get('timestamp',''),
                match_id=row.get('match_id',''), market_type=row.get('market_type',''),
                selection_id=row.get('selection_id',''), selection_label=row.get('selection_label',''),
                decimal_odds=float(row.get('decimal_odds',1.0))
            ))
    return snaps

def _parse_odds_snapshot(s: dict) -> RealOddsSnapshot:
    return RealOddsSnapshot(
        snapshot_id=s.get('snapshot_id',''), source_provider=s.get('source_provider',''),
        snapshot_type=s.get('snapshot_type',''), timestamp=s.get('timestamp',''),
        match_id=s.get('match_id',''), market_type=s.get('market_type',''),
        selection_id=s.get('selection_id',''), selection_label=s.get('selection_label',''),
        decimal_odds=float(s.get('decimal_odds',1.0))
    )

# ===== Settlement Market Rules =====
@dataclass
class SettlementRuleResult:
    candidate_id: str=''; market_type: str=''
    outcome_status: str='pending'; confidence: float=1.0
    rule_used: str=''; reason: str=''
    requires_review: bool=False; warnings: list=field(default_factory=list)

def settle_1x2(candidate: dict, match_result: NormalizedMatchResult) -> SettlementRuleResult:
    cid = candidate.get('candidate_id','')
    sid = candidate.get('selection_id','')
    if match_result.result_status != 'completed':
        return SettlementRuleResult(candidate_id=cid, market_type='1x2', outcome_status='pending',
                                    reason='match_not_completed', requires_review=True)
    outcome = 'miss'
    if sid == 'home' and match_result.winner_90 == 'home': outcome = 'hit'
    elif sid == 'draw' and match_result.winner_90 == 'draw': outcome = 'hit'
    elif sid == 'away' and match_result.winner_90 == 'away': outcome = 'hit'
    return SettlementRuleResult(candidate_id=cid, market_type='1x2', outcome_status=outcome,
                                 rule_used='1x2_90min', reason=f'winner_90={match_result.winner_90}')

def settle_over_under(candidate: dict, match_result: NormalizedMatchResult) -> SettlementRuleResult:
    cid = candidate.get('candidate_id','')
    mt = candidate.get('market_type','over_under_2.5')
    if match_result.result_status != 'completed':
        return SettlementRuleResult(candidate_id=cid, market_type=mt, outcome_status='pending',
                                    reason='match_not_completed', requires_review=True)
    total_goals = match_result.home_score_90 + match_result.away_score_90
    line = float(mt.replace('over_under_',''))
    sid = candidate.get('selection_id','')
    outcome = 'miss'
    if sid == 'over' and total_goals > line: outcome = 'hit'
    elif sid == 'under' and total_goals < line: outcome = 'hit'
    elif total_goals == line: outcome = 'push'
    return SettlementRuleResult(candidate_id=cid, market_type=mt, outcome_status=outcome,
                                 rule_used='over_under_90min', reason=f'total_goals={total_goals} line={line}')

def settle_correct_score(candidate: dict, match_result: NormalizedMatchResult) -> SettlementRuleResult:
    cid = candidate.get('candidate_id','')
    if match_result.result_status != 'completed':
        return SettlementRuleResult(candidate_id=cid, market_type='correct_score', outcome_status='pending',
                                    reason='match_not_completed', requires_review=True)
    actual = f'{match_result.home_score_90}-{match_result.away_score_90}'
    predicted = candidate.get('selection_id','')
    outcome = 'hit' if actual == predicted else 'miss'
    return SettlementRuleResult(candidate_id=cid, market_type='correct_score', outcome_status=outcome,
                                 rule_used='correct_score_90min', reason=f'actual={actual} predicted={predicted}')

def settle_futures(candidate: dict, group_tables: dict, knockout_results: dict) -> SettlementRuleResult:
    cid = candidate.get('candidate_id','')
    return SettlementRuleResult(candidate_id=cid, market_type=candidate.get('market_type',''),
                                 outcome_status='pending', reason='futures_not_settled_yet',
                                 requires_review=False, confidence=0.3)

# ===== Auto Settlement Matcher =====
@dataclass
class AutoSettlementMatch:
    ledger_entry_id: str=''; candidate_id: str=''; match_id: str=''
    market_type: str=''; selection_id: str=''
    auto_outcome_status: str='pending'; confidence: float=0.0
    requires_review: bool=False; review_reason: str=''
    matched_result: dict=field(default_factory=dict)

@dataclass
class AutoSettlementPreview:
    ledger_entry_count: int=0; matched_count: int=0
    auto_settled_count: int=0; manual_review_count: int=0; pending_count: int=0
    hit_count: int=0; miss_count: int=0; push_count: int=0
    void_count: int=0; unknown_count: int=0
    matches: list=field(default_factory=list)
    warnings: list=field(default_factory=list)

def match_ledger_to_results(simulation_ledger: dict, normalized_results: list,
                             group_tables: dict, knockout_results: dict, config: dict) -> AutoSettlementPreview:
    preview = AutoSettlementPreview()
    entries = simulation_ledger.get('ledger', simulation_ledger.get('entries', []))
    if isinstance(entries, dict):
        entries = list(entries.values()) if not isinstance(entries, list) else entries
    if not isinstance(entries, list): entries = []
    preview.ledger_entry_count = len(entries)
    result_map = {r.match_id: r for r in normalized_results}
    for entry in entries:
        eid = entry.get('entry_id', entry.get('candidate_id',''))
        mid = entry.get('match_id','')
        mt = entry.get('market_type','')
        sid = entry.get('selection_id','')
        m = AutoSettlementMatch(ledger_entry_id=eid, candidate_id=eid, match_id=mid, market_type=mt, selection_id=sid)
        mr = result_map.get(mid)
        if not mr:
            m.requires_review=True; m.review_reason='no_result_found'
            preview.manual_review_count+=1; preview.matches.append(m); continue
        m.matched_result = _d(mr)
        preview.matched_count+=1
        if mt == '1x2':
            r = settle_1x2(entry, mr)
        elif 'over_under' in mt:
            r = settle_over_under(entry, mr)
        elif mt == 'correct_score':
            r = settle_correct_score(entry, mr)
        elif mt in ('winner','group_qualification','group_winner','reach_final'):
            r = settle_futures(entry, group_tables, knockout_results)
        else:
            r = SettlementRuleResult(outcome_status='pending', reason='unsupported_market', requires_review=True)
        m.auto_outcome_status = r.outcome_status
        m.confidence = r.confidence
        m.requires_review = r.requires_review
        m.review_reason = r.reason
        if r.requires_review: preview.manual_review_count+=1
        elif r.outcome_status == 'pending': preview.pending_count+=1
        else: preview.auto_settled_count+=1
        if r.outcome_status == 'hit': preview.hit_count+=1
        elif r.outcome_status == 'miss': preview.miss_count+=1
        elif r.outcome_status == 'push': preview.push_count+=1
        elif r.outcome_status == 'void': preview.void_count+=1
        else: preview.unknown_count+=1
        preview.matches.append(m)
    return preview
