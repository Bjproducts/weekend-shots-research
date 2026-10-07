# Frozen A/B stress test — FA Women's Super League 2023/24

Source: [StatsBomb Open Data](https://github.com/statsbomb/open-data). Complete 132-match season selected and the plan frozen before player outcomes were replayed.

A is the original environment-first rule. B is A plus previous-five-start averages of at least 3 shots and 80 minutes. Neither rule was changed.

| Check | A: original | B: challenger | B retention |
|---|---:|---:|---:|
| Full season | 23/27 (85.2%) | 13/14 (92.9%) | 51.9% |
| Rounds 1–11 | 7/8 (87.5%) | 4/4 (100.0%) | 50.0% |
| Rounds 12–22 | 16/19 (84.2%) | 9/10 (90.0%) | 52.6% |
| Excluding three most-selected B players | 11/14 (78.6%) | 4/4 (100.0%) | 28.6% |

B minus A was 7.7 percentage points. Paired-week bootstrap 95% interval: [-3.12, 21.43]. A picks rejected by B: 10/13 (76.9%).

Saved all 3,984 player appearances, 27 A picks and every B decision. 84 fixtures had sufficient team history.

## Interpretation

This is another independent dataset and a useful test of whether the mechanism travels, but it is not direct confirmation for men's MLS because the population differs. Treat the result as stress-test evidence, not a guaranteed future rate.

## Limits

- This is women's football: it is an external mechanism/portability stress test, not direct proof of a men's MLS betting rate.
- Historical replay, not a prospective trial; actual starters are assumed known at lineup time.
- Same StatsBomb provider as prior European research, although the 132 matches are unused and non-overlapping.
- The >24-hour history buffer is conservative; historical publication timing and kickoff timezone publication are not certified.
- StatsBomb shot and minutes definitions follow the saved adapter; no odds or profitability test was performed.
- The paired-week bootstrap does not remove all persistent player/team dependence. No threshold was changed after outcomes.
