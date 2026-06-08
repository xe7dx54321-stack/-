# WorldCup Campaign Strategy Agent

世界杯全赛程策略规划系统 — 用于分析 2026 年世界杯 104 场比赛及长周期市场，以初始本金 100、目标本金 1,000,000、每日最大使用当前本金 50% 为 campaign policy，输出唯一每日统一策略。

> **注意：本系统只做 campaign analysis / simulation / strategy planning，不做真实下注执行，不接任何真实下注 API，不登录任何投注平台，不承诺盈利。**

---

## 项目定位

这不是"每天临时找一两个高赔下注点"，而是一个**世界杯全赛程 Campaign Strategy Engine**：

- 赛前生成 104 场战役地图
- 比赛期间根据本金状态、赛程阶段、赔率变化、已发生赛果和未结算长周期仓位，输出唯一一套当日策略组合
- 核心优化目标：最大化达成目标概率，而不是单纯最大化单笔 EV

---

## 为什么每天只输出一套策略？

本系统是 **Campaign Strategy Agent**，不是下注推荐器：

- 每日输出的是资金桶骨架 + 策略标签，不包含具体比赛推荐
- 不提供多个互斥方案（那是拍脑袋），而是提供精准的一条策略路径
- 赛后根据实际结果自动切换到预设分支路径
- 策略骨架 = Reserve/Core/Edge/Attack/Futures 五个桶 + 对应市场类别

---

## Round 1 已完成模块（资金地基）

| 模块 | 文件 | 功能 |
|------|------|------|
| Campaign Policy Engine | `policy.py` | 本金/目标/上限定义与校验 |
| Bankroll State Machine | `bankroll_state.py` | S0-S7 状态分类，bucket 分配 |
| Market Universe Registry | `market_registry.py` | 20 种玩法注册与 bucket 查询 |
| Odds / EV Engine | `odds_math.py` | 隐含概率、去水、EV、串关计算 |
| Target Math | `target_math.py` | 目标倍率、每窗口所需增长、紧迫度 |
| Foundation Runner | `runner.py` | 基础 dry-run 执行器 |

## Round 2 已完成模块（赛程日历）

| 模块 | 文件 | 功能 |
|------|------|------|
| Stage Mapper | `stage_mapper.py` | 日期→阶段映射 |
| Match Registry | `match_registry.py` | 104 场比赛加载与查询 |
| Calendar Engine | `calendar_engine.py` | 组合赛程+比赛+政策的引擎 |
| Opportunity Window | `opportunity_window.py` | 剩余比赛/窗口计算 |
| Calendar Runner | `calendar_runner.py` | 日历预览报告 |

## Round 3 新增模块（每日统一策略 v1）

| 模块 | 文件 | 功能 |
|------|------|------|
| Strategy Profile Selector | `strategy_profile.py` | 基于 stage + bankroll state 选择风险策略 |
| Match Strategy Labeler | `match_strategy_labeler.py` | 给每场比赛打策略标签（非下注建议） |
| Strategy Allocator | `strategy_allocator.py` | 资金桶分配到可用市场类别 |
| Scenario Preview | `scenario_preview.py` | 全中/全失/部分中等情景投影 |
| Daily Strategy Engine | `daily_strategy.py` | 整合 R1+R2+R3 的主引擎 |
| Daily Strategy Runner | `daily_strategy_runner.py` | 日报生成 |

### 五个资金桶的含义

| 桶 | 用途 | 风险等级 |
|----|------|----------|
| **Reserve** | 保留现金，不参与部署（≥50%本金） | 零风险 |
| **Core** | 低风险高确定性市场（1X2、double chance） | 低 |
| **Edge** | 中等风险价值市场（让球、大小球、2串1） | 中 |
| **Attack** | 高赔率机会（比分、3串1、4串1） | 高 |
| **Futures** | 长周期仓位（晋级、冠亚军、金靴） | 长期 |

### Match Label 说明

Match label 是**策略候选标签**，不是下注建议：

- `high_confidence_core` — 适合 Core 桶的低风险比赛
- `value_edge` — 有价值空间的 Edge 桶比赛
- `high_odds_attack` — 高赔率 Attack 候选
- `group_decider` — 出线关键战
- `knockout_high_stakes` — 淘汰赛高关注度
- `championship_match` — 决赛/半决赛级别
- `opening_match` — 开幕/首轮高不确定性
- `futures_position` — 适合长周期投入

### Scenario Preview 说明

Scenario preview 是 **placeholder projection**（占位性情景投影），不是预测或承诺：
- `all_miss` — 全部失败后本金状态
- `all_hit` — 全部命中后本金状态
- `attack_hit` — Attack 桶单独命中
- `partial_hit` — Core+Edge 命中

---

## 安全边界

```text
real_bet_execution = false
auto_betting = false
external_betting_api_allowed = false
real_money_instruction_allowed = false
campaign_analysis_only = true
daily_max_deploy_ratio <= 0.5
reserve_min_ratio >= 0.5
```

---

## 如何运行

```bash
# 全部测试
python -m pytest tests -v

# Round 1: Foundation dry-run
python scripts/run_campaign_foundation.py --bankroll 100 --windows-left 40 --json

# Round 2: Calendar preview
python scripts/run_calendar_preview.py --date 2026-06-11 --json

# Round 3: Daily strategy preview
python scripts/run_daily_strategy_preview.py --date 2026-06-11 --bankroll 100 --json
python scripts/run_daily_strategy_preview.py --date 2026-06-24 --bankroll 100 --json
python scripts/run_daily_strategy_preview.py --date 2026-07-19 --bankroll 100 --json
python scripts/run_daily_strategy_preview.py --date 2026-06-11 --bankroll 5000 --json
```

输出文件：
- `reports/generated/foundation_preview.{json,md}`
- `reports/generated/calendar_preview.{json,md}`
- `reports/generated/daily_strategy_preview.{json,md}`

---

## 当前暂未实现

1. 暂未接真实赔率
2. 暂未接真实球队强弱模型
3. 暂未做 EV 排序
4. 暂未输出具体比赛候选选项（如"买 A 队胜"）
5. 暂未做真实 stake 分配到具体比赛
6. 暂未处理赛后结算
7. 暂未执行任何真实下注功能

---

## 下一轮建议

Round 4: Match Probability v1 — 接入基础球队评分和简单概率模型，让系统从"策略骨架"走向"比赛概率判断"。

---

## 项目结构

```
worldcup_campaign_agent/
  README.md
  Makefile
  config/
    campaign_policy.json
    bankroll_states.json
    market_universe.json
    worldcup_stage_map.json
    worldcup_calendar_policy.json
    daily_strategy_rules.json
    match_tagging_rules.json
    scenario_rules.json
  data/seed/
    worldcup_2026_match_registry.json
    worldcup_2026_groups.json
    worldcup_2026_venues.json
  schemas/
    match.schema.json / group.schema.json / stage.schema.json
    calendar_preview.schema.json
    daily_strategy.schema.json
    match_strategy_label.schema.json
    scenario_preview.schema.json
  src/worldcup_campaign/
    __init__.py
    policy.py / bankroll_state.py / market_registry.py
    odds_math.py / target_math.py / runner.py
    stage_mapper.py / match_registry.py
    calendar_engine.py / opportunity_window.py / calendar_runner.py
    strategy_profile.py / match_strategy_labeler.py
    strategy_allocator.py / scenario_preview.py
    daily_strategy.py / daily_strategy_runner.py
  scripts/
    run_campaign_foundation.py
    run_calendar_preview.py
    run_daily_strategy_preview.py
  tests/
    conftest.py
    test_policy.py / test_bankroll_state.py / test_market_registry.py
    test_odds_math.py / test_target_math.py / test_runner_foundation.py
    test_stage_mapper.py / test_match_registry.py
    test_calendar_engine.py / test_opportunity_window.py / test_calendar_runner.py
    test_strategy_profile.py / test_match_strategy_labeler.py
    test_strategy_allocator.py / test_scenario_preview.py
    test_daily_strategy_runner.py
  reports/generated/
    .gitkeep
```