# WorldCup Campaign Strategy Agent

涓栫晫鏉叏璧涚▼绛栫暐瑙勫垝绯荤粺 鈥?鐢ㄤ簬鍒嗘瀽 2026 骞翠笘鐣屾澂 104 鍦烘瘮璧涘強闀垮懆鏈熷競鍦猴紝浠ュ垵濮嬫湰閲?100銆佺洰鏍囨湰閲?1,000,000銆佹瘡鏃ユ渶澶т娇鐢ㄥ綋鍓嶆湰閲?50% 涓?campaign policy锛岃緭鍑哄敮涓€姣忔棩缁熶竴绛栫暐銆?
> **娉ㄦ剰锛氭湰绯荤粺鍙仛 campaign analysis / simulation / strategy planning锛屼笉鍋氱湡瀹炰笅娉ㄦ墽琛岋紝涓嶆帴浠讳綍鐪熷疄涓嬫敞 API锛屼笉鐧诲綍浠讳綍鎶曟敞骞冲彴锛屼笉鎵胯鐩堝埄銆?*

---

## 椤圭洰瀹氫綅

杩欎笉鏄?姣忓ぉ涓存椂鎵句竴涓や釜楂樿禂涓嬫敞鐐?锛岃€屾槸涓€涓?*涓栫晫鏉叏璧涚▼ Campaign Strategy Engine**锛?
- 璧涘墠鐢熸垚 104 鍦烘垬褰瑰湴鍥?- 姣旇禌鏈熼棿鏍规嵁鏈噾鐘舵€併€佽禌绋嬮樁娈点€佽禂鐜囧彉鍖栥€佸凡鍙戠敓璧涙灉鍜屾湭缁撶畻闀垮懆鏈熶粨浣嶏紝杈撳嚭鍞竴涓€濂楀綋鏃ョ瓥鐣ョ粍鍚?- 鏍稿績浼樺寲鐩爣锛氭渶澶у寲杈炬垚鐩爣姒傜巼锛岃€屼笉鏄崟绾渶澶у寲鍗曠瑪 EV

---

## 涓轰粈涔堟瘡澶╁彧杈撳嚭涓€濂楃瓥鐣ワ紵

鏈郴缁熸槸 **Campaign Strategy Agent**锛屼笉鏄笅娉ㄦ帹鑽愬櫒锛?
- 姣忔棩杈撳嚭鐨勬槸璧勯噾妗堕鏋?+ 绛栫暐鏍囩锛屼笉鍖呭惈鍏蜂綋姣旇禌鎺ㄨ崘
- 涓嶆彁渚涘涓簰鏂ユ柟妗堬紙閭ｆ槸鎷嶈剳琚嬶級锛岃€屾槸鎻愪緵绮惧噯鐨勪竴鏉＄瓥鐣ヨ矾寰?- 璧涘悗鏍规嵁瀹為檯缁撴灉鑷姩鍒囨崲鍒伴璁惧垎鏀矾寰?- 绛栫暐楠ㄦ灦 = Reserve/Core/Edge/Attack/Futures 浜斾釜妗?+ 瀵瑰簲甯傚満绫诲埆

---

## Round 1 宸插畬鎴愭ā鍧楋紙璧勯噾鍦板熀锛?
| 妯″潡 | 鏂囦欢 | 鍔熻兘 |
|------|------|------|
| Campaign Policy Engine | `policy.py` | 鏈噾/鐩爣/涓婇檺瀹氫箟涓庢牎楠?|
| Bankroll State Machine | `bankroll_state.py` | S0-S7 鐘舵€佸垎绫伙紝bucket 鍒嗛厤 |
| Market Universe Registry | `market_registry.py` | 20 绉嶇帺娉曟敞鍐屼笌 bucket 鏌ヨ |
| Odds / EV Engine | `odds_math.py` | 闅愬惈姒傜巼銆佸幓姘淬€丒V銆佷覆鍏宠绠?|
| Target Math | `target_math.py` | 鐩爣鍊嶇巼銆佹瘡绐楀彛鎵€闇€澧為暱銆佺揣杩害 |
| Foundation Runner | `runner.py` | 鍩虹 dry-run 鎵ц鍣?|

## Round 2 宸插畬鎴愭ā鍧楋紙璧涚▼鏃ュ巻锛?
| 妯″潡 | 鏂囦欢 | 鍔熻兘 |
|------|------|------|
| Stage Mapper | `stage_mapper.py` | 鏃ユ湡鈫掗樁娈垫槧灏?|
| Match Registry | `match_registry.py` | 104 鍦烘瘮璧涘姞杞戒笌鏌ヨ |
| Calendar Engine | `calendar_engine.py` | 缁勫悎璧涚▼+姣旇禌+鏀跨瓥鐨勫紩鎿?|
| Opportunity Window | `opportunity_window.py` | 鍓╀綑姣旇禌/绐楀彛璁＄畻 |
| Calendar Runner | `calendar_runner.py` | 鏃ュ巻棰勮鎶ュ憡 |

## Round 3 鏂板妯″潡锛堟瘡鏃ョ粺涓€绛栫暐 v1锛?
| 妯″潡 | 鏂囦欢 | 鍔熻兘 |
|------|------|------|
| Strategy Profile Selector | `strategy_profile.py` | 鍩轰簬 stage + bankroll state 閫夋嫨椋庨櫓绛栫暐 |
| Match Strategy Labeler | `match_strategy_labeler.py` | 缁欐瘡鍦烘瘮璧涙墦绛栫暐鏍囩锛堥潪涓嬫敞寤鸿锛?|
| Strategy Allocator | `strategy_allocator.py` | 璧勯噾妗跺垎閰嶅埌鍙敤甯傚満绫诲埆 |
| Scenario Preview | `scenario_preview.py` | 鍏ㄤ腑/鍏ㄥけ/閮ㄥ垎涓瓑鎯呮櫙鎶曞奖 |
| Daily Strategy Engine | `daily_strategy.py` | 鏁村悎 R1+R2+R3 鐨勪富寮曟搸 |
| Daily Strategy Runner | `daily_strategy_runner.py` | 鏃ユ姤鐢熸垚 |

### 浜斾釜璧勯噾妗剁殑鍚箟

| 妗?| 鐢ㄩ€?| 椋庨櫓绛夌骇 |
|----|------|----------|
| **Reserve** | 淇濈暀鐜伴噾锛屼笉鍙備笌閮ㄧ讲锛堚墺50%鏈噾锛?| 闆堕闄?|
| **Core** | 浣庨闄╅珮纭畾鎬у競鍦猴紙1X2銆乨ouble chance锛?| 浣?|
| **Edge** | 涓瓑椋庨櫓浠峰€煎競鍦猴紙璁╃悆銆佸ぇ灏忕悆銆?涓?锛?| 涓?|
| **Attack** | 楂樿禂鐜囨満浼氾紙姣斿垎銆?涓?銆?涓?锛?| 楂?|
| **Futures** | 闀垮懆鏈熶粨浣嶏紙鏅嬬骇銆佸啝浜氬啗銆侀噾闈达級 | 闀挎湡 |

### Match Label 璇存槑

Match label 鏄?*绛栫暐鍊欓€夋爣绛?*锛屼笉鏄笅娉ㄥ缓璁細

- `high_confidence_core` 鈥?閫傚悎 Core 妗剁殑浣庨闄╂瘮璧?- `value_edge` 鈥?鏈変环鍊肩┖闂寸殑 Edge 妗舵瘮璧?- `high_odds_attack` 鈥?楂樿禂鐜?Attack 鍊欓€?- `group_decider` 鈥?鍑虹嚎鍏抽敭鎴?- `knockout_high_stakes` 鈥?娣樻卑璧涢珮鍏虫敞搴?- `championship_match` 鈥?鍐宠禌/鍗婂喅璧涚骇鍒?- `opening_match` 鈥?寮€骞?棣栬疆楂樹笉纭畾鎬?- `futures_position` 鈥?閫傚悎闀垮懆鏈熸姇鍏?
### Scenario Preview 璇存槑

Scenario preview 鏄?**placeholder projection**锛堝崰浣嶆€ф儏鏅姇褰憋級锛屼笉鏄娴嬫垨鎵胯锛?- `all_miss` 鈥?鍏ㄩ儴澶辫触鍚庢湰閲戠姸鎬?- `all_hit` 鈥?鍏ㄩ儴鍛戒腑鍚庢湰閲戠姸鎬?- `attack_hit` 鈥?Attack 妗跺崟鐙懡涓?- `partial_hit` 鈥?Core+Edge 鍛戒腑

---

## 瀹夊叏杈圭晫

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

## 濡備綍杩愯

```bash
# 鍏ㄩ儴娴嬭瘯
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

杈撳嚭鏂囦欢锛?- `reports/generated/foundation_preview.{json,md}`
- `reports/generated/calendar_preview.{json,md}`
- `reports/generated/daily_strategy_preview.{json,md}`

---

## 褰撳墠鏆傛湭瀹炵幇

1. 鏆傛湭鎺ョ湡瀹炶禂鐜?2. 鏆傛湭鎺ョ湡瀹炵悆闃熷己寮辨ā鍨?3. 鏆傛湭鍋?EV 鎺掑簭
4. 鏆傛湭杈撳嚭鍏蜂綋姣旇禌鍊欓€夐€夐」锛堝"涔?A 闃熻儨"锛?5. 鏆傛湭鍋氱湡瀹?stake 鍒嗛厤鍒板叿浣撴瘮璧?6. 鏆傛湭澶勭悊璧涘悗缁撶畻
7. 鏆傛湭鎵ц浠讳綍鐪熷疄涓嬫敞鍔熻兘

---

## 涓嬩竴杞缓璁?
Round 5: Mock Odds / Odds Snapshot + EV Ranking v1 — 让概率第一次和赔率结合，筛选有理论价值的市场。
---

## 椤圭洰缁撴瀯

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