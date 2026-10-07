# Home strength → main shooter: first historical test

Question: does a stronger home team with a favourable shooting matchup improve its main shooters’ 2+ shots hit rate?

## Finding

The full environment plus recent minutes and 4/5 consistency produced 150/185 hits (81.1%); later matches were 46/57 (80.7%). The environment identified home shot dominance in 118/160 matches (73.8%), versus 62.6% across eligible home sides.

However, consistent main shooters WITHOUT the environment filter hit 152/184 (82.6%) in later matches. The environment’s extra benefit beyond player consistency is therefore unproven. Keep both versions for a fresh forward check; do not advertise an established 81% win rate.

Eligible fixtures: 665. Competitions: {'MLS': 665}. Later-match check starts 2025-10-26 (last 30% of eligible calendar dates).

| Filter | Earlier matches | Later matches | Overall |
|---|---:|---:|---:|
| All eligible home starters | 1336/4482 (29.8%) | 484/1663 (29.1%) | 1820/6145 (29.6%) |
| Top 2 home shooters (baseline) | 644/968 (66.5%) | 253/362 (69.9%) | 897/1330 (67.4%) |
| Top 2 + stronger home team | 231/332 (69.6%) | 95/130 (73.1%) | 326/462 (70.6%) |
| Top 2 + full home environment | 164/234 (70.1%) | 65/86 (75.6%) | 229/320 (71.6%) |
| Full environment + recent minutes >=70 | 155/218 (71.1%) | 63/82 (76.8%) | 218/300 (72.7%) |
| Full environment + minutes >=70 + 4/5 recent hits | 104/128 (81.2%) | 46/57 (80.7%) | 150/185 (81.1%) |
| Top 2 + minutes >=70 + 4/5 hits WITHOUT environment filter | 371/476 (77.9%) | 152/184 (82.6%) | 523/660 (79.2%) |

## Does the home team actually take more shots?

| Environment | All matches | Later matches |
|---|---:|---:|
| all_eligible | 416/665 (62.6%) | 103/181 (56.9%) |
| stronger | 161/231 (69.7%) | 39/65 (60.0%) |
| full_environment | 118/160 (73.8%) | 32/43 (74.4%) |

## Fixed definitions

- Stronger: higher season-to-date points per game AND higher last-five points per game than the away side; at least eight earlier matches per side, within the same competition and season.
- Shooting matchup: home side averages at least 12 shots in its last up-to-five home matches; away side concedes at least 12 in its last up-to-five away matches. Minimum three venue matches each. Home projection (home shots + away conceded)/2 must exceed the analogous away projection. These are simple historical proxies, not a trained forecast.
- Main shooters: top two of the recorded home starters with five earlier starts for that team/competition within 180 days, ranked by last-five average total shots; prior shot share breaks ties, then player ID. Players without five known shot counts are unranked. This ranks eligible confirmed starters, not an inferred whole squad.
- Minutes filter uses prior starts only. Consistency means 2+ shots in at least four of those five earlier starts. No current-match minutes, score, shot share or shot totals select candidates.
- All features use history more than 24 hours before kickoff. Current starting status is assumed known at lineup time. Each player-match counts once; two candidates in one match are correlated.

## Limits

- This tests the separate saved provider database, not the undated ticket sample or its 79.3% selected-history rate. Replacement reconciliation remains unchanged: 12 provisional original-player totals and three unresolved players.
- Season form means the available saved results, not a independently verified complete league table. Coverage is strongly MLS-weighted; sparse other leagues may fail eligibility.
- Later data is a retrospective stability check, not an untouched prospective trial. Rules were specified before running this script; no threshold sweep was performed. Known completion/publication timestamps are absent, so exact live data availability is not certified.
- Missing outcomes are excluded and counted in JSON; conflicting team totals are treated as unknown. No profit claim: prices and betting returns were not tested.
- A high percentage on a small subset is a hypothesis, not a proven win rate. JSON includes counts, fixture counts and descriptive Wilson intervals; those intervals do not account for within-player/fixture dependence.

Detailed per-player features/outcomes and full counts: home_environment_pattern_test.json. Reproduce: python work/test_home_pattern.py.
