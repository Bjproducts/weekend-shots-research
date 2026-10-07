# Big-five 2026 early-season carryover backtest

This is a **new early-season variant**, not the original same-season-only model. It fills missing eight-match and five-start history from the immediately previous season under the frozen 180-day, same-team rules.

Coverage: 156 weekend fixtures; 1716 home-starter samples; 31 qualifying environments.

Pattern A: **13/16 (81.2%)**. Pattern B: **2/2 (100.0%)**.

## By weekend

| Weekend | A | B |
|---|---:|---:|
| 2026-08-29 | 1/2 (50.0%) | No picks |
| 2026-09-05 | 3/3 (100.0%) | No picks |
| 2026-09-12 | 7/7 (100.0%) | 1/1 (100.0%) |
| 2026-09-19 | 2/4 (50.0%) | 1/1 (100.0%) |

## By league

| League | A | B |
|---|---:|---:|
| Bundesliga | 3/3 (100.0%) | No picks |
| LaLiga | 2/2 (100.0%) | 1/1 (100.0%) |
| Ligue 1 | 1/1 (100.0%) | No picks |
| Premier League | 4/7 (57.1%) | 1/1 (100.0%) |
| Serie A | 3/3 (100.0%) | No picks |

## Limits

- This is a newly specified early-season variant, not the already validated original formula.
- FotMob is a different provider from StatsBomb and earlier SportsAPI data; definitions require validation.
- Historical market odds are not used; the fixed prices are hypothetical.
- Same-kickoff picks cannot be literally rolled sequentially.
- Current lineups are actual historical starters, so this is a retrospective lineup-time replay.
- UTC fixture dates define the weekend buckets.
- Hit rates describe this sample and are not guaranteed future win rates.
