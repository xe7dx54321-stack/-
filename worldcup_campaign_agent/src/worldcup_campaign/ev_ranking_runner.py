"""EV ranking runner: orchestrates probability 鈫?odds 鈫?EV 鈫?ranking pipeline."""

import json
from dataclasses import asdict, field, dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from worldcup_campaign.match_registry import load_match_registry, get_matches_by_date
from worldcup_campaign.team_rating import TeamRatingRegistry
from worldcup_campaign.probability_model import ProbabilityModel
from worldcup_campaign.scoreline_model import ScorelineModel
from worldcup_campaign.over_under_model import OverUnderModel
from worldcup_campaign.probability_sanity import ProbabilitySanityGuard
from worldcup_campaign.mock_odds import MockOddsGenerator
from worldcup_campaign.market_candidate import MarketCandidateBuilder
from worldcup_campaign.ev_ranking import EVRanker
from worldcup_campaign.target_contribution_preview import TargetContributionCalculator
from worldcup_campaign.policy import load_campaign_policy


@dataclass
class EVRankingPreview:
    date: str
    candidate_count: int
    value_candidate_count: int
    odds_source_mode: str
    uses_real_bookmaker_odds: bool
    candidates: list[dict] = field(default_factory=list)
    sanity_summary: dict = field(default_factory=dict)
    safety: dict = field(default_factory=dict)
    not_betting_advice: bool = True


class EVRankingRunner:
    """Runs the full probability 鈫?EV ranking pipeline."""

    def __init__(
        self, ratings_path, prob_config_path, match_registry_path,
        policy_path, sanity_config_path, odds_policy_path, ev_config_path,
    ):
        self.ratings = TeamRatingRegistry(ratings_path)
        self.prob_model = ProbabilityModel(prob_config_path)
        self.scoreline_model = ScorelineModel(8)
        self.sanity = ProbabilitySanityGuard(sanity_config_path)
        self.odds_gen = MockOddsGenerator(odds_policy_path)
        self.candidate_builder = MarketCandidateBuilder(ev_config_path)
        self.ranker = EVRanker()
        self.tc_calc = TargetContributionCalculator()
        self.matches = load_match_registry(match_registry_path)
        self.policy = load_campaign_policy(policy_path)

        import json as j
        self.odds_policy = j.loads(Path(odds_policy_path).read_text(encoding="utf-8-sig"))

    def run(
        self, target_date: str, current_bankroll: float, windows_left: int = None,
    ) -> EVRankingPreview:
        dt = date.fromisoformat(target_date)
        day_matches = get_matches_by_date(dt, self.matches)
        if windows_left is None:
            from worldcup_campaign.opportunity_window import count_effective_windows
            windows_left = count_effective_windows(dt, self.matches)

        all_candidates = []
        sanity_stats = {"total_checked": 0, "repaired": 0, "blocked": 0, "warnings": []}

        for m in day_matches:
            hr = self.ratings.get_or_default(m.home_team)
            ar = self.ratings.get_or_default(m.away_team)

            mp = self.prob_model.calculate(
                m.match_id, m.home_team, m.away_team, hr.overall, ar.overall,
                is_knockout=m.is_knockout,
                home_is_placeholder=hr.is_placeholder,
                away_is_placeholder=ar.is_placeholder,
            )

            # Sanity check
            sanity_result = self.sanity.check_1x2(
                mp.home_win_prob, mp.draw_prob, mp.away_win_prob
            )
            sanity_stats["total_checked"] += 1
            if sanity_result.repaired:
                sanity_stats["repaired"] += 1
                sanity_stats["warnings"].extend(sanity_result.warnings)
            if sanity_result.blocked:
                sanity_stats["blocked"] += 1
                continue

            # Use repaired probabilities for odds generation
            hp, dp, ap = (
                sanity_result.repaired_home_prob,
                sanity_result.repaired_draw_prob,
                sanity_result.repaired_away_prob,
            )

            # Generate mock odds
            odds_1x2 = self.odds_gen.generate_1x2(m.match_id, hp, dp, ap)
            home_odds = next(o.odds for o in odds_1x2 if o.selection == "home")
            draw_odds = next(o.odds for o in odds_1x2 if o.selection == "draw")
            away_odds = next(o.odds for o in odds_1x2 if o.selection == "away")

            # Build 1x2 candidates
            c1 = self.candidate_builder.build_1x2_candidates(
                m.match_id, m.match_number, m.home_team, m.away_team, m.stage,
                hp, dp, ap, home_odds, draw_odds, away_odds,
                warnings=sanity_result.warnings,
            )
            for c in c1:
                tc = self.tc_calc.calculate(current_bankroll, c.mock_odds, windows_left)
                c.target_contribution_preview = round(tc.contribution_ratio, 4)
            all_candidates.extend(c1)

            # Over/under candidates
            scorelines = self.scoreline_model.calculate(mp.expected_goals_home, mp.expected_goals_away)
            ou_model = OverUnderModel()
            ou_results = ou_model.calculate(scorelines)
            for ou in ou_results:
                ou_odds = self.odds_gen.generate_over_under(
                    m.match_id, ou.line, ou.over_probability, ou.under_probability
                )
                o_odds = next(o.odds for o in ou_odds if o.selection == "over")
                u_odds = next(o.odds for o in ou_odds if o.selection == "under")
                c2 = self.candidate_builder.build_ou_candidates(
                    m.match_id, m.match_number, m.home_team, m.away_team, m.stage,
                    ou.line, ou.over_probability, ou.under_probability, o_odds, u_odds,
                )
                for c in c2:
                    tc = self.tc_calc.calculate(current_bankroll, c.mock_odds, windows_left)
                    c.target_contribution_preview = round(tc.contribution_ratio, 4)
                all_candidates.extend(c2)

        # Rank
        ranking = self.ranker.rank(
            all_candidates, target_date,
            self.odds_policy.get("odds_source_mode", "synthetic_from_model"),
            sanity_summary=sanity_stats,
        )

        # Safety
        safety = {
            "campaign_analysis_only": self.policy.campaign_analysis_only,
            "real_bet_execution": self.policy.real_bet_execution,
            "auto_betting": self.policy.auto_betting,
            "external_betting_api_allowed": self.policy.external_betting_api_allowed,
            "real_money_instruction_allowed": self.policy.real_money_instruction_allowed,
        }

        return EVRankingPreview(
            date=ranking.date,
            candidate_count=ranking.candidate_count,
            value_candidate_count=ranking.value_candidate_count,
            odds_source_mode=ranking.odds_source_mode,
            uses_real_bookmaker_odds=False,
            candidates=[asdict(c) for c in ranking.candidates],
            sanity_summary=ranking.sanity_summary,
            safety=safety,
            not_betting_advice=True,
        )

    def write_json(self, preview: EVRankingPreview, path: str) -> None:
        data = asdict(preview)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def write_markdown(self, preview: EVRankingPreview, path: str) -> None:
        lines = []
        lines.append("# EV Ranking Preview")
        lines.append("")
        lines.append(f"- **Date:** {preview.date}")
        lines.append(f"- **Candidates:** {preview.candidate_count}")
        lines.append(f"- **Value Candidates:** {preview.value_candidate_count}")
        lines.append(f"- **Odds Source:** {preview.odds_source_mode}")
        lines.append(f"- **Uses Real Bookmaker Odds:** {preview.uses_real_bookmaker_odds}")
        lines.append("")

        ss = preview.sanity_summary
        if ss:
            lines.append("## Probability Sanity")
            lines.append("")
            lines.append(f"- Checked: {ss.get('total_checked', 0)} | Repaired: {ss.get('repaired', 0)} | Blocked: {ss.get('blocked', 0)}")
            lines.append("")

        if preview.candidates:
            lines.append("## Top Candidates")
            lines.append("")
            lines.append("| # | Match | Market | Selection | Odds | Model Prob | Edge | EV | Value | Buckets |")
            lines.append("|---|-------|--------|-----------|------|------------|------|-----|-------|---------|")
            for i, c in enumerate(preview.candidates[:15]):
                lines.append(
                    f"| {i+1} | {c['match_id']} | {c['market_type']} | {c['selection']} "
                    f"| {c['mock_odds']} | {c['model_probability']:.1%} | {c['edge']:.1%} "
                    f"| {c['ev']:+.3f} | {c['value_flag']} | {','.join(c.get('bucket_eligibility', []))} |"
                )
            lines.append("")

        lines.append("## Safety Boundary")
        lines.append("")
        lines.append("| Flag | Value |")
        lines.append("|------|-------|")
        for key, value in preview.safety.items():
            lines.append(f"| {key} | {value} |")
        lines.append("")
        lines.append("---")
        lines.append("*Generated by EV Ranking Engine v1*")
        lines.append("> **Disclaimer:** Uses mock/synthetic odds. NOT real bookmaker odds. NOT betting advice.")

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("\n".join(lines), encoding="utf-8")