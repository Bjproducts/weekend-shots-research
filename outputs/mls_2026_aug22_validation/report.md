# August 22–23: pre-match collection shortlist

Pre-match environment audit; player test not yet completed

15 archived weekend fixtures; 5 pass the unchanged overall/recent home-strength condition; 3 pass both team gates with downloaded venue data. These are environments to investigate, NOT player picks.

| Home | Away | Season PPG H/A | Recent PPG H/A | Strength gate |
|---|---|---:|---:|---|
| Charlotte FC | D.C. United | 1.450/1.200 | 1.600/1.200 | needs_lineups_and_previous_starts |
| New York Red Bulls | Chicago Fire FC | 1.250/1.842 | 0.600/1.800 | fails_strength |
| Orlando City SC | Real Salt Lake | 1.050/1.474 | 1.400/0.400 | fails_strength |
| Inter Miami CF | Toronto FC | 1.950/1.050 | 1.600/1.200 | needs_lineups_and_previous_starts |
| CF Montréal | LA Galaxy | 1.000/1.190 | 1.000/1.000 | fails_strength |
| FC Cincinnati | Seattle Sounders FC | 1.500/1.263 | 2.000/0.000 | fails_shooting |
| Nashville SC | Columbus Crew | 2.300/1.000 | 2.000/0.800 | fails_shooting |
| St. Louis City SC | Houston Dynamo FC | 1.500/1.900 | 2.200/3.000 | fails_strength |
| Austin FC | Philadelphia Union | 1.000/1.000 | 1.200/2.600 | fails_strength |
| Vancouver Whitecaps FC | FC Dallas | 1.947/1.650 | 1.000/1.600 | fails_strength |
| Los Angeles FC | Portland Timbers FC | 1.619/1.350 | 1.400/2.000 | fails_strength |
| San Jose Earthquakes | Minnesota United FC | 1.650/1.250 | 0.200/0.600 | fails_strength |
| San Diego FC | Colorado Rapids | 1.200/1.400 | 1.400/2.400 | fails_strength |
| New England Revolution | New York City FC | 1.650/1.300 | 1.400/1.400 | fails_strength |
| Atlanta United FC | Sporting Kansas City | 0.900/0.750 | 1.400/0.800 | needs_lineups_and_previous_starts |

## Venue shooting checks

| Home | Home shots | Away conceded | Home / away proxy | Player/team shot conflicts |
|---|---:|---:|---:|---|
| Charlotte FC | 13.60 | 16.20 | 14.90/12.70 | 0 |
| Inter Miami CF | 18.20 | 14.40 | 16.30/13.60 | 0 |
| FC Cincinnati | 15.60 | 13.20 | 14.40/15.20 | 0 |
| Nashville SC | 11.00 | 11.00 | 11.00/13.00 | 0 |
| Atlanta United FC | 15.60 | 16.00 | 15.80/11.30 | 0 |

## Remaining work

Verify venue shooting history for strength-pass fixtures before requesting player lineups. Failing the fixed strength gate rules out A and B regardless of the target result. Do not download player histories for those fixtures.
For environments passing both gates, collect the home starting XI and verified previous five starts for every eligible home starter. Match stable provider identities and minute conventions. Preserve unknowns. Current-match results were not used in this screen.
The complete weekend backtest remains unfinished. No losses, hits, streaks or win rate have been claimed for this new weekend.

## Collection progress

All three qualifying home starting XIs are saved in target_lineups.json: 33 starter entries. The Flashscore results page showed the same 15 named weekend pairings as the ASA catalogue. Player histories are still pending reconciliation.
overlap_diagnostic.json tests possible reuse of old history using exact full names, same team and kickoff proximity. It is diagnostic, not an approved cross-provider join: opponent/fixture identity still requires checking. It includes substitutes as well as starters; unmatched appearances are not automatically downloads required for the final shortlist.
Initial venue_home.json / venue_away.json requests explicitly set optional boolean parameters to the string false and returned shot counts inconsistent with player totals. They are retained as rejected diagnostic responses. Only venue_full_home.json / venue_full_away.json, omitting those optional filters, are used; all 50 relevant team-game shot sums agree with cached player totals. Do not reuse the rejected responses or infer their exact server-side interpretation.