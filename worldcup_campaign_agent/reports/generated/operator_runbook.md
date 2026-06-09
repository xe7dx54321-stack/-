# Operator Runbook

## Daily Setup
1. Confirm network_fetch_default_enabled=false
2. Run: python scripts/run_daily_ops_watchdog.py --date <TODAY> --bankroll <BANKROLL> --json
3. If watchdog BLOCKED, STOP and review circuit_breaker
4. If watchdog WARN, review warnings before continuing

## Matchday Workflow
1. python scripts/run_campaign_foundation.py --bankroll <BANKROLL> --windows-left <N> --json
2. python scripts/run_calendar_preview.py --date <TODAY> --json
3. python scripts/run_match_probability_preview.py --date <TODAY> --json
4. python scripts/run_ev_ranking_preview.py --date <TODAY> --bankroll <BANKROLL> --json --synthetic-odds
5. python scripts/run_integrated_daily_strategy.py --date <TODAY> --bankroll <BANKROLL> --json --synthetic-odds
6. python scripts/run_parlay_preview.py --date <TODAY> --bankroll <BANKROLL> --json --synthetic-odds
7. python scripts/run_futures_preview.py --date <TODAY> --bankroll <BANKROLL> --json --synthetic-futures-odds
8. python scripts/run_signal_fusion_preview.py --date <TODAY> --bankroll <BANKROLL> --json
9. python scripts/run_daily_ops.py --date <TODAY> --bankroll <BANKROLL> --json
10. python scripts/run_campaign_dashboard.py --date <TODAY> --bankroll <BANKROLL> --json

## Rest Day Workflow
1. python scripts/run_daily_ops_watchdog.py --date <TODAY> --bankroll <BANKROLL> --mode pre_daily_ops --json
2. python scripts/run_campaign_dashboard.py --date <TODAY> --bankroll <BANKROLL> --json

## Post-Match Settlement
1. Seed results: data/seed/match_results_seed.json
2. python scripts/run_real_data_preview.py --date <TODAY> --bankroll <BANKROLL> --json
3. python scripts/run_postmatch_settlement.py --date <TODAY> --bankroll <BANKROLL> --json
4. python scripts/run_model_calibration_review.py --date <TODAY> --bankroll <BANKROLL> --json

## Human Review Workflow
1. python scripts/run_human_review_workbench.py --date <TODAY> --bankroll <BANKROLL> --json
2. Open reports/generated/human_review_workbench.html
3. Process review items by severity (critical -> high -> medium -> low)
4. Record decisions in data/seed/review_decision_input_example.json
5. Re-run workbench with --decision-file

## Dashboard Check
1. Open reports/generated/campaign_dashboard.html
2. Verify liquid_simulated_bankroll / locked_pending_units / total_campaign_equity
3. Check required_multiplier_liquid and required_multiplier_equity

## Emergency Procedures
- If any runner outputs stake / bet_instruction / bookmaker_account: STOP immediately
- If real_bet_execution=true appears anywhere: STOP and audit all outputs
- If network_fetch_default_enabled is accidentally true: STOP and reset config

## Safety Boundary Check (Daily)
- [ ] network_fetch_default_enabled=false
- [ ] real_bet_execution=false
- [ ] auto_betting=false
- [ ] No stake fields in any output
- [ ] No bookmaker_account in any output
- [ ] All reports have analysis_only=true, simulation_only=true, not_betting_advice=true

> This is a simulation-only system. Not betting advice. No real bets placed. No real money used.
