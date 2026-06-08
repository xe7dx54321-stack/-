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

## Round 1 已完成模块

| 模块 | 文件 | 功能 |
|------|------|------|
| Campaign Policy Engine | `src/worldcup_campaign/policy.py` | 本金/目标/上限定义与校验 |
| Bankroll State Machine | `src/worldcup_campaign/bankroll_state.py` | S0-S7 状态分类，bucket 分配 |
| Market Universe Registry | `src/worldcup_campaign/market_registry.py` | 20 种玩法注册与 bucket 查询 |
| Odds / EV Engine | `src/worldcup_campaign/odds_math.py` | 隐含概率、去水、EV、串关计算 |
| Target Math | `src/worldcup_campaign/target_math.py` | 目标倍率、每窗口所需增长、紧迫度 |
| Foundation Runner | `src/worldcup_campaign/runner.py` | 基础 dry-run 执行器 |

## Round 2 新增模块

| 模块 | 文件 | 功能 |
|------|------|------|
| Stage Mapper | `src/worldcup_campaign/stage_mapper.py` | 日期→阶段映射，阶段校验 |
| Match Registry | `src/worldcup_campaign/match_registry.py` | 104 场比赛加载与查询 |
| Calendar Engine | `src/worldcup_campaign/calendar_engine.py` | 组合赛程+比赛+政策的状态引擎 |
| Opportunity Window | `src/worldcup_campaign/opportunity_window.py` | 剩余比赛/窗口计算 |
| Calendar Runner | `src/worldcup_campaign/calendar_runner.py` | 日历预览报告生成 |

### 日历/赛程数据

赛程基于 2026 世界杯官方信息：

- **48 队，12 组，每组 4 队**
- **104 场比赛**（72 小组 + 32 淘汰赛）
- 小组前两名 + 8 个成绩最好的小组第三 → 32 强
- 淘汰赛：R32 → R16 → 八强 → 半决赛 → 三四名 → 决赛
- 赛期：2026-06-11 至 2026-07-19

数据文件：
- `data/seed/worldcup_2026_match_registry.json` — 104 场完整赛程
- `data/seed/worldcup_2026_groups.json` — 12 个小组球队（placeholder）
- `data/seed/worldcup_2026_venues.json` — 16 个比赛场馆
- `config/worldcup_stage_map.json` — 11 个赛事阶段定义
- `config/worldcup_calendar_policy.json` — 赛程参数

> **注意：** 淘汰赛阶段球队为 placeholder（TBD），因为小组赛结果决定对阵。未来 Round N 将接入真实赛果更新。

---

## 安全边界

系统强制以下安全边界，写入代码和测试：

```text
real_bet_execution = false
auto_betting = false
external_betting_api_allowed = false
real_money_instruction_allowed = false
campaign_analysis_only = true
daily_max_deploy_ratio <= 0.5
reserve_min_ratio >= 0.5
```

任何安全开关为 `true` 或超出比例限制时，系统直接 fail。

---

## 如何运行测试

```bash
cd worldcup_campaign_agent
python -m pytest tests -v
```

或使用 Makefile：

```bash
make test
```

---

## 如何运行 Foundation Dry-Run (Round 1)

```bash
python scripts/run_campaign_foundation.py --bankroll 100 --windows-left 40 --json
```

---

## 如何运行 Calendar Preview (Round 2)

```bash
# 开幕日
python scripts/run_calendar_preview.py --date 2026-06-11 --json

# 小组赛第三轮
python scripts/run_calendar_preview.py --date 2026-06-24 --json

# 决赛日
python scripts/run_calendar_preview.py --date 2026-07-19 --json
```

输出：
- JSON 至 stdout (with `--json`)
- `reports/generated/calendar_preview.json`
- `reports/generated/calendar_preview.md`

---

## 当前暂未实现内容

- 真实赛程数据 API 接入（使用 seed 数据）
- 球队概率模型（Single Match Probability Engine）
- 真实赔率抓取
- 每日完整策略（Daily Unified Strategy Builder）
- 任何真实下注执行功能
- 赛后结果输入（Post-Match State Updater）
- EV 排序与策略选优
- 淘汰赛真实对阵更新

---

## 下一轮建议

Round 3: Daily Unified Strategy v1 — 将 Round 1 的本金状态机与 Round 2 的今日比赛 slate 连接起来，生成"唯一一套当日资金桶策略骨架"。

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
  data/
    seed/
      worldcup_2026_match_registry.json
      worldcup_2026_groups.json
      worldcup_2026_venues.json
  schemas/
    match.schema.json
    group.schema.json
    stage.schema.json
    calendar_preview.schema.json
  src/
    worldcup_campaign/
      __init__.py
      policy.py
      bankroll_state.py
      market_registry.py
      odds_math.py
      target_math.py
      runner.py
      stage_mapper.py
      match_registry.py
      calendar_engine.py
      opportunity_window.py
      calendar_runner.py
  scripts/
    run_campaign_foundation.py
    run_calendar_preview.py
  tests/
    __init__.py
    conftest.py
    test_policy.py
    test_bankroll_state.py
    test_market_registry.py
    test_odds_math.py
    test_target_math.py
    test_runner_foundation.py
    test_stage_mapper.py
    test_match_registry.py
    test_calendar_engine.py
    test_opportunity_window.py
    test_calendar_runner.py
  reports/
    generated/
      .gitkeep
```