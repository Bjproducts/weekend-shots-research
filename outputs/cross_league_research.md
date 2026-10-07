# Broader test and data cleaning

Data source: [StatsBomb Open Data](https://github.com/statsbomb/open-data). Original project feed: [SportsAPI Pro](https://sportsapipro.com/). The configured SportsAPI account reported 100 daily requests and 99 remaining after one connection check. No subscription or quota upgrade was made.

La Liga and Serie A 2015/16 were selected for complete 380-match coverage before their pattern results were computed. The same rule hash was retained from the MLS test. Premier League is the prior external test, not another new sample.

| Dataset | Full pattern | Consistent home shooters | Full pattern excluding 3 most-selected players |
|---|---:|---:|---:|
| Premier League 2015/16 | 73/90 (81.1%) | 222/297 (74.7%) | 53/68 (77.9%) |
| La Liga 2015/16 | 59/70 (84.3%) | 206/273 (75.5%) | 36/47 (76.6%) |
| Serie A 2015/16 | 71/86 (82.6%) | 220/290 (75.9%) | 49/62 (79.0%) |

Cleaning: 31617 accepted player appearances; 0 quarantined. Original records preserved. All 1,140 match records passed starter-count and team/player-shot reconciliation checks.

## Research: concentration and time stability

| League | Distinct selected players | Top-three share of picks | Before Jan 2016 | Jan onward |
|---|---:|---:|---:|---:|
| Premier League 2015/16 | 37 | 24.4% | 30/39 (76.9%) | 43/51 (84.3%) |
| La Liga 2015/16 | 27 | 32.9% | 22/27 (81.5%) | 37/43 (86.0%) |
| Serie A 2015/16 | 38 | 27.9% | 17/21 (81.0%) | 54/65 (83.1%) |

## Interpretation and limits

All three European datasets are 2015/16 StatsBomb, so era/provider effects remain. Leave-top-three-out is exploratory, chosen by selection count, not success. Multiple picks are correlated; no statistical superiority or profitability claim.
The full pattern is a subset of the benchmark. Its higher/lower observed rate is not proof the filter causes improvement. Inspect per-league counts and concentration rather than promoting a universal 80% rate.
Missing values are never turned into zero. Event-derived zeros require full downloaded matches. Regulation minutes are rounded up from merged lineup intervals and capped at 90; publication-time availability is not verified. These limitations are preserved in each season manifest.
Next research should add a different era/provider under the same rules; do not tune thresholds on these results. SportsAPI Pro remains usable but needs a staged quota-bounded download to obtain a full contemporary season.

All cleaned samples and quarantine records: cross_league_clean_samples.zip. Raw evidence, full results and individual picks remain in each season directory/archive.
