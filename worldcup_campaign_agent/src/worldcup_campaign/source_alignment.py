"""Source alignment guard: detects mismatches between CLI inputs and generated snapshots."""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SourceAlignmentPolicy:
    check_cli_vs_snapshot: bool = True
    check_date_alignment: bool = True
    check_bankroll_alignment: bool = True
    check_report_freshness: bool = True
    bankroll_mismatch_tolerance: float = 0.01
    date_mismatch_policy: str = "warn"
    bankroll_mismatch_policy: str = "warn"
    missing_source_policy: str = "warn_and_continue"
    stale_source_policy: str = "warn_and_continue"
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


@dataclass
class SourceFreshnessSummary:
    total_sources: int = 0
    available_sources: int = 0
    missing_sources: int = 0
    stale_sources: int = 0
    source_details: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


@dataclass
class SourceAlignmentResult:
    cli_date: str = ""
    cli_bankroll: float = 0.0
    snapshot_date: str = ""
    snapshot_bankroll: float = 0.0
    display_bankroll: float = 0.0
    date_aligned: bool = True
    bankroll_aligned: bool = True
    source_freshness_summary: Optional[SourceFreshnessSummary] = None
    warnings: list = field(default_factory=list)
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


def load_source_alignment_policy(path: str) -> SourceAlignmentPolicy:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return SourceAlignmentPolicy(
        check_cli_vs_snapshot=data.get("check_cli_vs_snapshot", True),
        check_date_alignment=data.get("check_date_alignment", True),
        check_bankroll_alignment=data.get("check_bankroll_alignment", True),
        check_report_freshness=data.get("check_report_freshness", True),
        bankroll_mismatch_tolerance=data.get("bankroll_mismatch_tolerance", 0.01),
        date_mismatch_policy=data.get("date_mismatch_policy", "warn"),
        bankroll_mismatch_policy=data.get("bankroll_mismatch_policy", "warn"),
        missing_source_policy=data.get("missing_source_policy", "warn_and_continue"),
        stale_source_policy=data.get("stale_source_policy", "warn_and_continue"),
        analysis_only=data.get("analysis_only", True),
        simulation_only=data.get("simulation_only", True),
        not_betting_advice=data.get("not_betting_advice", True),
    )


def validate_source_alignment_policy(policy: SourceAlignmentPolicy) -> None:
    if policy.bankroll_mismatch_tolerance < 0:
        raise ValueError("bankroll_mismatch_tolerance must be >= 0")


def check_source_alignment(
    cli_date: str,
    cli_bankroll: float,
    dashboard_sources: dict,
    policy: SourceAlignmentPolicy
) -> SourceAlignmentResult:
    result = SourceAlignmentResult(
        cli_date=cli_date,
        cli_bankroll=cli_bankroll,
        display_bankroll=cli_bankroll,
    )

    # Try to extract snapshot info from available sources
    snapshot_date = ""
    snapshot_bankroll = cli_bankroll

    # Check postmatch settlement for snapshot
    settlement = dashboard_sources.get("postmatch_settlement", {})
    if settlement:
        snapshot_date = settlement.get("date", "")
        snapshot_bankroll = settlement.get("simulated_bankroll_after", cli_bankroll)

    # Check campaign state history
    camp_state = dashboard_sources.get("campaign_state", {})
    if camp_state:
        if isinstance(camp_state, dict) and "snapshots" in camp_state:
            snapshots = camp_state["snapshots"]
            if snapshots:
                latest = snapshots[-1] if isinstance(snapshots, list) else camp_state
                if not snapshot_date:
                    snapshot_date = latest.get("date", "")
                if snapshot_bankroll == cli_bankroll:
                    snapshot_bankroll = latest.get("liquid_simulated_bankroll", latest.get("simulated_bankroll_after", snapshot_bankroll))
        elif isinstance(camp_state, dict) and "date" in camp_state:
            if not snapshot_date:
                snapshot_date = camp_state.get("date", "")
            state_bankroll = camp_state.get("liquid_simulated_bankroll", camp_state.get("simulated_bankroll_after", None))
            if state_bankroll is not None and snapshot_bankroll == cli_bankroll:
                snapshot_bankroll = state_bankroll

    # Check integrated strategy for bankroll
    integrated = dashboard_sources.get("integrated_strategy", {})
    if integrated and snapshot_bankroll == cli_bankroll:
        is_bankroll = integrated.get("current_bankroll", None)
        if is_bankroll is not None:
            snapshot_bankroll = is_bankroll

    result.snapshot_date = snapshot_date
    result.snapshot_bankroll = snapshot_bankroll
    result.display_bankroll = snapshot_bankroll if snapshot_bankroll != cli_bankroll else cli_bankroll

    # Date alignment
    if policy.check_date_alignment and snapshot_date:
        if snapshot_date != cli_date:
            result.date_aligned = False
            if policy.date_mismatch_policy == "warn":
                result.warnings.append(
                    f"CLI date ({cli_date}) differs from snapshot date ({snapshot_date}). "
                    f"Dashboard uses generated snapshot data; "
                    f"rerun relevant modules with --date {snapshot_date} or refresh sources."
                )

    # Bankroll alignment
    if policy.check_bankroll_alignment:
        diff = abs(cli_bankroll - snapshot_bankroll)
        if diff > policy.bankroll_mismatch_tolerance:
            result.bankroll_aligned = False
            if policy.bankroll_mismatch_policy == "warn":
                result.warnings.append(
                    f"CLI bankroll ({cli_bankroll}) differs from snapshot bankroll ({snapshot_bankroll}). "
                    f"Dashboard uses generated snapshot bankroll ({snapshot_bankroll}) as display_bankroll. "
                    f"To use CLI bankroll, re-run modules or refresh sources."
                )

    # Source freshness
    result.source_freshness_summary = summarize_source_freshness(dashboard_sources, policy)

    return result


def summarize_source_freshness(
    dashboard_sources: dict,
    policy: SourceAlignmentPolicy
) -> SourceFreshnessSummary:
    summary = SourceFreshnessSummary()
    source_status = dashboard_sources.get("source_status", {})

    if not source_status:
        for key in ["foundation", "postmatch_settlement", "campaign_schedule", "calendar_preview",
                     "integrated_strategy", "ev_ranking", "parlay_preview", "futures_preview",
                     "match_probability", "campaign_state"]:
            val = dashboard_sources.get(key, None)
            if val and val != {}:
                source_status[key] = "loaded"
            else:
                source_status[key] = "missing"

    summary.total_sources = len(source_status)
    summary.available_sources = sum(1 for v in source_status.values() if v == "loaded")
    summary.missing_sources = sum(1 for v in source_status.values() if v == "missing")
    summary.stale_sources = sum(1 for v in source_status.values() if v == "stale")
    summary.source_details = source_status

    for key, status in source_status.items():
        if status == "missing" and policy.missing_source_policy == "warn_and_continue":
            summary.warnings.append(f"Source '{key}' is missing, continuing without it.")

    return summary


# Alias for backward compatibility with test usage
def load_dashboard_sources_for_alignment(reports_dir: str) -> dict:
    """Simple helper to load dashboard sources for alignment checking."""
    p = Path(reports_dir)
    mapping = {
        "foundation": "foundation_preview.json",
        "postmatch_settlement": "postmatch_settlement.json",
        "campaign_schedule": "campaign_schedule_preview.json",
        "calendar_preview": "calendar_preview.json",
        "integrated_strategy": "integrated_daily_strategy.json",
        "ev_ranking": "ev_ranking_preview.json",
        "parlay_preview": "parlay_preview.json",
        "futures_preview": "futures_preview.json",
        "match_probability": "match_probability_preview.json",
        "campaign_state": "campaign_state_snapshot.json",
    }
    sources = {}
    source_status = {}
    for key, fname in mapping.items():
        fpath = p / fname
        if fpath.exists():
            try:
                sources[key] = json.loads(fpath.read_text(encoding="utf-8"))
                source_status[key] = "loaded"
            except Exception:
                sources[key] = {}
                source_status[key] = "error"
        else:
            sources[key] = {}
            source_status[key] = "missing"
    sources["source_status"] = source_status
    return sources
