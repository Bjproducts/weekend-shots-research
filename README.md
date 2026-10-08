# Weekend Shots Research

Research and prospective shadow-testing system for football player total-shots selections.

The workflow ranks match environments first, then evaluates confirmed home starters for:

- Plan A: consistent 2+ shots candidates.
- Plan B: Plan A plus at least 3.0 prior average shots and 80 prior average minutes.
- Experimental 3+ shots ranking, kept separate from the validated 2+ target.

The repository contains the analysis code, frozen test plans, compact result files, dashboards, and the prospective shadow-test ledger. Large downloaded source caches and reproducible intermediate datasets are intentionally excluded from Git.

Start with [the complete project state](outputs/README.md). Useful dashboards include:

- [Prospective captured-price and profit validation](outputs/profit_validation/index.html)
- [Higher-volume v4 prospective profit challenger](outputs/profit_challenger/index.html)
- [Volume-v4 historical assumed-price mechanics replay](outputs/hypothetical_volume_v4_combo_1_5/index.html)
- [Hypothetical v3 combination replay at assumed 1.50](outputs/hypothetical_v3_combo_1_5/index.html)
- [Live four-league Plan B 3+ board for 10 October 2026](outputs/live_plan_b3/2026-10-10/index.html)
- [Combined ranked Plan B backtest](outputs/ranked_plan_b_combined_backtest/index.html)
- [Plan B 3+ reranking experiment](outputs/plan_b_top3_three_shots_reranked/index.html)
- [Prospective 10 October shadow test](outputs/shadow_testing/2026-10-10/index.html)

## Important limitations

- Historical hit rates are descriptive and do not guarantee future results.
- Historical starting lineups are generally treated as if known before kickoff.
- Hypothetical fixed odds are not historical market prices or verified profit.
- Possible-lineup candidates are provisional and are not official prospective selections.
- Immutable prospective snapshots, confirmed-lineup locks, and settlements must not be overwritten.

## Live Plan B 3+ weekend workflow

The operational scanner now covers **MLS, Premier League, Serie A and Bundesliga**. For each active Saturday/Sunday it acquires bounded history first, ranks the top five Tier A/B home environments, builds a possible-XI shortlist, and freezes at most three Plan B candidates for the 3+ shots target.

The frozen candidate ranking is: previous-five 3+ hits, average player share of team shots, average shots, average minutes, environment rank, then player ID. A name remains provisional until FotMob reports a `standard` lineup and the same player is confirmed in the home starting XI before kickoff. Predicted and last-used lineups cannot create official picks, and a rejected top-three name is not replaced after the board is frozen.

For the 10–11 October 2026 run, 606 historical matches were acquired with no normalization failures, 40 weekend fixtures were scanned, five environments were selected and three provisional candidates were frozen. The full integrity suite passes 21/21 checks. There are currently no official picks because confirmed lineups are not yet available.

Reproduce the stages with:

```powershell
python work/sync_live_plan_b3_data.py --weekend 2026-10-10
python work/live_plan_b3.py prepare --weekend 2026-10-10
python work/live_plan_b3.py possible --weekend 2026-10-10
python work/live_plan_b3.py lineups --weekend 2026-10-10
python work/live_plan_b3.py settle --weekend 2026-10-10
python work/live_plan_b3.py dashboard --weekend 2026-10-10
python work/check_live_plan_b3.py --weekend 2026-10-10
```

This makes the process operational and auditable; it does not establish that the experimental 3+ rule is profitable. The board must be prospectively settled before its future hit rate is known.

## Current-season historical replay

The exact weekend engine was retrospectively replayed across every completed current-season Saturday/Sunday through 7 October 2026. The replay used 996 source matches to reconstruct Friday-only information for 428 target fixtures over 24 weekends. It selected no more than five environments and three provisional Plan B candidates each weekend, then used the historical starting XI as the confirmation gate without promoting replacements.

Result: **40/51 3+ shots hits (78.4%)**, with a 95% Wilson interval of **65.4–87.5%**. It produced picks on 22 weekends; **11/22 weekends were completely clean**. The engine produced three official picks on nine weekends and all three hit on **6/9 — 66.7%** of them. The longest individual hit run was 10. The evidence is highly concentrated: MLS supplied 49 of 51 picks, while the young European seasons supplied only two total picks. This is useful retrospective evidence, not a reliable cross-league future rate or proof of profit.

See the [season-to-date replay dashboard](outputs/season_to_date_plan_b3/index.html) and reproduce it with `python work/simulate_season_to_date_plan_b3.py` followed by `python work/check_season_to_date_plan_b3.py`.

### Active consistency ranking (v2)

Candidates are now explicitly restricted to the **home team**. When the highest remaining candidate and other candidates are within **0.5 prior average shots**, the engine prefers the more consistent record: more previous-five 3+ hits, higher five-start shot floor, lower shot standard deviation, more 2+ hits, then shot share and the existing tie-breakers.

This v2 rule changed two selections in the season-to-date replay but left the headline performance unchanged at **40/51 — 78.4%**, with **6/9 clean three-pick weekends**. One historical miss replaced another miss and one hit replaced another hit. Because the rule was requested after inspecting v1, this is an exploratory refinement rather than independent validation. See the [v2 consistency dashboard](outputs/season_to_date_plan_b3_consistency_v2/index.html).

### Active equal-league ranking (v3)

The live engine now gives every active league equal first access: it selects the strongest eligible environment from each league before filling any remaining environment slots. It then ranks the home-only consistency candidates, retains only the strongest candidate from each league, and takes at most three. It never forces a candidate from a league that fails Plan B.

The exploratory season-to-date v3 replay returned **20/23 — 87.0%**, with **18/21 clean active weekends**, but averaged only **1.1 official picks per active weekend** and produced no three-pick weekends. MLS still supplied 20 of 23 picks because it was the only active league for most of the saved period. The higher rate is based on a much smaller, post-result-selected sample and is not independent validation. See the [league-balanced v3 dashboard](outputs/season_to_date_plan_b3_league_balanced_v3/index.html).

## Prospective price-and-profit validation

League-balanced v3 is now frozen for a separate prospective experiment. Historical replays do not count toward it. Official legs enter only from an immutable `standard` confirmed home starting-XI decision. Prices must be exact **Over 2.5 total shots** quotes captured through The Odds API from DraftKings, FanDuel or BetMGM; there is no assumed 1.40 fallback.

Tickets are paper-only kickoff-window combinations. Every leg must be offered by one common bookmaker, and the displayed combination price is the mathematical product of captured leg prices (`derived_product_price`), not a bookmaker parlay quote. The requested 90% bankroll exposure is retained strictly as a stress test. Overlapping paper exposure is flagged non-executable, insolvency is permitted, and nothing in this repository can place a wager.

Initial setup:

```powershell
Copy-Item .env.example .env
# Add THE_ODDS_API_KEY to the local .env; this file is ignored by Git.
python work/profit_validation.py dashboard
python work/test_profit_validation.py -v
```

Run a deterministic cycle for the active weekend:

```powershell
python work/run_profit_collector.py --weekend 2026-10-10
```

After the key is configured, register the local ten-minute watch task if desired:

```powershell
powershell -ExecutionPolicy Bypass -File work/register_profit_collector.ps1
```

The scheduled runner automatically selects the nearest active frozen v3 weekend. It exits immediately unless a frozen candidate is within two hours of kickoff. Watch mode polls at ten-minute intervals and wakes at the exact five-minute freeze boundary. Raw and normalized observations are immutable; the global JSONL ledger is hash-chained and append-only.

Real-money use is not considered until the dashboard gate has all of: 100 prospective official legs, 30 executable combinations, 12 active weekends, at least three represented leagues with no league above 60%, positive executable captured-price paper ROI, positive average closing-line value, more than half of tickets beating the close, and zero unresolved discrepancies. Passing the gate starts a separate safer-staking decision; it never activates betting.

### Separate assumed-odds scenario

A mechanics-only replay applies an assumed 1.50 price to every historical 3+ shots leg while preserving the combo-only, five-minute freeze and 90% paper-stake rules. Historical lineup availability is explicitly assumed at 60 minutes before kickoff because publication timestamps are unavailable. Across 23 v3 official selections, 21 were isolated `no_combo` records and only one two-leg ticket formed. Both legs hit: the assumed 2.25 product changed 100 paper units to 212.50. This one-ticket result is not historical price evidence, cannot measure closing-line value and never enters the prospective activation gate. See the [assumed-odds replay](outputs/hypothetical_v3_combo_1_5/index.html).

## Higher-volume profitability challenger (v4)

Frozen league-balanced v3 remains the unchanged control. The separate v4 challenger keeps the same Tier A/B environments, home-only Plan B gates and consistency ordering, but retains the strongest candidate from each fixture before allowing up to two candidates per league and three in total. Its board is frozen before lineups; failed lineup checks never trigger replacements.

The retrospective structural replay produced **33/38 3+ hits (86.8%)** across 22 active weekends. It is post-result descriptive evidence. Under the same assumed 1.50 and lineup-timing mechanics, only **one two-leg combination** formed; 36 legs were isolated as `no_combo`. That combination won, moving the hypothetical 10% track from 100 to 112.50, the non-recommended 90% stress track from 100 to 212.50, and the separate full-rollover track to **`100 × 1.5² = 225`**. A one-ticket hypothetical sample is not profitability evidence. A loss on the full-rollover track reduces its active balance to zero.

Prospectively, v3 and v4 run in parallel using real captured prices. Each strategy has a separate append-only ledger. A shared immutable quote store prevents the same physical player quote from being collected twice when both strategies select that player. V4 maintains independent 100-unit tracks: fixed 10% is the primary benchmark and 90% remains a stress test. Open stakes are not reserved; excess aggregate exposure is flagged `non_executable_overlap` and excluded from promotion metrics.

The challenger cannot replace v3 until its real-price fixed-10 track has 100 official legs, 30 executable combinations, 12 active weekends, adequate league representation, positive ROI and CLV, more than half of tickets beating the close, maximum drawdown no higher than 25%, and no unresolved discrepancies. Passing only triggers manual review.

```powershell
python work/check_plan_b3_volume_v4.py
python work/check_hypothetical_volume_v4_combo_1_5.py
python work/test_profit_challenger.py -v
python work/profit_challenger.py dashboard
```
