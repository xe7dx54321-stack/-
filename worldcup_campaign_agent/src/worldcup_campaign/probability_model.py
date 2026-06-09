"""1x2 probability model based on team ratings."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from worldcup_campaign.team_rating import TeamRatingRegistry


@dataclass
class MatchProbability:
    match_id: str
    home_team: str
    away_team: str
    home_rating: float
    away_rating: float
    rating_diff: float
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    expected_goals_home: float
    expected_goals_away: float
    confidence: float
    data_quality: str
    warnings: list[str]


class ProbabilityModel:
    """Generates 1x2 probabilities and expected goals from team ratings."""

    def __init__(self, config_path: str):
        self.config = json.loads(Path(config_path).read_text(encoding="utf-8-sig"))
        self.home_adv = self.config["home_advantage"]
        self.draw_margin = self.config["draw_margin"]
        self.eg_baseline = self.config["expected_goals_baseline"]
        self.eg_home_boost = self.config["expected_goals_home_boost"]
        self.eg_per_100 = self.config["expected_goals_per_100_rating"]
        self.conf_high = self.config["confidence"]["high_rating_diff"]
        self.conf_medium = self.config["confidence"]["medium_rating_diff"]
        self.conf_low = self.config["confidence"]["low_rating_confidence"]
        self.conf_high_v = self.config["confidence"]["high_rating_confidence"]
        self.seed_penalty = self.config["confidence"]["seed_data_penalty"]
        self.placeholder_penalty = self.config["confidence"]["placeholder_team_penalty"]
        self.ko_boost = self.config["confidence"]["knockout_uncertainty_boost"]

    def calculate(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        home_rating: float,
        away_rating: float,
        is_knockout: bool = False,
        home_is_placeholder: bool = False,
        away_is_placeholder: bool = False,
    ) -> MatchProbability:
        """Calculate 1x2 probabilities for a match."""
        warnings = []
        
        # Effective rating diff with home advantage
        effective_diff = (home_rating + self.home_adv) - away_rating
        
        # Convert to win probability using sigmoid-like function
        # p(home) = 1 / (1 + 10^(-diff/400))
        home_win_prob = 1.0 / (1.0 + 10.0 ** (-effective_diff / 400.0))
        away_win_prob = 1.0 / (1.0 + 10.0 ** (effective_diff / 400.0))
        
        # Draw probability fills the gap, scaled by draw_margin
        draw_factor = self.draw_margin / 100.0
        raw_gap = 1.0 - home_win_prob - away_win_prob
        draw_prob = max(0, raw_gap * draw_factor) if raw_gap > 0 else 0.02
        
        # Scale back if needed
        if home_win_prob + draw_prob + away_win_prob > 1.0:
            scale = (1.0 - draw_prob) / (home_win_prob + away_win_prob)
            home_win_prob *= scale
            away_win_prob *= scale
        
        # Expected goals
        home_attack = home_rating / 1700.0
        away_defense = (1700.0 - (away_rating - 1700.0)) / 1700.0
        eg_home = self.eg_baseline + self.eg_home_boost + (self.eg_per_100 * (home_rating - 1700) / 100)
        eg_home = max(0.3, min(5.0, eg_home))
        
        away_attack = away_rating / 1700.0
        home_defense = (1700.0 - (home_rating - 1700.0)) / 1700.0
        eg_away = self.eg_baseline + (self.eg_per_100 * (away_rating - 1700) / 100)
        eg_away = max(0.3, min(5.0, eg_away))
        
        # Confidence calculation
        abs_diff = abs(home_rating - away_rating)
        if abs_diff >= self.conf_high:
            base_conf = self.conf_high_v
        elif abs_diff >= self.conf_medium:
            base_conf = (self.conf_high_v + self.conf_low) / 2
        else:
            base_conf = self.conf_low
        
        # Penalties
        conf = base_conf
        conf -= self.seed_penalty
        if home_is_placeholder:
            conf -= self.placeholder_penalty
        if away_is_placeholder:
            conf -= self.placeholder_penalty
        if is_knockout:
            conf -= self.ko_boost
        
        conf = max(0.1, min(0.95, conf))
        
        # Data quality
        if home_is_placeholder or away_is_placeholder:
            dq = "low"
        elif abs_diff < self.conf_medium:
            dq = "medium"
        else:
            dq = "medium_high"
        
        if home_is_placeholder:
            warnings.append(f"Placeholder rating for {home_team}")
        if away_is_placeholder:
            warnings.append(f"Placeholder rating for {away_team}")
        
        return MatchProbability(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            home_rating=home_rating,
            away_rating=away_rating,
            rating_diff=round(effective_diff, 1),
            home_win_prob=round(home_win_prob, 4),
            draw_prob=round(draw_prob, 4),
            away_win_prob=round(away_win_prob, 4),
            expected_goals_home=round(eg_home, 2),
            expected_goals_away=round(eg_away, 2),
            confidence=round(conf, 4),
            data_quality=dq,
            warnings=warnings,
        )