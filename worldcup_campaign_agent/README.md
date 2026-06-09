# WorldCup Campaign Strategy Agent

娑撴牜鏅弶顖氬弿鐠ф稓鈻肩粵鏍殣鐟欏嫬鍨濈化鑽ょ埠 閳?閻劋绨崚鍡樼€?2026 楠炵繝绗橀悾灞炬緜 104 閸︾儤鐦挧娑樺挤闂€鍨噯閺堢喎绔堕崷鐚寸礉娴犮儱鍨垫慨瀣拱闁?100閵嗕胶娲伴弽鍥ㄦ拱闁?1,000,000閵嗕焦鐦￠弮銉︽付婢堆傚▏閻劌缍嬮崜宥嗘拱闁?50% 娑?campaign policy閿涘矁绶崙鍝勬暜娑撯偓濮ｅ繑妫╃紒鐔剁缁涙牜鏆愰妴?
> **濞夈劍鍓伴敍姘拱缁崵绮洪崣顏勪粵 campaign analysis / simulation / strategy planning閿涘奔绗夐崑姘辨埂鐎圭偘绗呭▔銊﹀⒔鐞涘矉绱濇稉宥嗗复娴犺缍嶉惇鐔风杽娑撳鏁?API閿涘奔绗夐惂璇茬秿娴犺缍嶉幎鏇熸暈楠炲啿褰撮敍灞肩瑝閹佃儻顕惄鍫濆焺閵?*

---

## 妞ゅ湱娲扮€规矮缍?
鏉╂瑤绗夐弰?濮ｅ繐銇夋稉瀛樻閹靛彞绔存稉銈勯嚋妤傛绂傛稉瀣暈閻?閿涘矁鈧本妲告稉鈧稉?*娑撴牜鏅弶顖氬弿鐠ф稓鈻?Campaign Strategy Engine**閿?
- 鐠ф稑澧犻悽鐔稿灇 104 閸︾儤鍨ぐ鐟版勾閸?- 濮ｆ棁绂岄張鐔兼？閺嶈宓侀張顒勫櫨閻樿埖鈧降鈧浇绂岀粙瀣▉濞堢偣鈧浇绂傞悳鍥у綁閸栨牓鈧礁鍑￠崣鎴犳晸鐠ф稒鐏夐崪灞炬弓缂佹挾鐣婚梹鍨噯閺堢喍绮ㄦ担宥忕礉鏉堟挸鍤崬顖欑娑撯偓婵傛缍嬮弮銉х摜閻ｃ儳绮嶉崥?- 閺嶇绺炬导妯哄閻╊喗鐖ｉ敍姘付婢堆冨鏉堢偓鍨氶惄顔界垼濮掑倻宸奸敍宀冣偓灞肩瑝閺勵垰宕熺痪顖涙付婢堆冨閸楁洜鐟?EV

---

## 娑撹桨绮堟稊鍫熺槨婢垛晛褰ф潏鎾冲毉娑撯偓婵傛鐡ラ悾銉吹

閺堫剛閮寸紒鐔告Ц **Campaign Strategy Agent**閿涘奔绗夐弰顖欑瑓濞夈劍甯归懡鎰珤閿?
- 濮ｅ繑妫╂潏鎾冲毉閻ㄥ嫭妲哥挧鍕櫨濡楀爼顎囬弸?+ 缁涙牜鏆愰弽鍥╊劮閿涘奔绗夐崠鍛儓閸忚渹缍嬪В鏃囩閹恒劏宕?- 娑撳秵褰佹笟娑橆樋娑擃亙绨伴弬銉︽煙濡楀牞绱欓柇锝嗘Ц閹峰秷鍓崇悮瀣剁礆閿涘矁鈧本妲搁幓鎰返缁儳鍣惃鍕閺夛紕鐡ラ悾銉ㄧ熅瀵?- 鐠ф稑鎮楅弽瑙勫祦鐎圭偤妾紒鎾寸亯閼奉亜濮╅崚鍥ㄥ床閸掍即顣╃拋鎯у瀻閺€顖濈熅瀵?- 缁涙牜鏆愭銊︾仸 = Reserve/Core/Edge/Attack/Futures 娴滄柧閲滃?+ 鐎电懓绨茬敮鍌氭簚缁鍩?
---

## Round 1 瀹告彃鐣幋鎰侀崸妤嬬礄鐠у嫰鍣鹃崷鏉跨唨閿?
| 濡€虫健 | 閺傚洣娆?| 閸旂喕鍏?|
|------|------|------|
| Campaign Policy Engine | `policy.py` | 閺堫剟鍣?閻╊喗鐖?娑撳﹪妾虹€规矮绠熸稉搴㈢墡妤?|
| Bankroll State Machine | `bankroll_state.py` | S0-S7 閻樿埖鈧礁鍨庣猾浼欑礉bucket 閸掑棝鍘?|
| Market Universe Registry | `market_registry.py` | 20 缁夊秶甯哄▔鏇熸暈閸愬奔绗?bucket 閺屻儴顕?|
| Odds / EV Engine | `odds_math.py` | 闂呮劕鎯堝鍌滃芳閵嗕礁骞撳娣偓涓扸閵嗕椒瑕嗛崗瀹狀吀缁?|
| Target Math | `target_math.py` | 閻╊喗鐖ｉ崐宥囧芳閵嗕焦鐦＄粣妤€褰涢幍鈧棁鈧晶鐐烘毐閵嗕胶鎻ｆ潻顐㈠ |
| Foundation Runner | `runner.py` | 閸╄櫣顢?dry-run 閹笛嗩攽閸?|

## Round 2 瀹告彃鐣幋鎰侀崸妤嬬礄鐠ф稓鈻奸弮銉ュ坊閿?
| 濡€虫健 | 閺傚洣娆?| 閸旂喕鍏?|
|------|------|------|
| Stage Mapper | `stage_mapper.py` | 閺冦儲婀￠埆鎺楁▉濞堝灚妲х亸?|
| Match Registry | `match_registry.py` | 104 閸︾儤鐦挧娑樺鏉炴垝绗岄弻銉嚄 |
| Calendar Engine | `calendar_engine.py` | 缂佸嫬鎮庣挧娑氣柤+濮ｆ棁绂?閺€璺ㄧ摜閻ㄥ嫬绱╅幙?|
| Opportunity Window | `opportunity_window.py` | 閸撯晙缍戝В鏃囩/缁愭褰涚拋锛勭暬 |
| Calendar Runner | `calendar_runner.py` | 閺冦儱宸绘０鍕潔閹躲儱鎲?|

## Round 3 閺傛澘顤冨Ο鈥虫健閿涘牊鐦￠弮銉х埠娑撯偓缁涙牜鏆?v1閿?
| 濡€虫健 | 閺傚洣娆?| 閸旂喕鍏?|
|------|------|------|
| Strategy Profile Selector | `strategy_profile.py` | 閸╄桨绨?stage + bankroll state 闁瀚ㄦ搴ㄦ珦缁涙牜鏆?|
| Match Strategy Labeler | `match_strategy_labeler.py` | 缂佹瑦鐦￠崷鐑樼槷鐠ф稒澧︾粵鏍殣閺嶅洨顒烽敍鍫ユ姜娑撳鏁炲楦款唴閿?|
| Strategy Allocator | `strategy_allocator.py` | 鐠у嫰鍣惧璺哄瀻闁板秴鍩岄崣顖滄暏鐢倸婧€缁鍩?|
| Scenario Preview | `scenario_preview.py` | 閸忋劋鑵?閸忋劌銇?闁劌鍨庢稉顓犵搼閹懏娅欓幎鏇炲 |
| Daily Strategy Engine | `daily_strategy.py` | 閺佹潙鎮?R1+R2+R3 閻ㄥ嫪瀵屽鏇熸惛 |
| Daily Strategy Runner | `daily_strategy_runner.py` | 閺冦儲濮ら悽鐔稿灇 |

### 娴滄柧閲滅挧鍕櫨濡楀墎娈戦崥顐＄疅

| 濡?| 閻劑鈧?| 妞嬪酣娅撶粵澶岄獓 |
|----|------|----------|
| **Reserve** | 娣囨繄鏆€閻滀即鍣鹃敍灞肩瑝閸欏倷绗岄柈銊ц閿涘牃澧?0%閺堫剟鍣鹃敍?| 闂嗗爼顥撻梽?|
| **Core** | 娴ｅ酣顥撻梽鈺呯彯绾喖鐣鹃幀褍绔堕崷鐚寸礄1X2閵嗕龚ouble chance閿?| 娴?|
| **Edge** | 娑擃厾鐡戞搴ㄦ珦娴犲嘲鈧厧绔堕崷鐚寸礄鐠佲晝鎮嗛妴浣搞亣鐏忓繒鎮嗛妴?娑?閿?| 娑?|
| **Attack** | 妤傛绂傞悳鍥ㄦ簚娴兼熬绱欏В鏂垮瀻閵?娑?閵?娑?閿?| 妤?|
| **Futures** | 闂€鍨噯閺堢喍绮ㄦ担宥忕礄閺呭楠囬妴浣稿暆娴滄艾鍟楅妴渚€鍣鹃棃杈剧礆 | 闂€鎸庢埂 |

### Match Label 鐠囧瓨妲?
Match label 閺?*缁涙牜鏆愰崐娆撯偓澶嬬垼缁?*閿涘奔绗夐弰顖欑瑓濞夈劌缂撶拋顕嗙窗

- `high_confidence_core` 閳?闁倸鎮?Core 濡楀墎娈戞担搴棑闂勨晜鐦挧?- `value_edge` 閳?閺堝鐜崐鑲┾敄闂傚娈?Edge 濡楄埖鐦挧?- `high_odds_attack` 閳?妤傛绂傞悳?Attack 閸婃瑩鈧?- `group_decider` 閳?閸戣櫣鍤庨崗鎶芥暛閹?- `knockout_high_stakes` 閳?濞ｆɑ鍗戠挧娑㈢彯閸忚櫕鏁炴惔?- `championship_match` 閳?閸愬疇绂?閸楀﹤鍠呯挧娑氶獓閸?- `opening_match` 閳?瀵偓楠?妫ｆ牞鐤嗘妯圭瑝绾喖鐣鹃幀?- `futures_position` 閳?闁倸鎮庨梹鍨噯閺堢喐濮囬崗?
### Scenario Preview 鐠囧瓨妲?
Scenario preview 閺?**placeholder projection**閿涘牆宕版担宥嗏偓褎鍎忛弲顖涘瑜版唻绱氶敍灞肩瑝閺勵垶顣╁ù瀣灗閹佃儻顕敍?- `all_miss` 閳?閸忋劑鍎存径杈Е閸氬孩婀伴柌鎴犲Ц閹?- `all_hit` 閳?閸忋劑鍎撮崨鎴掕厬閸氬孩婀伴柌鎴犲Ц閹?- `attack_hit` 閳?Attack 濡楄泛宕熼悪顒€鎳℃稉?- `partial_hit` 閳?Core+Edge 閸涙垝鑵?
---

## 鐎瑰鍙忔潏鍦櫕

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

## 婵″倷缍嶆潻鎰攽

```bash
# 閸忋劑鍎村ù瀣槸
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

鏉堟挸鍤弬鍥︽閿?- `reports/generated/foundation_preview.{json,md}`
- `reports/generated/calendar_preview.{json,md}`
- `reports/generated/daily_strategy_preview.{json,md}`

---

## 瑜版挸澧犻弳鍌涙弓鐎圭偟骞?
1. 閺嗗倹婀幒銉ф埂鐎圭偠绂傞悳?2. 閺嗗倹婀幒銉ф埂鐎圭偟鎮嗛梼鐔峰繁瀵鲸膩閸?3. 閺嗗倹婀崑?EV 閹烘帒绨?4. 閺嗗倹婀潏鎾冲毉閸忚渹缍嬪В鏃囩閸婃瑩鈧鈧銆嶉敍鍫濐洤"娑?A 闂冪喕鍎?閿?5. 閺嗗倹婀崑姘辨埂鐎?stake 閸掑棝鍘ら崚鏉垮徔娴ｆ挻鐦挧?6. 閺嗗倹婀径鍕倞鐠ф稑鎮楃紒鎾剁暬
7. 閺嗗倹婀幍褑顢戞禒璁崇秿閻喎鐤勬稉瀣暈閸旂喕鍏?
---

## 娑撳绔存潪顔肩紦鐠?
Round 5: Mock Odds / Odds Snapshot + EV Ranking v1 鈥?璁╂鐜囩涓€娆″拰璧旂巼缁撳悎锛岀瓫閫夋湁鐞嗚浠峰€肩殑甯傚満銆?---

## 妞ゅ湱娲扮紒鎾寸€?
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