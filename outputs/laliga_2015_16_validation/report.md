# New historical test: La Liga 2015/16

Source: [StatsBomb Open Data](https://github.com/statsbomb/open-data). All 380 matches downloaded and checked, 20 teams with 19 home and 19 away fixtures each. Season chosen for coverage before evaluating the pattern.

Saved 10550 player appearances, including exclusions. 300 fixtures passed the prior-team-history requirements. Rules: home-main-shooter-v1 unchanged.

| Version | Whole season | Before Jan 2016 | Jan 2016 onward |
|---|---:|---:|---:|
| full_pattern | 59/70 (84.3%) | 22/27 (81.5%) | 37/43 (86.0%) |
| benchmark | 206/273 (75.5%) | 69/89 (77.5%) | 137/184 (74.5%) |

The original MLS comparison was 150/185 (81.1%) for the full pattern and 523/660 (79.2%) for the benchmark. These results must not be pooled as if leagues/providers were identical.

The benchmark is consistent HOME main shooters, with the same team-history eligibility, without requiring the stronger-home/shooting conditions. The full pattern is a subset, not an independent comparison group.

## Limits

- Historical external-dataset test, not a live profitability test.
- Different provider and older era: StatsBomb shots are counted from event data; blocked shots count, own goals do not.
- All player appearances saved; unused substitutes are not player appearances. Zero shots means no shot events in a downloaded complete match.
- Minutes use the existing adapter: merged lineup intervals rounded up and capped at 90; stoppage time not added. This differs from some provider minutes.
- Published kickoff clock has no timezone; adapter attaches UTC without claiming verified UTC. A >24h history buffer is retained.
- Lineup-time selection assumes recorded starters known; historical publication availability is not certified.
- The season was chosen for complete coverage before inspecting its pattern results. No threshold tuning. No odds/profit calculation.

## Files

- all_samples.json: every player appearance, result, selection flags and exclusion reasons.
- qualifying_picks.json: every qualifying benchmark/full-pattern selection with lagged features.
- weekly_results.json: every calendar week.
- normalized_matches.json: all normalized fixture/player records.
- raw/: all downloaded events, lineups and match-list JSON, gzip compressed.
- manifest.json: source attribution, rules, coverage, hashes and limitations.
