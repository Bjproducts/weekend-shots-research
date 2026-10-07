# Weekend Shots Research

Research and prospective shadow-testing system for football player total-shots selections.

The workflow ranks match environments first, then evaluates confirmed home starters for:

- Plan A: consistent 2+ shots candidates.
- Plan B: Plan A plus at least 3.0 prior average shots and 80 prior average minutes.
- Experimental 3+ shots ranking, kept separate from the validated 2+ target.

The repository contains the analysis code, frozen test plans, compact result files, dashboards, and the prospective shadow-test ledger. Large downloaded source caches and reproducible intermediate datasets are intentionally excluded from Git.

Start with [the complete project state](outputs/README.md). Useful dashboards include:

- [Combined ranked Plan B backtest](outputs/ranked_plan_b_combined_backtest/index.html)
- [Plan B 3+ reranking experiment](outputs/plan_b_top3_three_shots_reranked/index.html)
- [Prospective 10 October shadow test](outputs/shadow_testing/2026-10-10/index.html)

## Important limitations

- Historical hit rates are descriptive and do not guarantee future results.
- Historical starting lineups are generally treated as if known before kickoff.
- Hypothetical fixed odds are not historical market prices or verified profit.
- Possible-lineup candidates are provisional and are not official prospective selections.
- Immutable prospective snapshots, confirmed-lineup locks, and settlements must not be overwritten.

