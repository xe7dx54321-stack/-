"""Futures odds generator: synthetic odds from tournament path probabilities."""
import json, sys
from dataclasses import dataclass, field
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


@dataclass
class FuturesOdds:
    team_code: str
    team_name: str
    market_type: str
    selection_id: str = ""
    selection_label: str = ""
    path_probability: float = 0.0
    synthetic_odds: float = 1.01
    odds_band: str = "low"
    source: str = "synthetic_from_probability"
    uses_real_bookmaker_odds: bool = False
    analysis_only: bool = True
    not_betting_advice: bool = True


class FuturesOddsGenerator:
    def __init__(self, odds_policy_path: str, futures_market_config_path: str):
        self.policy = json.loads(Path(odds_policy_path).read_text(encoding="utf-8-sig"))
        self.market_config = json.loads(Path(futures_market_config_path).read_text(encoding="utf-8-sig"))
        self.vig = self.policy.get("default_vig", 0.15)
        self.min_odds = self.policy.get("min_decimal_odds", 1.01)
        self.max_odds = self.policy.get("max_decimal_odds", 10000.0)
        self.bands = self.policy.get("odds_bands", {})

    def generate_from_paths(self, paths: list) -> list[FuturesOdds]:
        all_odds = []
        markets = self.market_config.get("markets", [])

        prob_map = {
            "group_qualification": "group_qual_prob",
            "group_winner": "group_winner_prob",
            "reach_round_of_32": "reach_r32",
            "reach_round_of_16": "reach_r16",
            "reach_quarter_final": "reach_qf",
            "reach_semi_final": "reach_sf",
            "reach_final": "reach_final",
            "winner": "winner_prob",
            "runner_up": "runner_up_prob",
        }

        for market in markets:
            mt = market["market_type"]
            if mt == "exact_final_pair":
                continue  # Handled separately
            if mt == "golden_boot":
                all_odds.extend(self._generate_golden_boot_odds(paths))
                continue

            attr = prob_map.get(mt)
            if not attr:
                continue

            for tp in paths:
                prob = getattr(tp, attr, 0.0)
                if prob < 0.0001:
                    continue
                odds = self._prob_to_odds(prob)
                band = self._classify_band(odds)

                all_odds.append(FuturesOdds(
                    team_code=tp.team_code,
                    team_name=tp.team_name,
                    market_type=mt,
                    selection_id=f"TEAM_{tp.team_code}",
                    selection_label=f"{tp.team_name} ({tp.team_code})",
                    path_probability=round(prob, 6),
                    synthetic_odds=odds,
                    odds_band=band,
                ))

        return all_odds

    def generate_exact_final_pair_odds(self, pairs: list[dict]) -> list[FuturesOdds]:
        results = []
        for pair in pairs:
            prob = pair["probability"]
            if prob < 0.00001:
                continue
            odds = self._prob_to_odds(prob)
            band = self._classify_band(odds)
            results.append(FuturesOdds(
                team_code=f"{pair['team_a']}_vs_{pair['team_b']}",
                team_name=f"{pair['team_a_name']} vs {pair['team_b_name']}",
                market_type="exact_final_pair",
                selection_id=f"EFP_{pair['team_a']}_{pair['team_b']}",
                selection_label=f"{pair['team_a_name']} vs {pair['team_b_name']}",
                path_probability=round(prob, 6),
                synthetic_odds=odds,
                odds_band=band,
            ))
        return results

    def _generate_golden_boot_odds(self, paths: list) -> list:
        # Simplified: use attack rating * expected_matches as proxy
        results = []
        scores = []
        for tp in paths:
            score = tp.rating * tp.expected_matches_played * 0.5 / 1500
            scores.append((tp, score))
        total = sum(s for _, s in scores)
        if total <= 0:
            return results

        for tp, score in scores:
            prob = score / total if total > 0 else 0
            if prob < 0.001:
                continue
            odds = self._prob_to_odds(prob)
            band = self._classify_band(odds)
            results.append(FuturesOdds(
                team_code=tp.team_code,
                team_name=tp.team_name,
                market_type="golden_boot",
                selection_id=f"GB_{tp.team_code}",
                selection_label=f"{tp.team_name} Golden Boot",
                path_probability=round(prob, 6),
                synthetic_odds=odds,
                odds_band=band,
            ))
        return results

    def _prob_to_odds(self, prob: float) -> float:
        if prob <= 0:
            return self.max_odds
        raw_odds = 1.0 / (prob * (1.0 + self.vig))
        return round(max(self.min_odds, min(self.max_odds, raw_odds)), 2)

    def _classify_band(self, odds: float) -> str:
        for name, r in self.bands.items():
            if r["min"] <= odds < r["max"]:
                return name
        return "lottery"


class FuturesProbabilityAggregator:
    def __init__(self, market_config_path: str):
        self.config = json.loads(Path(market_config_path).read_text(encoding="utf-8-sig"))

    def build_summary(self, paths: list, pairs: list, futures_odds: list[FuturesOdds]) -> dict:
        return {
            "total_teams": len(paths),
            "winner_probability_sum": round(sum(p.winner_prob for p in paths), 6),
            "runner_up_probability_sum": round(sum(p.runner_up_prob for p in paths), 6),
            "exact_final_pair_count": len(pairs),
            "exact_final_pair_probability_sum": round(sum(x["probability"] for x in pairs), 6),
            "futures_odds_count": len(futures_odds),
            "markets_covered": list(set(o.market_type for o in futures_odds)),
            "analysis_only": True,
            "simulation_only": True,
            "not_betting_advice": True,
            "data_quality": "seed_rating_based_simulation",
        }
