# Phase 2: Mining the selected 2+ shots history

The report contains **150 assessed player–fixture-pairing observations: 119 hits, 31 misses, a 79.3% selected-sample hit rate**. These cover 119 fixture IDs and 95 displayed players. This is a descriptive discovery dataset; no predictive model or outside football information was used.

Source: shots_and_shots_on_target_report.pdf, captured 23 September 2026. Methodology: pp. 1–3. Record-level evidence: pp. 4–39. Every research-table row retains its source page, fixture ID, displayed score, original-player note, ticket references and exceptions.

## Scope and deduplication

The report already consolidates repeated tickets by fixture pairing, displayed player, market, equivalent line and original substituted player. I extracted its 438 match-register groups, selected all 179 Shots / 2+ groups, retained the 119 HIT and 31 MISS groups, and excluded 23 VOID-only and 6 UNKNOWN groups. The alphabetical summary and ticket audit were not added as fresh observations. Shots / 1+, Shots / 3+ and SOT selections do not enter the 2+ sample, even when their statistics reveal whether two shots occurred.

I then checked the stricter key `(fixture ID, displayed player)` among assessed Shots / 2+ groups. All 150 keys were unique, so no additional assessed rows required merging. The 484 ticket references attached to these rows are provenance, not 484 independent observations; 334 references beyond one per record receive no extra weight. References can include void or missing-statistic occurrences.

**Distinct dated matches cannot be established.** Dates were not exposed in the source history; repeated meetings with the same pairing may already have been combined by the report. Fixture IDs identify report pairings, not official match IDs, and ID order is not a verified timeline. Reversed pairings remain separate source IDs. Nothing here establishes that these are 150 distinct dated player-match outcomes.

Mixed-status groups stay assessed when the report supplies a non-void numeric result: 23 retained records also have void occurrences and 7 also have missing-statistic occurrences. A void is not converted to a miss. Displayed numbers are accepted as report evidence, not independently verified official totals or proven full-match statistics. The source also warns that cash-out statistics need not represent outcomes at cash-out time.

Player names and unusual pairings remain exactly as reported. No player was reassigned to a team using outside knowledge. The displayed pairing and score are recorded, but player team, player home/away, date, league, starting status, minutes and tactical role are not inferred.

## Actual-shot distribution

| Actual shots | Observations | Share of 150 |
| --- | --- | --- |
| 0 | 13 | 8.7% |
| 1 | 18 | 12.0% |
| 2 | 32 | 21.3% |
| 3 | 36 | 24.0% |
| 4 | 23 | 15.3% |
| 5+ | 28 | 18.7% |

Exact upper tail: 5 shots = 15; 6 = 5; 7 = 2; 8 = 0; 9 = 3; 10 = 2; 11 = 0; 12 = 1. Total displayed shots = 460; mean = 3.07; median = 3. These describe the selected sample only.

## Every miss, grouped by what is observable

Eighteen misses (58.1% of 31) finished on one shot; thirteen (41.9%) finished on zero. A one-shot near miss describes a threshold shortfall, not its cause. Zero recorded shots does not establish that a player had no opportunities.

The four categories below are mutually exclusive descriptive categories. The report cannot support assigning causal labels such as minutes failure, role failure, team-volume failure, low player share, opponent suppression or normal variance. Those explanations remain unknown for all 31 misses.

| Report-supported category | Misses | Share of misses |
| --- | --- | --- |
| Replacement noted / zero shots | 7 | 22.6% |
| No replacement note / one-shot near miss | 10 | 32.3% |
| Replacement noted / one-shot near miss | 8 | 25.8% |
| No replacement note / zero shots | 6 | 19.4% |

### Replacement noted / zero shots

| Fixture | Pairing / displayed score | Player | Sub for | Shots | PDF page |
| --- | --- | --- | --- | --- | --- |
| F001 | Deportivo A Coruna v Real Betis / 1-1 | Facundo Bernal | Antony | 0 | 5 |
| F038 | Aston Villa v Nottm Forest / 1-2 | Tammy Abraham | Nicolas Jackson | 0 | 4 |
| F064 | Toulouse v Lille / 0-1 | Ayase Ueda | Olivier Giroud | 0 | 7 |
| F096 | Liverpool v Nottm Forest / 2-2 | Rio Ngumoha | Cody Gakpo | 0 | 11 |
| F145 | Genoa v Napoli / 0-2 | Lorenzo Lucca | Rasmus Hojlund | 0 | 10 |
| F167 | Kansas City v St. Louis City SC / 1-1 | Alexandru Matan | Simon Becher | 0 | 5 |
| F170 | Chicago Fire v Portland Timbers / 2-1 | Puso Dithejane | Philip Zinckernagel | 0 | 9 |

### No replacement note / one-shot near miss

| Fixture | Pairing / displayed score | Player | Sub for | Shots | PDF page |
| --- | --- | --- | --- | --- | --- |
| F009 | Leeds v Crystal Palace / 0-0 | Dominic Calvert-Lewin | No note | 1 | 11 |
| F026 | FC Dallas v Austin FC / 0-0 | Petar Musa | No note | 1 | 5 |
| F037 | Chelsea v Hull / 2-2 | Joao Pedro | No note | 1 | 9 |
| F068 | Burnley v Middlesbrough / 1-1 | Will Lankshear | No note | 1 | 4 |
| F074 | Osasuna v Getafe / 1-0 | Ante Budimir | No note | 1 | 6 |
| F087 | Houston Dynamo v San Jose / 0-0 | Guilherme Augusto | No note | 1 | 5 |
| F130 | San Diego FC v Colorado Rapids / 3-0 | Rafael Navarro | No note | 1 | 13 |
| F141 | San Jose v Minnesota Utd / 1-5 | Preston Judd | No note | 1 | 13 |
| F222 | England v Argentina / 1-2 | Harry Kane | No note | 1 | 10 |
| F222 | England v Argentina / 1-2 | Lionel Messi | No note | 1 | 10 |

### Replacement noted / one-shot near miss

| Fixture | Pairing / displayed score | Player | Sub for | Shots | PDF page |
| --- | --- | --- | --- | --- | --- |
| F016 | San Jose v LAFC / 2-2 | Jacob Shaffelburg | Denis Bouanga | 1 | 13 |
| F032 | Liverpool v Fulham / 0-0 | Rio Ngumoha | Bradley Barcola | 1 | 11 |
| F036 | Tottenham v Everton / 0-0 | James Maddison | Omar Marmoush | 1 | 14 |
| F101 | Lille v PSG / 2-2 | Khvicha Kvaratskhelia | Desire Doue | 1 | 6 |
| F132 | LAFC v Portland Timbers / 1-1 | Omir Fernandez | Kristoffer Velde | 1 | 11 |
| F138 | Atletico Madrid v Villarreal / 2-2 | Jose Maria Gimenez | Ademola Lookman | 1 | 8 |
| F146 | Borussia Dortmund v Bayern Munich / 1-2 | Tom Bischof | Luis Diaz | 1 | 8 |
| F166 | Toronto FC v Charlotte FC / 3-3 | Luca De La Torre | Pep Biel | 1 | 7 |

### No replacement note / zero shots

| Fixture | Pairing / displayed score | Player | Sub for | Shots | PDF page |
| --- | --- | --- | --- | --- | --- |
| F061 | Gent v OH Leuven / 1-0 | Josue Vergara | No note | 0 | 5 |
| F064 | Toulouse v Lille / 0-1 | Hakon Arnar Haraldsson | No note | 0 | 7 |
| F069 | Millwall v Wrexham / 0-3 | Joshua Coburn | No note | 0 | 6 |
| F130 | San Diego FC v Colorado Rapids / 3-0 | Marcus Ingvartsen | No note | 0 | 13 |
| F169 | Seattle Sounders v Vancouver Whitecaps / 0-2 | Ryan Gauld | No note | 0 | 13 |
| F176 | San Jose v St. Louis City SC / 1-3 | Timo Werner | No note | 0 | 7 |

## Replacement notes and role stability

| Observable group | Records | Hits | Misses | Hit rate |
| --- | ---: | ---: | ---: | ---: |
| Explicit “Sub for” note | 15 | 0 | 15 | 0.0% |
| No replacement note | 135 | 119 | 16 | 88.1% |

The 15 replacement records involve 14 players; Rio Ngumoha appears twice. They account for 48.4% of all misses while representing 10.0% of the assessed sample. Their totals are seven zeros and eight ones. All 23 void-only and 6 unknown target groups lack replacement notes.

This is a strong descriptive association inside this report. **A stable-role versus disrupted-role comparison is not identifiable:** no note does not prove a stable starting role, and “Sub for” does not establish entry time, minutes, position, lineup changes or the mechanism behind the replacement. There are zero records with an explicitly established stable-role classification.

Khvicha Kvaratskhelia supplies a small within-player contrast: F101, “Sub for Desire Doue”, 1 shot; F168, no replacement note, 4 shots. Different fixtures and unknown minutes prevent attributing this difference to replacement status. Original players’ outcomes elsewhere are not counterfactual outcomes for their replacements.

## Threshold headroom among hits

Headroom is the observed shot count minus 2. It is retrospective and must not be used as a pre-match feature.

| Actual shots among hits | Headroom above 2 | Count | Share of 119 hits |
| --- | --- | --- | --- |
| 2 | 0 | 32 | 26.9% |
| 3 | 1 | 36 | 30.3% |
| 4 | 2 | 23 | 19.3% |
| 5+ | 3+ | 28 | 23.5% |

Of the hits, **87/119 (73.1%) reached 3+ shots** and **51/119 (42.9%) reached 4+**. Exactly two shots accounts for 32/119 (26.9%) hits, so these observations had no surplus above the threshold. Mean actual shots among hits = 3.71; mean observed headroom = 1.71; median headroom = 1.

These facts demonstrate realized clearance in successful records. Conditioning on hits excludes the failures; it does not demonstrate future resilience, an expected shot rate, or a validated margin-of-safety rule.

## Repeated-player performance

Thirty-two players appear in at least two assessed 2+ records, accounting for 87 observations. The other 63 players appear once. The full repeated-player table follows; shot sequences are in fixture-ID order, **not chronological order**. Every rate uses assessed Shots / 2+ observations only.

| Player | N | Hits | Misses | Hit rate | Fixture: shots | Replacement notes |
| --- | --- | --- | --- | --- | --- | --- |
| Alexander Isak | 2 | 2 | 0 | 100.0% | F005: 3; F032: 3 | 0 |
| Ante Budimir | 2 | 1 | 1 | 50.0% | F074: 1; F114: 4 | 0 |
| Antoine Griezmann | 5 | 5 | 0 | 100.0% | F043: 3; F084: 2; F135: 5; F165: 5; F198: 3 | 0 |
| Antony | 2 | 2 | 0 | 100.0% | F093: 6; F108: 4 | 0 |
| Bukayo Saka | 2 | 2 | 0 | 100.0% | F024: 2; F035: 4 | 0 |
| Cavan Sullivan | 3 | 3 | 0 | 100.0% | F014: 2; F090: 3; F172: 6 | 0 |
| Cole Palmer | 2 | 2 | 0 | 100.0% | F037: 3; F076: 4 | 0 |
| Evander Ferreira | 5 | 5 | 0 | 100.0% | F015: 4; F085: 5; F133: 3; F157: 6; F173: 5 | 0 |
| Gonzalo Garcia | 2 | 2 | 0 | 100.0% | F003: 3; F047: 5 | 0 |
| Guilherme Augusto | 2 | 1 | 1 | 50.0% | F087: 1; F175: 3 | 0 |
| Hany Mukhtar | 2 | 2 | 0 | 100.0% | F010: 4; F218: 2 | 0 |
| Heung-Min Son | 4 | 4 | 0 | 100.0% | F016: 2; F044: 4; F132: 9; F178: 4 | 0 |
| Joao Pedro | 3 | 2 | 1 | 66.7% | F037: 1; F076: 5; F113: 4 | 0 |
| Kevin Kelsy | 2 | 2 | 0 | 100.0% | F158: 3; F170: 2 | 0 |
| Khvicha Kvaratskhelia | 2 | 1 | 1 | 50.0% | F101: 1; F168: 4 | 1 |
| Kristoffer Velde | 4 | 4 | 0 | 100.0% | F011: 9; F089: 3; F158: 2; F170: 3 | 0 |
| Lionel Messi | 3 | 2 | 1 | 66.7% | F137: 2; F179: 12; F222: 1 | 0 |
| Lois Openda | 2 | 2 | 0 | 100.0% | F019: 3; F106: 4 | 0 |
| Louis Munteanu | 3 | 3 | 0 | 100.0% | F017: 9; F086: 4; F159: 2 | 0 |
| Mason Greenwood | 2 | 2 | 0 | 100.0% | F078: 3; F151: 5 | 0 |
| Milan Iloski | 5 | 5 | 0 | 100.0% | F014: 2; F039: 3; F090: 7; F142: 2; F172: 5 | 0 |
| Mohamed Salah | 2 | 2 | 0 | 100.0% | F029: 4; F075: 3 | 0 |
| Nicolas Paz | 2 | 2 | 0 | 100.0% | F008: 10; F144: 4 | 0 |
| Oihan Sancet | 2 | 2 | 0 | 100.0% | F023: 2; F049: 3 | 0 |
| Pep Biel | 2 | 2 | 0 | 100.0% | F134: 2; F180: 3 | 0 |
| Petar Musa | 3 | 2 | 1 | 66.7% | F026: 1; F160: 4; F171: 3 | 0 |
| Prince Osei Owusu | 4 | 4 | 0 | 100.0% | F018: 5; F131: 4; F156: 3; F174: 5 | 0 |
| Rafael Navarro | 2 | 1 | 1 | 50.0% | F013: 2; F130: 1 | 0 |
| Rio Ngumoha | 2 | 0 | 2 | 0.0% | F032: 1; F096: 0 | 2 |
| Robert Lewandowski | 4 | 4 | 0 | 100.0% | F010: 3; F041: 3; F165: 4; F170: 4 | 0 |
| Serhou Guirassy | 3 | 3 | 0 | 100.0% | F020: 3; F031: 3; F053: 5 | 0 |
| Simon Becher | 2 | 2 | 0 | 100.0% | F013: 4; F079: 3 | 0 |

Evander Ferreira has 5/5 hits with 4, 5, 3, 6, 5 shots; Prince Osei Owusu has 4/4 with 5, 4, 3, 5; Robert Lewandowski has 4/4 with 3, 3, 4, 4. All their recorded totals exceed two. These are candidates for studying repeat clearance, not established player probabilities. The earlier conversation’s Evander and Son examples were incomplete: the report includes five assessed Evander records and four Son records.

Variation also matters: Joao Pedro has 1, 5, 4 shots (2/3 hits); Petar Musa has 1, 4, 3 (2/3); Lionel Messi has 2, 12, 1 (2/3). A large maximum does not establish a reliable minimum. Rio Ngumoha has 1 and 0 (0/2), both explicitly marked as replacements.

## Other recurring evidence and candidate hypotheses

| Report evidence | Hypothesis to investigate | Data needed before testing |
| --- | --- | --- |
| All 15 replacement-noted records missed; 119/135 without a note hit. | Replacement status or the circumstances behind it may identify a different shot-generation process. | Meaning and timing of replacement, starter/substitute status, expected and actual minutes, tactical role, full sampling of replacement hits and misses. |
| 18/31 misses recorded exactly one shot. | Predictors of repeated attempts may differ from predictors of any attempt. | Minutes, shot timing, player share, team attempts, possession phases and match state; compare one versus two-plus across an unselected sample. |
| 87/119 hits had at least one shot above the threshold; some repeated players consistently cleared two. | A pre-match history of clearance may contain information beyond a simple historical 2+ rate. | Dated prior matches, all eligible selections, role and minutes controls; calculate features strictly before each target match. |
| Some repeated players have both high totals and a one-shot miss. | Context may explain variation within a player that a name-only summary misses. | Same-player observations with opponents, minutes, roles, lineups and team-volume context. |
| Eleven selected records in pairings displayed as 0–0 include six hits and five misses. | Goal outcome alone is an insufficient description of shooting opportunity. | Player-team identity, team attempts and time-varying match state; final score is post-match context, not a pre-match input. |
| Cole Palmer F037 has 3 shots and 0 SOT; Evander F015 has 4 shots and 0 SOT; Preston Judd F141 has 1 shot and 1 SOT. | Total-attempt generation and on-target conversion should remain separate research targets. | Joint shots/SOT observations with shot quality, locations and accuracy context; no pooled labels. |

The 0–0 examples include F032 Isak and Wirtz with 3 each and replacement-noted Ngumoha with 1. This establishes differing player totals within a pairing, but does not establish team membership or player shot share. Two misses in the same fixture likewise cannot prove low team volume because unselected players are absent.

## What is established, and what remains unknown

Established **within the report**: the extracted records and source notes; their threshold outcomes; the 150-record denominator; the distribution, descriptive replacement association, repeated-player summaries and realized headroom. All counts reconcile to the report’s Shots / 2+ summary on p. 3.

Not established: independent dated-match count, actual stable roles, the causes of any miss, population 2+ probability, future hit rate, profitable selection rules, predictive advantage from headroom, or causal effects of replacements. The history contains user-selected players, shared fixtures and repeated players; observations are not assumed independent. Voids and unknowns may be systematically different from assessed records. No inferential significance or model accuracy claim is made.

The next research step is to recover dated event identities and the meaning of replacement notes, then add expected/actual minutes, starts, tactical role, team attempts and player share for both hits and misses. Those fields should remain missing until evidence is available. No outside football data has been added in this phase.

## Research table and field definitions

The complete table below includes all 150 assessed records. The accompanying JSON preserves structured ticket lists and other reported markets for the same player–fixture pairing, plus all 29 exclusions. Other markets are context only and are not added to the denominator.

- Fixture ID/pairing, player, score, original-player note, displayed shots, source page and ticket references: transcribed source fields.
- Hit/miss: source classification, checked against shots >= 2.
- Headroom: derived actual shots minus 2; negative values indicate a shortfall.
- V / ?: counts of void and missing-statistic occurrences within the grouped selection, not extra outcomes.
- No note: absence of a replacement note, not proof of a normal or stable role.
- Date, league, player team, home/away, minutes, start and tactical role: unavailable, explicitly null in JSON.


| Fixture | Pairing | Score | Player | Sub for | Shots | Outcome | Headroom | V / ? | PDF page | Ticket references |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F001 | Deportivo A Coruna v Real Betis | 1-1 | Facundo Bernal | Antony | 0 | MISS | -2 | 0 / 0 | 5 | T001, T002, T003, T004 |
| F003 | Fulham v Man Utd | 1-1 | Bryan Mbeumo | No note | 5 | HIT | 3 | 0 / 0 | 22 | T001, T002, T003, T004 |
| F003 | Fulham v Man Utd | 1-1 | Gonzalo Garcia | No note | 3 | HIT | 1 | 0 / 0 | 22 | T002 |
| F003 | Fulham v Man Utd | 1-1 | Joshua King | No note | 3 | HIT | 1 | 0 / 0 | 22 | T001, T003, T004 |
| F005 | Bournemouth v Liverpool | 0-1 | Alexander Isak | No note | 3 | HIT | 1 | 0 / 0 | 17 | T002, T003, T004 |
| F005 | Bournemouth v Liverpool | 0-1 | Dominik Szoboszlai | No note | 2 | HIT | 0 | 0 / 0 | 17 | T002, T003 |
| F006 | Atletico Madrid v Real Madrid | 2-1 | Vinicius Jr. | No note | 2 | HIT | 0 | 0 / 0 | 8 | T002, T003, T004 |
| F008 | Frosinone v Como | 2-0 | Nicolas Paz | No note | 10 | HIT | 8 | 0 / 0 | 21 | T002, T003, T004 |
| F009 | Leeds v Crystal Palace | 0-0 | Dominic Calvert-Lewin | No note | 1 | MISS | -1 | 0 / 0 | 11 | T002, T003 |
| F010 | Nashville SC v Chicago Fire | 3-0 | Hany Mukhtar | No note | 4 | HIT | 2 | 0 / 0 | 26 | T005 |
| F010 | Nashville SC v Chicago Fire | 3-0 | Robert Lewandowski | No note | 3 | HIT | 1 | 0 / 0 | 26 | T005 |
| F010 | Nashville SC v Chicago Fire | 3-0 | Sam Surridge | No note | 3 | HIT | 1 | 0 / 0 | 26 | T009 |
| F011 | Portland Timbers v Atlanta Utd | 0-1 | Kristoffer Velde | No note | 9 | HIT | 7 | 0 / 0 | 29 | T005, T006, T009, T010, T012 |
| F013 | St. Louis City SC v Toronto FC | 3-1 | Rafael Navarro | No note | 2 | HIT | 0 | 0 / 0 | 32 | T006, T009, T011 |
| F013 | St. Louis City SC v Toronto FC | 3-1 | Simon Becher | No note | 4 | HIT | 2 | 1 / 0 | 32 | T006, T009 |
| F014 | Kansas City v Philadelphia | 3-4 | Bruno Damiani | No note | 2 | HIT | 0 | 0 / 0 | 24 | T007, T009 |
| F014 | Kansas City v Philadelphia | 3-4 | Cavan Sullivan | No note | 2 | HIT | 0 | 0 / 0 | 24 | T006, T009, T010, T012 |
| F014 | Kansas City v Philadelphia | 3-4 | Milan Iloski | No note | 2 | HIT | 0 | 0 / 0 | 24 | T006, T007, T008, T009, T010, T012 |
| F015 | Houston Dynamo v FC Cincinnati | 2-2 | Evander Ferreira | No note | 4 | HIT | 2 | 0 / 0 | 11 | T006, T007, T008, T009, T010, T011, T012 |
| F015 | Houston Dynamo v FC Cincinnati | 2-2 | Mateusz Bogusz | No note | 4 | HIT | 2 | 0 / 0 | 11 | T006, T009, T010, T012 |
| F016 | San Jose v LAFC | 2-2 | Heung-Min Son | No note | 2 | HIT | 0 | 0 / 0 | 13 | T006, T009, T010, T012 |
| F016 | San Jose v LAFC | 2-2 | Jacob Shaffelburg | Denis Bouanga | 1 | MISS | -1 | 0 / 0 | 13 | T006, T010, T012 |
| F017 | DC United v Charlotte FC | 1-2 | Louis Munteanu | No note | 9 | HIT | 7 | 0 / 0 | 9 | T006 |
| F018 | CF Montreal v Columbus Crew | 0-2 | Prince Osei Owusu | No note | 5 | HIT | 3 | 0 / 0 | 18 | T006, T009, T010, T012 |
| F019 | Lyon v Rennes | 4-0 | Esteban Lepaul | No note | 3 | HIT | 1 | 2 / 0 | 25 | T006, T010, T012 |
| F019 | Lyon v Rennes | 4-0 | Lois Openda | No note | 3 | HIT | 1 | 0 / 0 | 25 | T006, T010, T012 |
| F020 | VfB Stuttgart v Borussia Dortmund | 0-1 | Serhou Guirassy | No note | 3 | HIT | 1 | 0 / 0 | 33 | T006, T009, T010, T012 |
| F021 | Roma v Inter Milan | 2-2 | Lautaro Martinez | No note | 6 | HIT | 4 | 0 / 0 | 31 | T006, T009, T010, T012 |
| F021 | Roma v Inter Milan | 2-2 | Marcus Thuram | No note | 3 | HIT | 1 | 0 / 0 | 31 | T006 |
| F023 | Athletic Club v CD Alaves | 0-0 | Oihan Sancet | No note | 2 | HIT | 0 | 0 / 0 | 16 | T006, T009, T010, T012 |
| F024 | Brighton v Arsenal | 3-0 | Bukayo Saka | No note | 2 | HIT | 0 | 0 / 0 | 18 | T006, T009, T010, T012 |
| F026 | FC Dallas v Austin FC | 0-0 | Petar Musa | No note | 1 | MISS | -1 | 0 / 0 | 5 | T010, T012 |
| F028 | Borussia M'gladbach v Mainz | 3-4 | Phillip Tietz | No note | 3 | HIT | 1 | 0 / 0 | 17 | T010, T012 |
| F029 | Trabzonspor v Galatasaray | 4-0 | Mohamed Salah | No note | 4 | HIT | 2 | 0 / 0 | 32 | T010, T012 |
| F031 | Borussia Dortmund v Paderborn | 3-0 | Serhou Guirassy | No note | 3 | HIT | 1 | 0 / 0 | 17 | T013, T014, T015, T016 |
| F032 | Liverpool v Fulham | 0-0 | Alexander Isak | No note | 3 | HIT | 1 | 0 / 0 | 11 | T013, T014, T015, T016 |
| F032 | Liverpool v Fulham | 0-0 | Florian Wirtz | No note | 3 | HIT | 1 | 0 / 0 | 11 | T015, T016 |
| F032 | Liverpool v Fulham | 0-0 | Rio Ngumoha | Bradley Barcola | 1 | MISS | -1 | 0 / 0 | 11 | T013, T014 |
| F034 | SC Freiburg v Borussia M'gladbach | 5-0 | Igor Matanovic | No note | 3 | HIT | 1 | 0 / 0 | 32 | T013, T014, T015, T016 |
| F035 | Sunderland v Arsenal | 0-2 | Bukayo Saka | No note | 4 | HIT | 2 | 0 / 0 | 13 | T013, T014, T015, T016 |
| F036 | Tottenham v Everton | 0-0 | James Maddison | Omar Marmoush | 1 | MISS | -1 | 0 / 0 | 14 | T013 |
| F037 | Chelsea v Hull | 2-2 | Cole Palmer | No note | 3 | HIT | 1 | 0 / 0 | 9 | T016 |
| F037 | Chelsea v Hull | 2-2 | Joao Pedro | No note | 1 | MISS | -1 | 0 / 0 | 9 | T013, T014, T015, T016 |
| F037 | Chelsea v Hull | 2-2 | Morgan Rogers | No note | 2 | HIT | 0 | 0 / 0 | 9 | T013, T014, T015 |
| F038 | Aston Villa v Nottm Forest | 1-2 | Tammy Abraham | Nicolas Jackson | 0 | MISS | -2 | 0 / 0 | 4 | T013 |
| F039 | Philadelphia v CF Montreal | 2-0 | Milan Iloski | No note | 3 | HIT | 1 | 4 / 2 | 29 | T018, T019, T020, T021, T022, T023, T024, T025 |
| F041 | Toronto FC v Chicago Fire | 4-4 | Robert Lewandowski | No note | 3 | HIT | 1 | 1 / 0 | 32 | T018, T020 |
| F043 | Orlando City v San Diego FC | 1-0 | Antoine Griezmann | No note | 3 | HIT | 1 | 1 / 0 | 28 | T018, T020 |
| F044 | Real Salt Lake v LAFC | 2-2 | Heung-Min Son | No note | 4 | HIT | 2 | 1 / 0 | 30 | T018, T020 |
| F046 | Brentford v Sunderland | 1-1 | Igor Thiago | No note | 2 | HIT | 0 | 3 / 2 | 18 | T019, T021, T022, T023, T024, T025 |
| F047 | Fulham v Crystal Palace | 2-3 | Gonzalo Garcia | No note | 5 | HIT | 3 | 3 / 2 | 22 | T019, T021, T022, T023, T024, T025 |
| F049 | Athletic Club v Atletico Madrid | 3-0 | Oihan Sancet | No note | 3 | HIT | 1 | 3 / 0 | 16 | T019, T022, T024, T025 |
| F050 | Villarreal v Deportivo A Coruna | 2-3 | Nicolas Pepe | No note | 5 | HIT | 3 | 3 / 2 | 34 | T019, T021, T022, T023, T024, T025 |
| F052 | Werder Bremen v RB Leipzig | 3-1 | Antonio Nusa | No note | 2 | HIT | 0 | 3 / 2 | 34 | T019, T021, T022, T023, T024, T025 |
| F053 | TSG Hoffenheim v Borussia Dortmund | 2-3 | Serhou Guirassy | No note | 5 | HIT | 3 | 3 / 2 | 32 | T019, T021, T022, T023, T024, T025 |
| F054 | Borussia M'gladbach v Elversberg | 3-4 | Hugo Bolin | No note | 6 | HIT | 4 | 1 / 0 | 17 | T019, T022 |
| F055 | Nottm Forest v Tottenham | 0-0 | Omar Marmoush | No note | 3 | HIT | 1 | 3 / 2 | 27 | T019, T021, T022, T023, T024, T025 |
| F056 | Roma v Atalanta | 2-1 | Donyell Malen | No note | 3 | HIT | 1 | 1 / 0 | 31 | T019, T022 |
| F060 | FC Copenhagen v FC Nordsjaelland | 2-0 | Mohamed Elyounoussi | No note | 2 | HIT | 0 | 0 / 0 | 21 | T032 |
| F061 | Gent v OH Leuven | 1-0 | Josue Vergara | No note | 0 | MISS | -2 | 0 / 0 | 5 | T031, T033 |
| F062 | Hibernian v Hearts | 1-3 | Claudio Braga | No note | 5 | HIT | 3 | 0 / 0 | 22 | T031, T033 |
| F064 | Toulouse v Lille | 0-1 | Ayase Ueda | Olivier Giroud | 0 | MISS | -2 | 0 / 0 | 7 | T033 |
| F064 | Toulouse v Lille | 0-1 | Hakon Arnar Haraldsson | No note | 0 | MISS | -2 | 0 / 0 | 7 | T031 |
| F067 | West Brom v Charlton | 1-1 | Isaac Price | No note | 4 | HIT | 2 | 3 / 0 | 34 | T040, T041, T042, T043, T044 |
| F068 | Burnley v Middlesbrough | 1-1 | Will Lankshear | No note | 1 | MISS | -1 | 2 / 0 | 4 | T040, T043, T044 |
| F069 | Millwall v Wrexham | 0-3 | Joshua Coburn | No note | 0 | MISS | -2 | 2 / 0 | 6 | T040, T043, T044 |
| F072 | Udinese v Venezia | 2-1 | Keinan Davis | No note | 2 | HIT | 0 | 0 / 0 | 33 | T045 |
| F074 | Osasuna v Getafe | 1-0 | Ante Budimir | No note | 1 | MISS | -1 | 0 / 0 | 6 | T047, T048, T049 |
| F075 | Amed SK v Trabzonspor | 2-1 | Mohamed Salah | No note | 3 | HIT | 1 | 0 / 0 | 15 | T047, T048, T049 |
| F076 | Chelsea v Brighton | 4-3 | Cole Palmer | No note | 4 | HIT | 2 | 0 / 0 | 19 | T056, T057, T058 |
| F076 | Chelsea v Brighton | 4-3 | Joao Pedro | No note | 5 | HIT | 3 | 0 / 0 | 19 | T056, T057, T058 |
| F078 | Samsunspor v Fenerbahce | 0-2 | Mason Greenwood | No note | 3 | HIT | 1 | 0 / 0 | 31 | T056, T058 |
| F079 | St. Louis City SC v FC Dallas | 3-3 | Simon Becher | No note | 3 | HIT | 1 | 0 / 0 | 32 | T056, T058 |
| F080 | Columbus Crew v New England | 1-3 | Carles Gil | No note | 4 | HIT | 2 | 0 / 0 | 20 | T056, T058 |
| F082 | Man Utd v Ipswich | 5-2 | Matheus Cunha | No note | 2 | HIT | 0 | 0 / 0 | 25 | T057 |
| F084 | Minnesota Utd v Orlando City | 3-3 | Antoine Griezmann | No note | 2 | HIT | 0 | 0 / 0 | 26 | T061, T063, T064, T065, T078, T080 |
| F085 | Nashville SC v FC Cincinnati | 4-0 | Evander Ferreira | No note | 5 | HIT | 3 | 0 / 0 | 26 | T061, T063, T064, T065, T066, T075, T077, T078, T080 |
| F086 | DC United v LAFC | 0-0 | Louis Munteanu | No note | 4 | HIT | 2 | 0 / 0 | 10 | T061, T063, T064, T065, T066 |
| F087 | Houston Dynamo v San Jose | 0-0 | Guilherme Augusto | No note | 1 | MISS | -1 | 0 / 0 | 5 | T061, T063, T064, T065, T066, T075 |
| F088 | Kansas City v Vancouver Whitecaps | 0-3 | Brian White | No note | 4 | HIT | 2 | 0 / 0 | 24 | T061, T063, T064, T065, T066 |
| F089 | Portland Timbers v Austin FC | 1-2 | Kristoffer Velde | No note | 3 | HIT | 1 | 0 / 0 | 29 | T064, T065, T066 |
| F090 | NY Red Bulls v Philadelphia | 1-3 | Cavan Sullivan | No note | 3 | HIT | 1 | 0 / 0 | 28 | T061, T075 |
| F090 | NY Red Bulls v Philadelphia | 1-3 | Milan Iloski | No note | 7 | HIT | 5 | 0 / 0 | 28 | T061, T063, T064, T065, T066, T075, T077, T078, T080 |
| F093 | Levante v Real Betis | 5-2 | Antony | No note | 6 | HIT | 4 | 0 / 0 | 25 | T070, T074, T075, T077, T078, T079, T080 |
| F094 | Elversberg v Bayer Leverkusen | 3-2 | Patrik Schick | No note | 5 | HIT | 3 | 0 / 0 | 20 | T070, T074, T079 |
| F096 | Liverpool v Nottm Forest | 2-2 | Rio Ngumoha | Cody Gakpo | 0 | MISS | -2 | 0 / 0 | 11 | T074, T075, T077, T078, T079, T080 |
| F101 | Lille v PSG | 2-2 | Khvicha Kvaratskhelia | Desire Doue | 1 | MISS | -1 | 0 / 0 | 6 | T081 |
| F103 | Barcelona v Athletic Club | 2-0 | Raphinha | No note | 3 | HIT | 1 | 0 / 0 | 16 | T087 |
| F106 | Lyon v Fenerbahce | 1-2 | Conceicao Talisca | No note | 2 | HIT | 0 | 0 / 0 | 12 | T095, T098, T099, T100 |
| F106 | Lyon v Fenerbahce | 1-2 | Corentin Tolisso | No note | 2 | HIT | 0 | 0 / 0 | 12 | T095, T098 |
| F106 | Lyon v Fenerbahce | 1-2 | Lois Openda | No note | 4 | HIT | 2 | 0 / 0 | 12 | T099, T100 |
| F108 | Valencia v Real Betis | 0-1 | Antony | No note | 4 | HIT | 2 | 0 / 0 | 33 | T101, T102 |
| F113 | Fulham v Chelsea | 2-3 | Joao Pedro | No note | 4 | HIT | 2 | 2 / 0 | 22 | T105, T111, T113 |
| F114 | Osasuna v Levante | 0-0 | Ante Budimir | No note | 4 | HIT | 2 | 0 / 0 | 28 | T109 |
| F117 | Al Ittihad Jeddah v Al Hazm | 3-2 | Youssef En Nesyri | No note | 2 | HIT | 0 | 0 / 0 | 15 | T109 |
| F118 | Neom SC v Al Qadisiya Al Khubar | 0-2 | Tijjani Reijnders | No note | 2 | HIT | 0 | 0 / 0 | 12 | T109 |
| F120 | Atlanta Utd v Kansas City | 2-1 | Miguel Almiron | No note | 2 | HIT | 0 | 0 / 0 | 16 | T116 |
| F121 | Elche v Barcelona | 0-5 | Lamine Yamal | No note | 2 | HIT | 0 | 0 / 0 | 38 | T116 |
| F122 | Rennes v PSG | 2-2 | Ousmane Dembele | No note | 3 | HIT | 1 | 0 / 0 | 12 | T116 |
| F123 | Alanyaspor v Besiktas | 1-0 | Vaclav Cerny | No note | 2 | HIT | 0 | 0 / 0 | 15 | T116 |
| F130 | San Diego FC v Colorado Rapids | 3-0 | Marcus Ingvartsen | No note | 0 | MISS | -2 | 5 / 0 | 13 | T118, T124, T125, T128, T129, T130 |
| F130 | San Diego FC v Colorado Rapids | 3-0 | Rafael Navarro | No note | 1 | MISS | -1 | 0 / 0 | 13 | T118, T124, T125, T128, T129, T130 |
| F131 | CF Montreal v LA Galaxy | 2-2 | Prince Osei Owusu | No note | 4 | HIT | 2 | 0 / 0 | 18 | T118, T119, T124, T125, T128, T129, T130, T131, T132, T133, T135, T136 |
| F132 | LAFC v Portland Timbers | 1-1 | Heung-Min Son | No note | 9 | HIT | 7 | 0 / 0 | 11 | T118, T124, T125, T128, T129, T130, T131, T132, T133, T135, T136 |
| F132 | LAFC v Portland Timbers | 1-1 | Omir Fernandez | Kristoffer Velde | 1 | MISS | -1 | 0 / 0 | 11 | T122 |
| F133 | FC Cincinnati v Seattle Sounders | 1-1 | Evander Ferreira | No note | 3 | HIT | 1 | 0 / 0 | 21 | T118, T124, T125, T128, T129, T130, T131, T132, T133, T135, T136 |
| F134 | Charlotte FC v DC United | 3-1 | Pep Biel | No note | 2 | HIT | 0 | 0 / 0 | 19 | T136 |
| F135 | Orlando City v Real Salt Lake | 2-1 | Antoine Griezmann | No note | 5 | HIT | 3 | 0 / 0 | 28 | T118, T124, T125, T128, T129, T130, T131, T132, T133, T135 |
| F137 | Inter Miami v Toronto FC | 1-2 | Lionel Messi | No note | 2 | HIT | 0 | 0 / 0 | 23 | T136 |
| F138 | Atletico Madrid v Villarreal | 2-2 | Jose Maria Gimenez | Ademola Lookman | 1 | MISS | -1 | 0 / 0 | 8 | T120 |
| F141 | San Jose v Minnesota Utd | 1-5 | Preston Judd | No note | 1 | MISS | -1 | 0 / 0 | 13 | T122, T123, T131, T132, T133, T135 |
| F142 | Austin FC v Philadelphia | 1-1 | Milan Iloski | No note | 2 | HIT | 0 | 0 / 0 | 16 | T131, T132, T133, T135 |
| F144 | Udinese v Como | 1-1 | Nicolas Paz | No note | 4 | HIT | 2 | 0 / 0 | 33 | T127, T134 |
| F145 | Genoa v Napoli | 0-2 | Lorenzo Lucca | Rasmus Hojlund | 0 | MISS | -2 | 0 / 0 | 10 | T127, T134 |
| F146 | Borussia Dortmund v Bayern Munich | 1-2 | Tom Bischof | Luis Diaz | 1 | MISS | -1 | 0 / 0 | 8 | T127, T134 |
| F148 | Espanyol v Real Madrid | 1-2 | Kylian Mbappe | No note | 10 | HIT | 8 | 0 / 0 | 20 | T128 |
| F151 | Fenerbahce v Konyaspor | 4-2 | Mason Greenwood | No note | 5 | HIT | 3 | 0 / 0 | 21 | T127 |
| F152 | Athletic Club v Sevilla | 1-3 | Inaki Williams | No note | 2 | HIT | 0 | 0 / 0 | 38 | T134 |
| F156 | Columbus Crew v CF Montreal | 1-2 | Prince Osei Owusu | No note | 3 | HIT | 1 | 0 / 0 | 19 | T137, T138, T139, T140 |
| F157 | FC Cincinnati v New York City | 2-1 | Evander Ferreira | No note | 6 | HIT | 4 | 0 / 0 | 10 | T137, T138, T139, T140, T141 |
| F158 | Portland Timbers v San Diego FC | 3-1 | Kevin Kelsy | No note | 3 | HIT | 1 | 0 / 0 | 30 | T137 |
| F158 | Portland Timbers v San Diego FC | 3-1 | Kristoffer Velde | No note | 2 | HIT | 0 | 0 / 0 | 30 | T138, T139, T140, T141 |
| F159 | DC United v New England | 0-3 | Louis Munteanu | No note | 2 | HIT | 0 | 0 / 0 | 20 | T137, T138, T139, T140 |
| F160 | Real Salt Lake v FC Dallas | 3-4 | Petar Musa | No note | 4 | HIT | 2 | 0 / 0 | 30 | T137, T138, T139, T140, T141 |
| F162 | Minnesota Utd v Atlanta Utd | 1-2 | Tomas Chancalay | No note | 2 | HIT | 0 | 0 / 0 | 26 | T138, T139, T140 |
| F165 | Orlando City v Chicago Fire | 1-2 | Antoine Griezmann | No note | 5 | HIT | 3 | 0 / 0 | 12 | T139, T140, T141 |
| F165 | Orlando City v Chicago Fire | 1-2 | Robert Lewandowski | No note | 4 | HIT | 2 | 0 / 0 | 12 | T141 |
| F166 | Toronto FC v Charlotte FC | 3-3 | Luca De La Torre | Pep Biel | 1 | MISS | -1 | 0 / 0 | 7 | T141 |
| F167 | Kansas City v St. Louis City SC | 1-1 | Alexandru Matan | Simon Becher | 0 | MISS | -2 | 0 / 0 | 5 | T141 |
| F168 | Lens v PSG | 1-0 | Khvicha Kvaratskhelia | No note | 4 | HIT | 2 | 0 / 0 | 25 | T142, T146, T147, T148, T150 |
| F169 | Seattle Sounders v Vancouver Whitecaps | 0-2 | Ryan Gauld | No note | 0 | MISS | -2 | 0 / 0 | 13 | T142 |
| F170 | Chicago Fire v Portland Timbers | 2-1 | Kevin Kelsy | No note | 2 | HIT | 0 | 0 / 0 | 9 | T148 |
| F170 | Chicago Fire v Portland Timbers | 2-1 | Kristoffer Velde | No note | 3 | HIT | 1 | 0 / 0 | 9 | T147 |
| F170 | Chicago Fire v Portland Timbers | 2-1 | Puso Dithejane | Philip Zinckernagel | 0 | MISS | -2 | 0 / 0 | 9 | T146 |
| F170 | Chicago Fire v Portland Timbers | 2-1 | Robert Lewandowski | No note | 4 | HIT | 2 | 0 / 0 | 9 | T150 |
| F171 | Austin FC v FC Dallas | 1-2 | Petar Musa | No note | 3 | HIT | 1 | 0 / 0 | 16 | T142, T146, T147, T148, T150 |
| F172 | New York City v Philadelphia | 2-3 | Cavan Sullivan | No note | 6 | HIT | 4 | 0 / 0 | 39 | T147, T149 |
| F172 | New York City v Philadelphia | 2-3 | Milan Iloski | No note | 5 | HIT | 3 | 0 / 0 | 39 | T142, T146, T147, T148, T149, T150 |
| F173 | Orlando City v FC Cincinnati | 1-1 | Evander Ferreira | No note | 5 | HIT | 3 | 0 / 0 | 28 | T151, T153, T154, T155, T156 |
| F174 | CF Montreal v DC United | 1-1 | Hennadii Synchuk | No note | 7 | HIT | 5 | 0 / 0 | 18 | T151, T153, T154, T155 |
| F174 | CF Montreal v DC United | 1-1 | Prince Osei Owusu | No note | 5 | HIT | 3 | 0 / 0 | 18 | T156 |
| F175 | Houston Dynamo v LA Galaxy | 1-0 | Guilherme Augusto | No note | 3 | HIT | 1 | 0 / 0 | 23 | T151, T153, T154, T155, T156 |
| F176 | San Jose v St. Louis City SC | 1-3 | Timo Werner | No note | 0 | MISS | -2 | 0 / 0 | 7 | T151, T153, T154, T155, T156 |
| F178 | LAFC v San Diego FC | 0-1 | Heung-Min Son | No note | 4 | HIT | 2 | 0 / 0 | 24 | T151, T153, T154, T155, T156 |
| F179 | Nashville SC v Inter Miami | 4-1 | Lionel Messi | No note | 12 | HIT | 10 | 1 / 0 | 26 | T151, T152, T153, T157 |
| F180 | Charlotte FC v Columbus Crew | 3-1 | Pep Biel | No note | 3 | HIT | 1 | 0 / 0 | 19 | T153, T154, T155, T156 |
| F198 | Monterrey v Orlando City | 1-2 | Antoine Griezmann | No note | 3 | HIT | 1 | 1 / 0 | 12 | T193, T194 |
| F218 | Nashville SC v CF Montreal | 1-0 | Hany Mukhtar | No note | 2 | HIT | 0 | 1 / 0 | 26 | T279, T280 |
| F222 | England v Argentina | 1-2 | Harry Kane | No note | 1 | MISS | -1 | 0 / 0 | 10 | T302 |
| F222 | England v Argentina | 1-2 | Lionel Messi | No note | 1 | MISS | -1 | 0 / 0 | 10 | T302 |

## Excluded groups

| Fixture | Pairing | Player | Status | PDF page |
| --- | --- | --- | --- | --- |
| F002 | Villarreal v Levante | Nicolas Pepe | VOID | 37 |
| F025 | New England v Orlando City | Antoine Griezmann | UNKNOWN | 39 |
| F027 | Nottm Forest v Coventry | Igor Jesus | VOID | 36 |
| F033 | Augsburg v Bayer Leverkusen | Patrik Schick | VOID | 35 |
| F039 | Philadelphia v CF Montreal | Prince Osei Owusu | VOID | 29 |
| F040 | FC Cincinnati v DC United | Evander Ferreira | VOID | 35 |
| F055 | Nottm Forest v Tottenham | Igor Jesus | VOID | 27 |
| F057 | Newcastle v Bournemouth | Yoane Wissa | UNKNOWN | 39 |
| F058 | Inter Milan v Napoli | Pio Esposito | UNKNOWN | 38 |
| F060 | FC Copenhagen v FC Nordsjaelland | Prince Amoako | VOID | 21 |
| F065 | Club America v Monterrey | Brian Rodriguez | UNKNOWN | 38 |
| F066 | Toluca v Leon | Daniel Arcila | VOID | 39 |
| F066 | Toluca v Leon | Diber Cambindo | UNKNOWN | 39 |
| F066 | Toluca v Leon | Helinho | UNKNOWN | 39 |
| F069 | Millwall v Wrexham | Camiel Neghli | VOID | 6 |
| F070 | Celtic v Aberdeen | Benjamin Nygren | VOID | 8 |
| F071 | QPR v Cardiff | Ilias Chair | VOID | 37 |
| F078 | Samsunspor v Fenerbahce | Conceicao Talisca | VOID | 31 |
| F092 | Strasbourg v Lens | Odsonne Edouard | VOID | 37 |
| F139 | Brighton v Aston Villa | Ollie Watkins | VOID | 35 |
| F143 | Nottm Forest v Leeds | Chris Wood | VOID | 6 |
| F161 | Colorado Rapids v LAFC | Heung-Min Son | VOID | 19 |
| F169 | Seattle Sounders v Vancouver Whitecaps | Brian White | VOID | 13 |
| F172 | New York City v Philadelphia | Nicolas Fernandez Mercau | VOID | 39 |
| F211 | Orlando City v Nashville SC | Hany Mukhtar | VOID | 37 |
| F211 | Orlando City v Nashville SC | Martin Ojeda | VOID | 37 |
| F212 | NY Red Bulls v Charlotte FC | Pep Biel | VOID | 36 |
| F215 | LAFC v Real Salt Lake | Denis Bouanga | VOID | 24 |
| F215 | LAFC v Real Salt Lake | Heung-Min Son | VOID | 24 |
