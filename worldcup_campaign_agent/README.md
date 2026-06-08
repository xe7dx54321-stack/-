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

本轮 (Campaign Foundation & Safety Boundary v1) 完成以下模块：

| 模块 | 文件 | 功能 |
|------|------|------|
| Campaign Policy Engine | `src/worldcup_campaign/policy.py` | 本金/目标/上限定义与校验 |
| Bankroll State Machine | `src/worldcup_campaign/bankroll_state.py` | S0-S7 状态分类，bucket 分配 |
| Market Universe Registry | `src/worldcup_campaign/market_registry.py` | 20 种玩法注册与 bucket 查询 |
| Odds / EV Engine | `src/worldcup_campaign/odds_math.py` | 隐含概率、去水、EV、串关计算 |
| Target Math | `src/worldcup_campaign/target_math.py` | 目标倍率、每窗口所需增长、紧迫度 |
| Foundation Runner | `src/worldcup_campaign/runner.py` | 基础 dry-run 执行器 |
| CLI Entry | `scripts/run_campaign_foundation.py` | 命令行入口 |

配置文件：

- `config/campaign_policy.json` — campaign 政策
- `config/bankroll_states.json` — S0-S7 本金状态
- `config/market_universe.json` — 20 种玩法注册

---

## 安全边界

系统强制以下安全边界，写入代码和测试：

```text
real_bet_execution = false
auto_betting = false
external_betting_api_allowed = false
real_money_instruction_allowed = false
campaign_analysis_only = true
daily_max_deploy_ratio ≤ 0.5
reserve_min_ratio ≥ 0.5
```

任何安全开关为 `true` 或超出比例限制时，系统直接 fail。

系统可以输出：模拟部署金额、理论赔率、模型概率、EV、目标贡献、本金状态。

系统不可输出或实现：真实下注 API、自动提交下注、登录博彩账户、绕过平台限制、保证盈利、稳赚表述。

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

## 如何运行 Foundation Dry-Run

```bash
cd worldcup_campaign_agent
python scripts/run_campaign_foundation.py --bankroll 100 --windows-left 40 --json
```

输出：
- JSON 至 stdout
- `reports/generated/foundation_preview.json`
- `reports/generated/foundation_preview.md`

---

## 当前暂未实现内容

本轮 (Round 1) 范围控制，以下内容**暂不实现**：

- 真实赛程数据接入（World Cup Calendar Engine）
- 球队概率模型（Single Match Probability Engine）
- 真实赔率抓取
- 每日完整策略（Daily Unified Strategy Builder）
- 任何真实下注执行功能
- 锦标赛路径模拟（Tournament Path Simulator）
- 策略树（Campaign Strategy Tree）
- 赛后状态更新（Post-Match State Updater）

---

## 下一轮建议

Round 2: World Cup Calendar & Match Registry v1

- 实现 2026 世界杯 48 队、104 场比赛的赛程引擎
- 小组赛阶段管理
- 比赛数据模型（球队、时间、场地）
- 赛程阶段识别（group/round_of_32/round_of_16/quarter_final/semi_final/final）

---

## 项目结构

```
worldcup_campaign_agent/
  README.md
  Makefile
  pyproject.toml
  config/
    campaign_policy.json
    bankroll_states.json
    market_universe.json
  src/
    worldcup_campaign/
      __init__.py
      policy.py
      bankroll_state.py
      market_registry.py
      odds_math.py
      target_math.py
      runner.py
  scripts/
    run_campaign_foundation.py
  tests/
    __init__.py
    test_policy.py
    test_bankroll_state.py
    test_market_registry.py
    test_odds_math.py
    test_target_math.py
    test_runner_foundation.py
  reports/
    generated/
      .gitkeep
```
