# Recent-season validation: acquisition in progress

Bundesliga 2024/25, SportsAPI Pro. 73/306 matches with player data downloaded; 233 remain. Quota remaining at stop: 10. Ten calls reserved.

Coverage: 2024-08-23 through 2024-11-01. 2289 player appearances saved. 73 fixtures passed checks; 0 quarantined. 1 fixtures had enough earlier team history.

| Rule | Partial-batch results |
|---|---:|
| full_pattern | 2/2 (100.0%) |
| benchmark | 2/2 (100.0%) |

Do not compare this small opening-season batch as if it were a completed season. Most of the downloaded matches establish earlier history rather than testing the rule.

## Next action

Resume the cached download after the provider quota resets; 233 matches still need player stats. No future run is scheduled. The complete fixture catalog is already saved.

## Limits

- Daily quota limits acquisition. Never choose matches based on outcome.
- Current data begins at season start; most matches only supply warm-up history.
- Fixture with missing shot counts or ambiguous starters is quarantined from feature stats; raw data and score history retained.
- Team shots are derived sums of player shots, not independently verified team totals.
- Provider currently supplies revised historical data, not certified as-of-publication snapshots.
- Rules unchanged; no profit calculation and no conclusion from small samples.