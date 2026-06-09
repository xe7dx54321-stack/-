"""Daily brief builder: generates Chinese-language daily campaign brief."""
import json, sys
from dataclasses import dataclass, field
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


@dataclass
class DailyBrief:
    title: str = "世界杯 Campaign Daily Brief"
    date: str = ""
    boss_summary: list = field(default_factory=list)
    researcher_detail: dict = field(default_factory=dict)
    today_focus: list = field(default_factory=list)
    bucket_brief: dict = field(default_factory=dict)
    parlay_brief: dict = field(default_factory=dict)
    futures_brief: dict = field(default_factory=dict)
    settlement_brief: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    next_actions: list = field(default_factory=list)
    safety_note: str = "Analysis only. Simulation only. NOT betting advice."
    analysis_only: bool = True
    simulation_only: bool = True
    not_betting_advice: bool = True


class DailyBriefBuilder:
    def __init__(self, brief_config_path: str):
        self.config = json.loads(Path(brief_config_path).read_text(encoding="utf-8-sig"))
        self.avoid = self.config.get("avoid_terms", [])

    def build(self, dashboard) -> DailyBrief:
        bs = dashboard.bankroll_summary
        cs = dashboard.calendar_summary
        ps = dashboard.parlay_summary
        fs = dashboard.futures_summary
        ss = dashboard.settlement_summary

        brief = DailyBrief(
            date=dashboard.current_date,
            boss_summary=[
                f"状态: {bs['bankroll_state']}, 流动本金 {bs['liquid_simulated_bankroll']} CNY",
                f"总权益: {bs['total_campaign_equity']} CNY (含锁定待结算 {bs['locked_pending_units']} CNY)",
                f"距离 {bs['target_bankroll']} 目标: {bs['required_multiplier_liquid']:.0f}x (流动), {bs['required_multiplier_equity']:.0f}x (含权益)",
                f"今日: {cs.get('stage','')} | {cs.get('match_count',0)} 场比赛 | 模式: {cs.get('daily_mode','')}",
                f"候选池: {dashboard.candidate_summary.get('total_candidates',0)} 候选, value_candidate=0 (synthetic odds 正常)",
                f"串关: {ps.get('source_candidates',0)} 候选 -> {ps.get('ranked_count',0)} 组合, 阻断 {ps.get('blocked_count',0)}",
                f"Futures: {fs.get('futures_odds_count',0)} 赔率, {fs.get('futures_bucket',0)} 在桶中",
                f"结算: {ss.get('settled',0)} 已结算, {ss.get('pending',0)} 待结算, {ss.get('hit',0)} 命中",
            ],
            researcher_detail={
                "campaign_state": dashboard.campaign_state,
                "bankroll": bs,
                "calendar": cs,
                "execution": dashboard.execution_schedule_summary,
            },
            today_focus=dashboard.execution_schedule_summary.get("recommended_modules", []),
            bucket_brief=dashboard.bucket_summary,
            parlay_brief=ps,
            futures_brief=fs,
            settlement_brief=ss,
            warnings=dashboard.warnings_summary,
            next_actions=[
                "运行 daily analysis 模块 (按 execution schedule)",
                "检查 candidate pools 是否有更新",
                "如为 matchday: 录入赛后 manual result seed",
                "运行 post-match settlement 更新本金状态",
                "检查 path sanity / probability sanity warnings",
                "查看 daily brief 确认下一步重点",
            ],
        )
        return brief

    def render_markdown(self, brief: DailyBrief) -> str:
        lines = [
            "# 世界杯 Campaign Daily Brief",
            "",
            f"**日期:** {brief.date} | **状态:** 分析中 | **模式:** simulation only",
            "",
            "## 一、老板摘要",
        ]
        for i, s in enumerate(brief.boss_summary, 1):
            lines.append(f"{i}. {s}")
        lines.append("")
        lines.append("## 二、研究员详情")
        rd = brief.researcher_detail
        lines.append("### Campaign State")
        lines.append(f"- 状态: {rd.get('campaign_state',{}).get('state','?')}")
        bs = rd.get('bankroll',{})
        lines.append(f"- 流动本金: {bs.get('liquid_simulated_bankroll','?')} CNY")
        lines.append(f"- 锁定待结算: {bs.get('locked_pending_units','?')} CNY")
        lines.append(f"- 总权益: {bs.get('total_campaign_equity','?')} CNY")
        lines.append("")
        lines.append("### 今日分析流程")
        for m in brief.today_focus:
            lines.append(f"- {m}")
        lines.append("")
        lines.append("### 五桶候选池")
        for b, info in (brief.bucket_brief or {}).items():
            lines.append(f"- **{b}**: budget={info.get('budget',0)}, candidates={info.get('candidate_count',0)}")
        lines.append("")
        lines.append("### 串关池")
        pb = brief.parlay_brief
        lines.append(f"- 源候选: {pb.get('source_candidates',0)} | 组合: {pb.get('ranked_count',0)} | 阻断: {pb.get('blocked_count',0)}")
        lines.append("")
        lines.append("### Futures / 长周期路径")
        fb = brief.futures_brief
        lines.append(f"- 模拟: {fb.get('groups_simulated',0)} 组 | Futures桶: {fb.get('futures_bucket',0)}")
        lines.append(f"- Winner prob sum: {fb.get('winner_prob_sum',0):.4f} (v1 simplified)")
        lines.append("")
        lines.append("### Settlement / Pending")
        sb = brief.settlement_brief
        lines.append(f"- 已结算: {sb.get('settled',0)} | 待结算: {sb.get('pending',0)}")
        lines.append(f"- 命中: {sb.get('hit',0)} | 未命中: {sb.get('miss',0)}")
        lines.append("")
        lines.append("### Warnings")
        for w in brief.warnings[:10]:
            lines.append(f"- {w}")
        lines.append("")
        lines.append("### 下一步动作")
        for a in brief.next_actions:
            lines.append(f"- {a}")
        lines.append("")
        lines.append("## Safety Note")
        lines.append(f"> {brief.safety_note}")
        return chr(10).join(lines)

    def validate_avoid_terms(self, text: str) -> list[str]:
        found = []
        for term in self.avoid:
            if term in text:
                found.append(term)
        return found
