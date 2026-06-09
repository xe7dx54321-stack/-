"""Knockout path simulator: estimate team advancement through tournament stages."""
import json, sys
from dataclasses import dataclass
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


@dataclass
class TournamentPath:
    team_code: str
    team_name: str
    group: str
    rating: float
    group_qual_prob: float = 0.0
    group_winner_prob: float = 0.0
    reach_r32: float = 0.0
    reach_r16: float = 0.0
    reach_qf: float = 0.0
    reach_sf: float = 0.0
    reach_final: float = 0.0
    winner_prob: float = 0.0
    runner_up_prob: float = 0.0
    expected_matches_played: float = 3.0


class KnockoutPathSimulator:
    def __init__(self, ratings_path: str, config_path: str):
        self.ratings = json.loads(Path(ratings_path).read_text(encoding="utf-8-sig"))
        self.config = json.loads(Path(config_path).read_text(encoding="utf-8-sig"))
        self.exp = self.config.get("advancement_base_probability", {}).get("power_exponent", 1.5)
        self.rating_map = {}
        self.name_map = {}
        self.group_map = {}
        for r in self.ratings:
            code = r["team_code"]
            self.rating_map[code] = r.get("overall", 1500)
            self.name_map[code] = r.get("team_name", code)
            self.group_map[code] = r.get("group", "")

    def build_paths(self, group_results: list) -> list[TournamentPath]:
        # Collect teams and their group stage probabilities
        paths = []
        all_r32_teams = set()

        for gr in group_results:
            for s in gr.standings:
                code = s.team_code
                rating = self.rating_map.get(code, 1500)
                qual_prob = s.qualification_probability
                winner_p = s.group_winner_probability

                tp = TournamentPath(
                    team_code=code,
                    team_name=self.name_map.get(code, code),
                    group=self.group_map.get(code, ""),
                    rating=rating,
                    group_qual_prob=qual_prob,
                    group_winner_prob=winner_p,
                    reach_r32=qual_prob  # Qualifying = reaching R32
                )
                paths.append(tp)
                if qual_prob > 0.3:  # significant chance to reach R32
                    all_r32_teams.add(code)

        # Calculate knockout advancement using rating-based power law
        all_ratings = [self.rating_map.get(t, 1500) for t in all_r32_teams]
        avg_r32_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 1500

        for tp in paths:
            if tp.reach_r32 < 0.01:
                continue

            # R32 -> R16: face an average R32 opponent
            p_adv_r16 = self._advance_prob(tp.rating, avg_r32_rating) if tp.rating > 0 else 0.4
            tp.reach_r16 = round(tp.reach_r32 * p_adv_r16, 6)

            # R16 -> QF: face stronger avg opponent
            avg_r16_rating = avg_r32_rating * 1.05
            p_adv_qf = self._advance_prob(tp.rating, avg_r16_rating)
            tp.reach_qf = round(tp.reach_r16 * p_adv_qf, 6)

            # QF -> SF
            avg_qf_rating = avg_r32_rating * 1.10
            p_adv_sf = self._advance_prob(tp.rating, avg_qf_rating)
            tp.reach_sf = round(tp.reach_qf * p_adv_sf, 6)

            # SF -> Final
            avg_sf_rating = avg_r32_rating * 1.15
            p_adv_final = self._advance_prob(tp.rating, avg_sf_rating)
            tp.reach_final = round(tp.reach_sf * p_adv_final, 6)

            # Winner: win the final (50/50 vs similar opponent)
            tp.winner_prob = round(tp.reach_final * 0.5, 6)
            tp.runner_up_prob = round(tp.reach_final * 0.5, 6)

            # Expected matches: 3 group + weighted knockout
            ko_matches = (tp.reach_r16 * 1 + tp.reach_qf * 1 + tp.reach_sf * 1 +
                         tp.reach_final * 1 + tp.winner_prob * 0)  # final counted in reach_final
            tp.expected_matches_played = round(3.0 + tp.reach_r16 + tp.reach_qf +
                                               tp.reach_sf + tp.reach_final, 2)

        return paths

    def _advance_prob(self, rating_a: float, rating_b: float) -> float:
        if rating_a <= 0 or rating_b <= 0:
            return 0.5
        ratio = rating_a / rating_b
        return min(0.95, max(0.05, ratio ** self.exp / (1 + ratio ** self.exp)))

    def calculate_exact_final_pairs(self, paths: list[TournamentPath]) -> list[dict]:
        pairs = []
        for i, a in enumerate(paths):
            for b in paths[i+1:]:
                prob = a.reach_final * b.reach_final
                if prob > 0.00001:
                    pairs.append({
                        "team_a": a.team_code,
                        "team_b": b.team_code,
                        "probability": round(prob, 8),
                        "team_a_name": a.team_name,
                        "team_b_name": b.team_name,
                    })
        pairs.sort(key=lambda x: x["probability"], reverse=True)
        return pairs[:50]

    def get_team_path(self, team_code: str, paths: list[TournamentPath]) -> TournamentPath:
        for p in paths:
            if p.team_code == team_code:
                return p
        return None
