# Winning-pick research: can we improve the pattern?

**Exploratory, not a proven upgrade.** Compared every existing full-pattern win with every miss; no wins-only success denominator. Bundesliga’s two preliminary picks are excluded.

Baseline: 353/431 (81.9%). Earlier: 249/306 (81.4%); later: 104/125 (83.2%).

| Additional pre-match filter | All picks | Earlier | Later | Picks retained |
|---|---:|---:|---:|---:|
| Top-ranked shooter only | 231/275 (84.0%) | 158/193 (81.9%) | 73/82 (89.0%) | 63.8% |
| Previous five starts: 5/5 hits | 183/212 (86.3%) | 136/160 (85.0%) | 47/52 (90.4%) | 49.2% |
| Prior average shots >=3 | 259/299 (86.6%) | 189/220 (85.9%) | 70/79 (88.6%) | 69.4% |
| Prior average shot share >=25% | 146/166 (88.0%) | 107/122 (87.7%) | 39/44 (88.6%) | 38.5% |
| Prior average minutes >=80 | 305/368 (82.9%) | 223/268 (83.2%) | 82/100 (82.0%) | 85.4% |
| Projected home shots >=16 | 139/162 (85.8%) | 93/109 (85.3%) | 46/53 (86.8%) | 37.6% |
| Projected home shot advantage >=4 | 236/280 (84.3%) | 158/190 (83.2%) | 78/90 (86.7%) | 65.0% |
| Season PPG advantage >=0.5 | 222/260 (85.4%) | 163/187 (87.2%) | 59/73 (80.8%) | 60.3% |
| Prior shots >=3 AND minutes >=80 | 230/263 (87.5%) | 173/199 (86.9%) | 57/64 (89.1%) | 61.0% |
| 5/5 prior hits AND top-ranked shooter | 137/160 (85.6%) | 99/118 (83.9%) | 38/42 (90.5%) | 37.1% |

## Practical findings

Prior shooting involvement is the strongest descriptive lead: winners averaged 3.63 shots per earlier start versus 3.12 for misses; prior shot share averaged 25.1% versus 22.0%. These are associations within our already-selected cohort, not causal effects.
The 25% prior-share filter keeps only 38.5% of picks and improves the pooled rate, but Premier League performance falls to 19/24 (79.2%); its later subset is only 3/5. It is not a universal improvement.
The shots >=3 plus minutes >=80 combination retains more opportunities (61.0%) and reaches 230/263 (87.5%), with 57/64 (89.1%) later. It is a second exploratory candidate, not the winner selected by the earlier-only ranking.
A larger team-strength gap alone looks good earlier but drops to 59/73 (80.8%) later, below the later baseline. Do not tighten that rule just because it sounds plausible.

## Candidate chosen using earlier results only

Prior average shot share >=25%
Highest earlier hit rate with >=80 earlier picks, >=35% of earlier baseline volume, and >=3 earlier leagues; ties use volume then name.

Later check: 39/44 (88.6%), versus baseline 104/125 (83.2%). Discarded later picks: 65/81 (80.2%).
Without the three most-selected players: 117/135 (86.7%). Their share of selected picks was 18.7%.

| League | Baseline overall | Filter overall | Baseline later | Filter later |
|---|---:|---:|---:|---:|
| La Liga | 59/70 (84.3%) | 32/36 (88.9%) | 18/21 (85.7%) | 10/11 (90.9%) |
| MLS | 150/185 (81.1%) | 71/79 (89.9%) | 43/54 (79.6%) | 18/20 (90.0%) |
| Premier League | 73/90 (81.1%) | 19/24 (79.2%) | 20/25 (80.0%) | 3/5 (60.0%) |
| Serie A | 71/86 (82.6%) | 24/27 (88.9%) | 23/25 (92.0%) | 8/8 (100.0%) |

## What winners looked like before kickoff

| Feature | Wins: average | Misses: average |
|---|---:|---:|
| recent_shots | 3.6295 (n=353) | 3.1231 (n=78) |
| recent_share | 0.2509 (n=353) | 0.2195 (n=78) |
| recent_minutes | 85.8153 (n=353) | 83.9974 (n=78) |
| recent_hits | 4.5184 (n=353) | 4.3718 (n=78) |
| home_home_shots | 16.0561 (n=353) | 15.9071 (n=78) |
| away_away_conceded | 15.3719 (n=353) | 14.7624 (n=78) |
| projected_home_shots | 15.714 (n=353) | 15.3347 (n=78) |
| home_ppg | 1.7884 (n=353) | 1.7353 (n=78) |
| away_ppg | 1.1326 (n=353) | 1.166 (n=78) |

## Limitations

- Exploratory re-analysis of already inspected history, NOT an independent holdout or promised future probability.
- Ten predeclared filters, so multiple-comparison/overfitting risk remains. Later results do not choose the discovery winner.
- The last 30% of qualifying calendar dates per league is a stability check; these splits differ from previous reports.
- Only pre-match features select picks; no current shots, minutes, score or realised shot share is used.
- Player/fixture observations are correlated; displayed Wilson intervals are descriptive and ignore clustering.
- Higher rate can mean fewer opportunities; discarded picks and per-league results are reported. No odds or profit calculation.
- European data shares the 2015/16 era/provider. Rules and earlier published results remain unchanged.

Next: keep the original rule as the benchmark and test this candidate unchanged on a genuinely untouched dataset. Do not retrospectively overwrite the baseline or discard its misses.
