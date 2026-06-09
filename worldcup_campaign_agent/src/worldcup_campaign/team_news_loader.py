"""Team news loader and normalizer: loads team news from fixture and normalizes."""
import json
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone


@dataclass
class TeamNewsItem:
    news_id: str = ""
    team: str = ""
    match_id: str = ""
    news_type: str = ""
    subtype: str = ""
    title: str = ""
    detail: str = ""
    reliability: str = "reported"
    reliability_score: float = 0.7
    source: str = ""
    timestamp: str = ""
    age_hours: float = 0.0
    is_fresh: bool = True
    is_stale: bool = False


@dataclass
class TeamNewsSummary:
    items: list = field(default_factory=list)
    news_item_count: int = 0
    normalized_news_count: int = 0
    team_count: int = 0
    match_count: int = 0
    reliability_warning_count: int = 0
    freshness_warning_count: int = 0
    warnings: list = field(default_factory=list)


RELIABILITY_SCORES = {"confirmed": 1.0, "reported": 0.7, "predicted": 0.5, "rumor": 0.3}


def load_team_news_fixture(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def normalize_team_news(fixture: dict, config: dict, reference_date: str = None) -> TeamNewsSummary:
    stale_hours = config.get("reliability", {}).get("stale_age_hours", 48)
    summary = TeamNewsSummary()
    teams_seen = set(); matches_seen = set()

    if reference_date:
        ref_dt = datetime.fromisoformat(reference_date).replace(tzinfo=None)
    else:
        ref_dt = datetime.now(timezone.utc).replace(tzinfo=None)

    for item in fixture.get("news_items", []):
        reliab = item.get("reliability", "reported")
        score = RELIABILITY_SCORES.get(reliab, 0.5)
        ts = item.get("timestamp", "")
        age = 0; is_fresh = True; is_stale = False
        if ts:
            try:
                item_dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
                age = (ref_dt - item_dt).total_seconds() / 3600.0
                is_stale = age > stale_hours
                is_fresh = not is_stale
            except ValueError:
                pass

        news = TeamNewsItem(
            news_id=item.get("news_id", ""), team=item.get("team", ""),
            match_id=item.get("match_id", ""), news_type=item.get("type", ""),
            subtype=item.get("subtype", ""), title=item.get("title", ""),
            detail=item.get("detail", ""), reliability=reliab,
            reliability_score=score, source=item.get("source", ""),
            timestamp=ts, age_hours=round(age, 2),
            is_fresh=is_fresh, is_stale=is_stale,
        )
        summary.items.append(news)
        if news.team: teams_seen.add(news.team)
        if news.match_id: matches_seen.add(news.match_id)
        if reliab == "rumor":
            summary.reliability_warning_count += 1
        if is_stale:
            summary.freshness_warning_count += 1

    summary.news_item_count = len(fixture.get("news_items", []))
    summary.normalized_news_count = len(summary.items)
    summary.team_count = len(teams_seen)
    summary.match_count = len(matches_seen)
    if summary.reliability_warning_count > 0:
        summary.warnings.append(f"{summary.reliability_warning_count} rumor/unconfirmed items; treat with low confidence.")
    if summary.freshness_warning_count > 0:
        summary.warnings.append(f"{summary.freshness_warning_count} stale news items (>{stale_hours}h old).")
    return summary
