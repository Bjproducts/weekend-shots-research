# Weekend Shots Research

Research and prospective shadow-testing system for football player total-shots selections.

The workflow ranks match environments first, then evaluates confirmed home starters for:

- Plan A: consistent 2+ shots candidates.
- Plan B: Plan A plus at least 3.0 prior average shots and 80 prior average minutes.
- Experimental 3+ shots ranking, kept separate from the validated 2+ target.

The repository contains the analysis code, frozen test plans, compact result files, dashboards, and the prospective shadow-test ledger. Large downloaded source caches and reproducible intermediate datasets are intentionally excluded from Git.

Start with [the complete project state](outputs/README.md). Useful dashboards include:

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
