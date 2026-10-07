# Fixed A/B validation — Ligue 1 2015/16

Source: [StatsBomb Open Data](https://github.com/statsbomb/open-data). New evaluation matches relative to refinement discovery; NOT a complete season: 377/380 available.

A = original frozen pattern. B = A plus at least 3 average shots and 80 average minutes over the previous five starts. No thresholds changed.

| Check | A: original | B: challenger | B retention |
|---|---:|---:|---:|
| All available matches | 44/55 (80.0%) | 26/29 (89.7%) | 52.7% |
| Only complete earlier scheduled rounds | 24/32 (75.0%) | 14/17 (82.4%) | 53.1% |
| Excluding three most-selected B players | 24/34 (70.6%) | 7/9 (77.8%) | 26.5% |

B minus A: 9.66 percentage points. Approximate paired-week bootstrap 95% interval: [-1.33, 21.3]. Rejected A picks: 18/26 (69.2%).

Saved 10479 player samples, 55 A picks and all B decisions. 297 fixtures had enough prior history.

## Missing fixture pairings

- Troyes vs Bordeaux
- Bastia vs Gazélec Ajaccio
- Saint-Étienne vs Paris Saint-Germain

## Limits

- Partial coverage: three expected fixture pairings absent. Missing match dates/stats are not invented.
- Prior-round sensitivity is conservative: it also removes picks before postponed earlier rounds were played.
- Independent of refinement discovery matches, but same provider and 2015/16 era as other European tests.
- Paired weekly bootstrap accounts for within-week dependence, not all persistent player/team dependence. Interval is approximate.
- Actual starter assumed known; StatsBomb published clock has no timezone offset; history buffer >24h. Historical publication availability not verified.
- Minutes and shots follow the existing StatsBomb adapter. No odds or profit test. No rule promotion or retuning.