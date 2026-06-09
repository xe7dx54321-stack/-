"""Injury/lineup analyzer: analyzes injury, suspension, and lineup availability."""
from dataclasses import dataclass, field


@dataclass
class InjuryRecord:
    team: str = ""
    match_id: str = ""
    player_note: str = ""
    injury_type: str = ""
    is_key_absence: bool = False
    impact_score: float = 0.0


@dataclass
class LineupRecord:
    team: str = ""
    match_id: str = ""
    lineup_status: str = ""
    confidence: float = 0.5
    notes: str = ""


@dataclass
class InjuryLineupSummary:
    injuries: list = field(default_factory=list)
    suspensions: list = field(default_factory=list)
    lineups: list = field(default_factory=list)
    injury_count: int = 0
    suspension_count: int = 0
    key_absence_count: int = 0
    lineup_count: int = 0
    confirmed_lineup_count: int = 0
    predicted_lineup_count: int = 0
    warnings: list = field(default_factory=list)


def analyze_injuries_and_lineups(news_summary, config: dict) -> InjuryLineupSummary:
    key_threshold = config.get("injury_impact", {}).get("key_player_absence_threshold", 0.7)
    summary = InjuryLineupSummary()

    for item in news_summary.items:
        ntype = item.news_type
        subtype = item.subtype

        if ntype == "injury":
            is_key = "key_player" in subtype
            is_susp = subtype == "suspension"
            impact = 0.8 if is_key else (0.5 if "minor" in subtype else 0.6)
            record = InjuryRecord(
                team=item.team, match_id=item.match_id,
                player_note=item.title, injury_type=subtype,
                is_key_absence=is_key, impact_score=impact,
            )
            if is_susp:
                summary.suspensions.append(record)
                summary.suspension_count += 1
            else:
                summary.injuries.append(record)
                summary.injury_count += 1
            if is_key:
                summary.key_absence_count += 1

        elif ntype == "lineup":
            is_confirmed = subtype == "confirmed"
            conf = 1.0 if is_confirmed else 0.5
            record = LineupRecord(
                team=item.team, match_id=item.match_id,
                lineup_status="confirmed" if is_confirmed else "predicted",
                confidence=conf, notes=item.title,
            )
            summary.lineups.append(record)
            summary.lineup_count += 1
            if is_confirmed:
                summary.confirmed_lineup_count += 1
            else:
                summary.predicted_lineup_count += 1

    if summary.key_absence_count > 0:
        summary.warnings.append(f"{summary.key_absence_count} key player absences detected; may significantly impact match odds.")
    return summary
