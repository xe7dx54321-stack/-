"""Market explanation: links team news signals to market expectation changes."""
from dataclasses import dataclass, field


@dataclass
class MarketExplanation:
    team: str = ""
    match_id: str = ""
    news_signal: str = ""
    context_signal: str = ""
    explanation: str = ""
    confidence: float = 0.5


@dataclass
class ExplanationSummary:
    explanations: list = field(default_factory=list)
    market_explanation_count: int = 0
    explained_signal_count: int = 0
    unexplained_signal_count: int = 0
    insufficient_news_count: int = 0
    warnings: list = field(default_factory=list)


def build_market_explanations(news_summary, context_summary, injury_summary, config: dict) -> ExplanationSummary:
    conf_threshold = config.get("explanation", {}).get("confidence_threshold", 0.4)
    summary = ExplanationSummary()
    teams_seen = set()

    for signal in context_summary.signals:
        teams_seen.add(signal.team)
        team_news = [n for n in news_summary.items if n.team == signal.team]
        if not team_news:
            summary.insufficient_news_count += 1
            continue

        parts = []
        # Injury impact
        injuries = [n for n in team_news if n.news_type == "injury"]
        if injuries:
            key_inj = [n for n in injuries if "key" in n.subtype]
            if key_inj:
                parts.append(f"Key player concern: {key_inj[0].title}")
                summary.explained_signal_count += 1
            else:
                parts.append("Minor injury/fitness note")

        # Lineup
        lineups = [n for n in team_news if n.news_type == "lineup"]
        if lineups:
            conf = lineups[0]
            parts.append(f"Lineup: {conf.title} (reliability: {conf.reliability})")
            summary.explained_signal_count += 1

        # Motivation
        mot = [n for n in team_news if n.news_type == "motivation"]
        if mot:
            parts.append(f"Motivation: {mot[0].title}")
            summary.explained_signal_count += 1

        confidence = 0.5
        confirmed = sum(1 for n in team_news if n.reliability == "confirmed")
        if confirmed >= 2: confidence = 0.8
        elif confirmed >= 1: confidence = 0.6
        elif any(n.reliability == "rumor" for n in team_news): confidence = 0.3

        if not parts:
            parts.append("No significant news affecting market expectation")
            summary.unexplained_signal_count += 1
        if confidence < conf_threshold:
            summary.insufficient_news_count += 1

        explanation = MarketExplanation(
            team=signal.team, match_id=signal.match_id,
            news_signal="; ".join(parts), context_signal=signal.context_signal,
            explanation=f"Context: {signal.context_signal}, Pressure: {signal.group_pressure}, Fatigue: {signal.fatigue_level}. " + " | ".join(parts),
            confidence=round(confidence, 2),
        )
        summary.explanations.append(explanation)
        summary.market_explanation_count += 1

    return summary
