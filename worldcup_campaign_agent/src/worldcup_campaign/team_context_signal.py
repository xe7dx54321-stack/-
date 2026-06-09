"""Team context signal: group pressure, fatigue, motivation, rotation risk."""
from dataclasses import dataclass, field


@dataclass
class TeamContextSignal:
    team: str = ""
    match_id: str = ""
    group_pressure: str = "none"
    fatigue_level: str = "low"
    motivation_score: float = 0.5
    rotation_risk: str = "low"
    context_signal: str = "neutral"
    notes: str = ""


@dataclass
class ContextSignalSummary:
    signals: list = field(default_factory=list)
    group_pressure_count: int = 0
    fatigue_signal_count: int = 0
    team_context_signal_count: int = 0
    positive_context_count: int = 0
    negative_context_count: int = 0
    mixed_context_count: int = 0
    insufficient_data_count: int = 0
    warnings: list = field(default_factory=list)


def build_team_context_signals(news_summary, fixture: dict, config: dict) -> ContextSignalSummary:
    summary = ContextSignalSummary()
    teams = fixture.get("teams", {})
    team_news = {}
    for item in news_summary.items:
        if item.team not in team_news:
            team_news[item.team] = []
        team_news[item.team].append(item)

    for team_code, team_data in teams.items():
        match_news = team_news.get(team_code, [])
        match_id = match_news[0].match_id if match_news else ""

        # Group pressure
        pts = team_data.get("group_points", 0); played = team_data.get("matches_played", 0)
        gp = "none"
        if played >= 1 and pts == 0:
            gp = "elimination_risk"
            summary.group_pressure_count += 1
        elif played >= 1 and pts <= 1:
            gp = "moderate"

        # Fatigue
        fatigue = "low"
        fatigue_types = [n for n in match_news if n.news_type in ("injury", "weather")]
        if any("minor" in n.subtype for n in fatigue_types):
            fatigue = "moderate"
            summary.fatigue_signal_count += 1

        # Motivation
        motivation_types = [n for n in match_news if n.news_type == "motivation"]
        mot_score = 0.5
        for mn in motivation_types:
            if "underdog" in mn.subtype or "debut" in mn.subtype or "champion" in mn.subtype:
                mot_score += 0.15
            if "favorite" in mn.subtype:
                mot_score -= 0.05
        if mot_score > 0.7: mot_score = 0.8
        if mot_score < 0.3: mot_score = 0.3

        # Rotation risk
        rotation = "low"
        rumor_types = [n for n in match_news if n.reliability == "rumor"]
        if rumor_types:
            rotation = "moderate"

        # Overall signal
        pos = 0; neg = 0
        if mot_score >= 0.6: pos += 1
        if gp == "elimination_risk": neg += 1
        if fatigue == "moderate": neg += 1
        if rotation == "moderate": neg += 1
        overall = "positive" if pos > neg else ("negative" if neg > pos else "neutral")

        signal = TeamContextSignal(
            team=team_code, match_id=match_id, group_pressure=gp,
            fatigue_level=fatigue, motivation_score=round(mot_score, 2),
            rotation_risk=rotation, context_signal=overall,
            notes=f"Points={pts} Played={played} News={len(match_news)}",
        )
        summary.signals.append(signal)
        summary.team_context_signal_count += 1
        if overall == "positive": summary.positive_context_count += 1
        elif overall == "negative": summary.negative_context_count += 1
        else: summary.mixed_context_count += 1

    return summary
