# Frozen A/B stress test — Frauen-Bundesliga 2023/24

Source: [StatsBomb Open Data](https://github.com/statsbomb/open-data). Complete 132-match season selected and plan frozen before player-event acquisition.

A is the original rule. B is A plus previous-five-start averages of at least 3 shots and 80 minutes. No threshold changed.

| Check | A: original | B: challenger | B retention |
|---|---:|---:|---:|
| Full season | 15/19 (78.9%) | 3/5 (60.0%) | 26.3% |
| Rounds 1–11 | 3/5 (60.0%) | 1/1 (100.0%) | 20.0% |
| Rounds 12–22 | 12/14 (85.7%) | 2/4 (50.0%) | 28.6% |
| Excluding three most-selected B players | 10/13 (76.9%) | 1/2 (50.0%) | 15.4% |

B minus A: -18.9 points. Paired-week bootstrap 95% interval: [-62.5, 20.0]. A picks rejected by B: 12/14 (85.7%).

Saved all 4,056 appearances, 19 A picks and every B decision; 84 fixtures had sufficient team history.

## Interpretation

Pattern A remained reasonably strong, but Pattern B did not generalise: it retained only five picks, hit three, and removed 14 picks that hit 12 times. This is negative evidence against promoting B over A. It is still a small sample, so it does not prove B is universally harmful.

This is a separate complete league stress test. It tests whether the mechanism travels, but it is not direct men's MLS validation and shares era/provider with the WSL test.

## Limits

- Women's football is a different population; this is not direct proof of a men's MLS betting rate.
- Historical replay, not a prospective trial; actual starters are assumed known at lineup time.
- Same 2023/24 era and StatsBomb provider family as the WSL test, so the two modern stress tests are not fully independent.
- The 132 matches are unused and non-overlapping with all earlier project evaluation matches.
- Historical publication timing and published kickoff timezone are not certified; replay uses the same >24-hour cutoff.
- No odds or profitability test; weekly bootstrap does not remove all player/team dependence; no retuning.
