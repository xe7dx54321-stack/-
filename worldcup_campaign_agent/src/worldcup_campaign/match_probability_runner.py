"""Match probability runner: generates probability preview reports."""

import json
from dataclasses import dataclass, asdict, field
from datetime import date
from pathlib import Path
from typing import Optional

from worldcup_campaign.match_registry import (
    MatchEntry, load_match_registry, get_matches_by_date,
)
from worldcup_campaign.team_rating import TeamRatingRegistry
from worldcup_campaign.probability_model import ProbabilityModel, MatchProbability
from worldcup_campaign.scoreline_model import ScorelineModel
from worldcup_campaign.over_under_model import OverUnderModel
from worldcup_campaign.handicap_model import HandicapModel
from worldcup_campaign.probability_quality import assess_quality


@dataclass
class MatchProbabilityReport:
    match_id: str
    match_number: int
    home_team: str
    away_team: str
    stage: str
    group: Optional[str]
    is_knockout: bool
    # 1x2
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    # Expected goals
    expected_goals_home: float
    expected_goals_away: float
    # Top scorelines
    top_scorelines: list[dict]
    # Over/under
    over_under: list[dict]
    # Handicap
    handicap: list[dict]
    # Quality
    confidence: float
    data_quality: str
    confidence_label: str
    warnings: list[str]


@dataclass
class ProbabilityPreview:
    current_date: str
    matches_count: int
    model_name: str
    model_version: str
    is_dry_run: bool
    matches: list[dict] = field(default_factory=list)
    safety: dict = field(default_factory=dict)


class MatchProbabilityRunner:
    """Generates match probability previews."""

    def __init__(
        self,
        ratings_path: str,
        prob_config_path: str,
        match_registry_path: str,
        policy_path: str,
    ):
        self.ratings = TeamRatingRegistry(ratings_path)
        self.prob_model = ProbabilityModel(prob_config_path)
        self.scoreline_model = ScorelineModel(
            self.prob_model.config.get("poisson_max_goals", 8)
        )
        self.ou_model = OverUnderModel(
            self.prob_model.config.get("over_under_lines", [0.5, 1.5, 2.5, 3.5, 4.5])
        )
        self.handicap_model = HandicapModel(
            self.prob_model.config.get("handicap_lines", None)
        )
        self.matches = load_match_registry(match_registry_path)
        # Load policy for safety flags only
        from worldcup_campaign.policy import load_campaign_policy
        self.policy = load_campaign_policy(policy_path)

    def _get_rating(self, team_code: str) -> tuple:
        """Get rating data for a team. Returns (overall, is_placeholder)."""
        r = self.ratings.get(team_code)
        if r:
            return r.overall, r.is_placeholder
        # TBD teams
        return 1600.0, True

    def run_for_date(self, target_date: str) -> ProbabilityPreview:
        """Run probability preview for all matches on a date."""
        dt = date.fromisoformat(target_date)
        day_matches = get_matches_by_date(dt, self.matches)

        reports = []
        for m in day_matches:
            reports.append(self._analyze_match(m))

        safety = {
            "campaign_analysis_only": self.policy.campaign_analysis_only,
            "real_bet_execution": self.policy.real_bet_execution,
            "auto_betting": self.policy.auto_betting,
            "external_betting_api_allowed": self.policy.external_betting_api_allowed,
            "real_money_instruction_allowed": self.policy.real_money_instruction_allowed,
        }

        return ProbabilityPreview(
            current_date=target_date,
            matches_count=len(reports),
            model_name=self.prob_model.config["model_name"],
            model_version=self.prob_model.config["model_version"],
            is_dry_run=self.prob_model.config["is_dry_run"],
            matches=[asdict(r) for r in reports],
            safety=safety,
        )

    def run_for_match_id(self, match_id: str) -> ProbabilityPreview:
        """Run probability preview for a single match by ID."""
        target_match = None
        for m in self.matches:
            if m.match_id == match_id:
                target_match = m
                break
        if target_match is None:
            raise ValueError(f"Match ID '{match_id}' not found in registry")

        report = self._analyze_match(target_match)

        safety = {
            "campaign_analysis_only": self.policy.campaign_analysis_only,
            "real_bet_execution": self.policy.real_bet_execution,
            "auto_betting": self.policy.auto_betting,
            "external_betting_api_allowed": self.policy.external_betting_api_allowed,
        }

        return ProbabilityPreview(
            current_date=target_match.date.isoformat(),
            matches_count=1,
            model_name=self.prob_model.config["model_name"],
            model_version=self.prob_model.config["model_version"],
            is_dry_run=self.prob_model.config["is_dry_run"],
            matches=[asdict(report)],
            safety=safety,
        )

    def _analyze_match(self, m: MatchEntry) -> MatchProbabilityReport:
        home_r, home_ph = self._get_rating(m.home_team)
        away_r, away_ph = self._get_rating(m.away_team)

        mp = self.prob_model.calculate(
            match_id=m.match_id,
            home_team=m.home_team,
            away_team=m.away_team,
            home_rating=home_r,
            away_rating=away_r,
            is_knockout=m.is_knockout,
            home_is_placeholder=home_ph,
            away_is_placeholder=away_ph,
        )

        # Scoreline
        scorelines = self.scoreline_model.calculate(
            mp.expected_goals_home, mp.expected_goals_away
        )
        top_sl = self.scoreline_model.get_top_scorelines(scorelines, 10)

        # Over/under
        ou_results = self.ou_model.calculate(scorelines)

        # Handicap
        hc_results = self.handicap_model.calculate(scorelines)

        # Quality
        qa = assess_quality(
            home_is_placeholder=home_ph,
            away_is_placeholder=away_ph,
            rating_diff_abs=abs(home_r - away_r),
            is_knockout=m.is_knockout,
            base_confidence=mp.confidence,
        )

        return MatchProbabilityReport(
            match_id=m.match_id,
            match_number=m.match_number,
            home_team=m.home_team,
            away_team=m.away_team,
            stage=m.stage,
            group=m.group,
            is_knockout=m.is_knockout,
            home_win_prob=mp.home_win_prob,
            draw_prob=mp.draw_prob,
            away_win_prob=mp.away_win_prob,
            expected_goals_home=mp.expected_goals_home,
            expected_goals_away=mp.expected_goals_away,
            top_scorelines=[{
                "scoreline": s.scoreline,
                "probability": s.probability,
            } for s in top_sl],
            over_under=[{
                "line": ou.line,
                "over_probability": ou.over_probability,
                "under_probability": ou.under_probability,
            } for ou in ou_results],
            handicap=[{
                "line": hc.line,
                "home_cover_probability": hc.home_cover_probability,
                "away_cover_probability": hc.away_cover_probability,
                "push_probability": hc.push_probability,
            } for hc in hc_results],
            confidence=qa.confidence,
            data_quality=qa.data_quality,
            confidence_label=qa.confidence_label,
            warnings=mp.warnings + qa.warnings,
        )

    def write_json(self, preview: ProbabilityPreview, path: str) -> None:
        data = asdict(preview)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def write_markdown(self, preview: ProbabilityPreview, path: str) -> None:
        lines = []
        lines.append("# Match Probability Preview")
        lines.append("")
        lines.append(f"- **Date:** {preview.current_date}")
        lines.append(f"- **Matches:** {preview.matches_count}")
        lines.append(f"- **Model:** {preview.model_name} v{preview.model_version}")
        lines.append(f"- **Dry Run:** {preview.is_dry_run}")
        lines.append("")

        for match in preview.matches:
            lines.append(f"## Match {match['match_number']}: {match['home_team']} vs {match['away_team']}")
            lines.append("")
            lines.append(f"- **Stage:** {match['stage']} | **Group:** {match.get('group', 'N/A')} | **KO:** {match['is_knockout']}")
            lines.append("")
            lines.append("### 1X2 Probabilities")
            lines.append("")
            lines.append(f"| Home Win | Draw | Away Win |")
            lines.append(f"|----------|------|----------|")
            lines.append(f"| {match['home_win_prob']:.1%} | {match['draw_prob']:.1%} | {match['away_win_prob']:.1%} |")
            lines.append("")
            lines.append(f"- **Expected Goals:** Home {match['expected_goals_home']} - {match['expected_goals_away']} Away")
            lines.append("")

            if match.get('top_scorelines'):
                lines.append("### Top Scorelines")
                lines.append("")
                lines.append("| Scoreline | Probability |")
                lines.append("|-----------|-------------|")
                for sl in match['top_scorelines'][:5]:
                    lines.append(f"| {sl['scoreline']} | {sl['probability']:.4f} |")
                lines.append("")

            if match.get('over_under'):
                lines.append("### Over/Under")
                lines.append("")
                lines.append("| Line | Over | Under |")
                lines.append("|------|------|-------|")
                for ou in match['over_under']:
                    lines.append(f"| {ou['line']} | {ou['over_probability']:.1%} | {ou['under_probability']:.1%} |")
                lines.append("")

            if match.get('handicap'):
                lines.append("### Handicap Projection")
                lines.append("")
                lines.append("| Line | Home Cover | Away Cover | Push |")
                lines.append("|------|------------|------------|------|")
                for hc in match['handicap']:
                    lines.append(f"| {hc['line']:+.1f} | {hc['home_cover_probability']:.1%} | {hc['away_cover_probability']:.1%} | {hc['push_probability']:.1%} |")
                lines.append("")

            lines.append(f"- **Confidence:** {match['confidence']:.2f} ({match['confidence_label']})")
            lines.append(f"- **Data Quality:** {match['data_quality']}")
            
            if match.get('warnings'):
                for w in match['warnings']:
                    lines.append(f"- {w}")
            lines.append("")

        lines.append("## Safety Boundary")
        lines.append("")
        lines.append("| Flag | Value |")
        lines.append("|------|-------|")
        for key, value in preview.safety.items():
            lines.append(f"| {key} | {value} |")
        lines.append("")
        lines.append("---")
        lines.append("*Generated by Match Probability Engine v1*")
        lines.append("")
        lines.append("> **Disclaimer:** All probabilities are from a seed-rating dry-run model. "
                     "NOT real team strength assessments. NOT betting advice.")

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("\n".join(lines), encoding="utf-8")