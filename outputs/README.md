# Weekend Shots Research — Progress and Current State

Updated: 7 October 2026.

## Live four-league Plan B 3+ scanner

The current operational focus is now a prospective Saturday/Sunday scanner for **MLS, Premier League, Serie A and Bundesliga**. It acquires data before applying the frozen formula, ranks the top five Tier A/B environments, builds deterministic possible lineups and freezes no more than three Plan B candidates ranked for the 3+ shots target.

The first live board is saved in `live_plan_b3/2026-10-10/`. Its bounded FotMob acquisition contains **606 normalized historical matches with zero failures**. The scanner evaluated **40 weekend fixtures**, selected five environments and froze three provisional candidates. All **21/21 integrity checks pass**. Predicted or last-used lineups are explicitly rejected by the confirmation gate; only a `standard` lineup before kickoff can turn a frozen provisional candidate into an official pick. No official picks are locked yet.

This is an operating trial, not evidence of a new win rate. The prior retrospective 3+ simulation remains 12/17 and did not clear the 71.4% break-even hit rate at hypothetical 1.40 odds. Future official picks must be settled prospectively without changing the frozen rule.

### Season-to-date engine replay

The four-league engine has also been retrospectively simulated from each current season's opening weekend through 7 October 2026. The acquisition contains **996 matches with zero failures** and supplies **428 completed Saturday/Sunday target fixtures across 24 weekends**. All information used for a weekend was cut off at Friday 00:00 UTC, so Saturday outcomes could not affect Sunday selections.

- Official simulated Plan B selections: **51**.
- 3+ shots results: **40/51 — 78.4%**; 95% Wilson interval **65.4–87.5%**.
- Active selection weekends: **22**; completely clean weekends: **11/22 — 50.0%**.
- Weekends with three official picks: **9**; all three hit on **6/9 — 66.7%**.
- Longest individual 3+ hit streak: **10**; longest miss streak: **2**.
- MLS: **38/49 — 77.6%**. Premier League: **1/1**. Serie A: **1/1**. Bundesliga: **0 picks**.
- The integrity checker passes **19/19 checks**, including Friday cutoffs, environment ranks, top-three ranking, lineup confirmation and outcome reconciliation.

The result is dominated by MLS because its 2026 season has far more completed weekends; the European seasons have only reached roughly five matchweeks. It must not be presented as 51 independent cross-league observations or as a guaranteed future rate. Historical odds were not collected. Full records are in `season_to_date_plan_b3/`.

August 22–23 fresh-weekend work is underway: 15 fixtures checked; five pass home strength and three pass both environment gates (Charlotte–D.C., Miami–Toronto, Atlanta–Sporting Kansas City). All three home XIs are saved (33 starters). Full-name/time-proximity diagnostics found 543 matching historical player-shot values, zero shot conflicts and 58 unmatched appearances across 47 proposed identities; these are not approved merges or final required-download counts. Previous-five-start/minute reconciliation and the new A/B settlement remain incomplete. See `mls_2026_aug22_validation/report.md`, `target_lineups.json` and `overlap_diagnostic.json`. No new win rate claimed.

On-demand local prototype: run `python work/on_demand.py` and open `http://127.0.0.1:8766`. It checks the historical MLS cache, fetches bounded missing ASA shot records and saves a specific browser-agent handoff. Flashscore collection is not autonomously dispatched from the page; new-source A/B remains blocked pending reconciliation. See `on_demand/README.md` for exact capabilities and limits. No paid requests or scheduled jobs.

Streak analysis of the saved MLS weekend replay: A has 30/36 hits, longest ordered hit run 11 and miss run 2; B has 21/23 hits, longest hit run 10 and miss run 1. Same-kickoff ordering is arbitrary: the longest run of kickoff groups with every pick hitting is 6 for both. All picks hit in 4/8 active weekends for A and 6/8 for B. See `mls_2026_weekends/streaks.html` and `streaks.json`; reproduce with `python work/mls_streaks.py`. These are previously studied, incompletely covered data, not fresh validation or future streak probabilities.

Latest source check: Flashscore public pages supplied explicit starting lineups, player shots and Minutes played for three MLS 2026 sample matches. Saved 66 starting-name entries and 13 partial player examples in `mls_2026_sources/flashscore_feasibility.json`; see `flashscore_feasibility.md` for the bounded August 22–23 collection plan. This is source feasibility only, not a new weekend backtest. Provider IDs and minute conventions still require overlap checks before merging.

## Where we are

**Phase 3: pattern testing and consistency research.** We have a working historical replay, a promising 2+ shots baseline, and exploratory refinements. We do not yet have a validated live weekend scanner or a proven future win rate.

**Latest focus: MLS 2026, historical weekends first.** A browser-based historical scanner now ranks favourable environments and displays A/B candidates and settlements for each Saturday/Sunday in America/Denver. It uses the existing saved history, not a new independent test. Results: A **30/36 (83.3%)**, B **21/23 (91.3%)**, across eight weekends with picks. The saved stats end at 2026-08-17 02:30 UTC (August 16 locally). Later weekends are labelled as data gaps, not misses or verified zero-opportunity weeks. No recurring monitoring is scheduled.

A user-requested research agent archived American Soccer Analysis (ASA) data for **401 completed MLS 2026 matches and 12,361 player appearances**, including **6,788 zero-shot appearances**, through September 27 UTC. All 401 game IDs have player records, with zero duplicate appearance keys. These overlap existing history and must not be added to project totals as wholly new matches. Raw responses and retrieval/hash metadata are in `mls_2026_sources/`; `asa_player_coverage_2026.json` records coverage. ASA does not supply a starter flag in the checked player-game endpoint and uses stoppage-inclusive minutes. Those fields must be reconciled before exact A/B replay on newer matches. Do not infer starts or substitute expanded minutes into the existing 80-minute rule. The newer archive has **not** produced a new A/B win rate.

The first fixed A/B evaluation on new matches is now complete: **Ligue 1 2015/16, 377/380 available fixtures**. A hit **44/55 (80.0%)**; B hit **26/29 (89.7%)**. This is promising but insufficient to promote B: partial coverage, a small sample, strong player concentration and an uncertainty interval that includes no improvement. Keep A as the baseline and B as an experimental version; do not retune on these new results.

The inspected StatsBomb catalog has no further unused complete European men's league season. More recent selected-team datasets are not substitutes for complete league history. A stronger follow-up needs a suitable new dataset or an agreed prospective paper-test plan, within the user's source constraints.

## Goal

Build a weekend screening system that:

1. Ranks favourable match/team shooting environments.
2. Finds the team's main, consistent shooters.
3. Checks starting status and likely playing time.
4. Produces a selective shortlist for **2+ shots**, then separately develops rules for **1+ shot** and **1+ shot on target**.

Consistency matters more than a flattering pooled percentage. Measure performance across weeks, leagues, seasons and players. Accept quiet weekends instead of forcing selections.

## Current user preferences and boundaries

- StatsBomb remains the preferred research feed. The user has now explicitly authorised an internet-research agent to find current MLS 2026 fixtures and suitable data. Free documented alternatives may be researched; do not resume paid SportsAPI Pro downloads without approval.
- **Do not use India.** No Indian league match-event/player dataset was downloaded or included in our tests; only availability was checked.
- Keep this practical: simple repeatable patterns, sample sizes and stability checks.
- Preserve the existing project, historical records and raw source data.
- Do not invent missing values or treat unknown shots as zero.
- No betting placement, staking strategy, subscriptions or paid upgrades have been performed.
- No recurring download or monitoring automation is scheduled.

## Original pattern: unchanged baseline

Target: **2+ total shots by an individual player**. This is not a shots-on-target rule.

### Team environment

- Home team has strictly higher season-to-date points per game than the away team.
- Home team also has strictly higher points per game over its previous five matches.
- At least eight earlier season results per team, in the same competition and season.
- Home team averages at least 12 shots over its last up-to-five home matches.
- Away team concedes at least 12 shots over its last up-to-five away matches.
- At least three usable venue matches per side.
- Home shot proxy exceeds away shot proxy:
  - Home proxy = (home side's earlier home shots + away side's earlier away shots conceded) / 2.
  - Away proxy = (away side's earlier away shots + home side's earlier home shots conceded) / 2.

These proxies are simple historical averages, not trained or calibrated expected-shot forecasts.

### Player selection

- Recorded home starter.
- Five earlier starts for the same team and competition within 180 days, with known shots.
- Top two eligible home starters by average shots over those five starts. Prior average shot share breaks ties, then player ID.
- Average minutes over those starts at least 70.
- Reached 2+ shots in at least four of those five starts.

History must be more than 24 hours before kickoff. Actual current-match minutes, shots, score and realised shot share do not select candidates. Starting status is assumed known at lineup time; this is not yet a Saturday-morning selection simulation.

The comparison benchmark uses the same eligible, consistent home shooters without requiring the stronger-home/shooting-environment conditions. It is not a pool of all home and away players.

## Data in the main research datasets

| Dataset | Matches with player stats | Player appearances | State |
|---|---:|---:|---|
| MLS 2024–2026 | 1,016 | 31,275 | Saved coverage is partial; 665 fixtures had sufficient history for the baseline replay |
| Premier League 2015/16 | 380 | 10,469 | Full season acquired and replayed |
| La Liga 2015/16 | 380 | 10,550 | Full season acquired and replayed |
| Serie A 2015/16 | 380 | 10,598 | Full season acquired and replayed |
| Ligue 1 2015/16 | 377 | 10,479 | New A/B evaluation; three expected fixtures missing |
| Bundesliga 2024/25 | 73 | 2,289 | Partial SportsAPI Pro download; collection stopped |
| **Total** | **2,606** | **75,660** | **Not 75,660 qualifying picks** |

These totals exclude duplicate backup exports, synthetic demo records and small unused league fragments. A player appearance is one player in one match; many appearances belong to the same fixture.

The Bundesliga catalog contains all 306 regular-season fixtures. Two promotion/relegation playoff fixtures were identified and excluded from the regular-season scope, with an audit record. Player stats for 233 matches remain uncollected. Ten SportsAPI requests remained at the last check; that is a historical snapshot, not a live quota reading.

Recent European men's StatsBomb coverage checked so far is mostly selected teams' matches rather than complete seasons. For example, the available Bundesliga 2023/24 file has 34 matches, not a full league. Do not silently treat these as full-season validation or mix providers to fill gaps.

## Baseline results

| Dataset | Full-pattern hits / picks | Hit rate | Consistent-shooter benchmark |
|---|---:|---:|---:|
| MLS | 150 / 185 | 81.1% | 523 / 660 — 79.2% |
| Premier League 2015/16 | 73 / 90 | 81.1% | 222 / 297 — 74.7% |
| La Liga 2015/16 | 59 / 70 | 84.3% | 206 / 273 — 75.5% |
| Serie A 2015/16 | 71 / 86 | 82.6% | 220 / 290 — 75.9% |
| **Main-test total** | **353 / 431** | **81.9%** | Pooled descriptive result only |

The 431 picks include **353 hits and 78 misses**. The Bundesliga batch adds two hits from two picks in one eligible fixture; it is excluded from the 431-pick research cohort because that preliminary sample is too small to assess consistency.

### What the consistency checks showed

- The MLS full pattern had picks in 44 active weeks; 12 of those weeks finished below 70%.
- In the original later MLS sample, the full pattern hit 46/57 (80.7%); the benchmark hit 152/184 (82.6%). Home-environment filtering did not demonstrate a later-sample improvement there.
- Excluding each European league's three most-selected players reduced full-pattern rates to 77.9% in England, 76.6% in Spain and 79.0% in Italy.
- The three European tests all use 2015/16 StatsBomb data. Different leagues are useful evidence, but this does not establish consistency across modern European seasons.

## Latest research: learning from wins AND misses

We compared all 353 wins with all 78 misses. Studying wins alone would hide which conditions also occur in failures.

Winners had higher earlier shooting involvement:

- Prior shots per start: **3.63 for wins vs 3.12 for misses**.
- Prior average team-shot share: **25.1% vs 22.0%**.
- Prior average minutes: **85.8 vs 84.0**.

These are descriptive associations within the baseline-selected cohort, not causal conclusions.

Ten predefined extra filters were evaluated; the original baseline was not changed.

| Rule on top of the baseline | All hits / picks | Rate | Baseline picks retained | Later-date check |
|---|---:|---:|---:|---:|
| No extra filter | 353 / 431 | 81.9% | 100% | 104 / 125 — 83.2% |
| Prior average shots >=3 AND minutes >=80 | 230 / 263 | 87.5% | 61.0% | 57 / 64 — 89.1% |
| Prior average shot share >=25% | 146 / 166 | 88.0% | 38.5% | 39 / 44 — 88.6% |

Both refinements use the previous five starts, not the current match.

The automated **earlier-data-only** candidate selection chose the 25% shot-share filter. However, it performed worse in the Premier League: 19/24 (79.2%) overall and only 3/5 in the later slice. The 3-shots/80-minutes combination is the recommended practical challenger because it retains more opportunities; it was NOT the automatic earlier-only winner. That recommendation follows inspection of the existing results and still needs independent testing.

The latest research's later slice is the last 30% of qualifying calendar dates within each league. It differs from the original replay splits. It is already-inspected history, **not an untouched holdout**. Do not claim that 87.5–89.1% is a validated future win rate.

## Latest Plan B replication: ranked Big Five 2023/24

The frozen ranked-environment workflow was replayed on four post-international-break weekends in 2023/24. The plan, dates, weights, top-five cutoff and player thresholds were saved before acquiring the 946 FotMob match records. All records normalized successfully with zero acquisition failures.

| Check | Result |
|---|---:|
| Selected top-five Tier A/B environments | 20 |
| Home team outshot away team | 16/20 — 80.0% |
| Plan A candidates | 18/22 — 81.8% |
| **Plan B candidates** | **11/14 — 78.6%** |
| Completely clean Plan B weekends | 1/4 |
| Longest Plan B hit streak | 6 |

This is useful negative evidence against treating the earlier 9/9 Plan B season as the expected rate. In this new replication, B was stricter but did not outperform A. The three Plan B misses were preserved rather than excluded after inspection.

Across the two directly comparable ranked Big Five replications (2023/24 and 2024/25), Plan B is **20/23 — 87.0%** versus Plan A at **37/44 — 84.1%**. Plan B produced 2.88 candidates per active weekend, but only **5/8 active weekends — 62.5%** were completely clean. This pooled difference is descriptive, not proof that B is superior, because observations share leagues, fixtures, players and weekends.

The combined report and every underlying selection are saved in `ranked_plan_b_combined_backtest/`, `big5_2023_ranked_candidate_validation/` and `big5_2024_ranked_candidate_validation/`.

### Retrospective 3+ shots / top-three simulation

A separate what-if simulation changed the target to **3+ shots**, assumed decimal odds of **1.40**, and retained at most the three highest-ranked Plan B candidates per weekend using only prior average shots, prior minutes, environment rank and player ID. This is not an independent test because the underlying backtests had already been inspected.

- Flat $10 singles: **12/17 — 70.6%**, $170 staked, $168 returned, **-$2 (-1.2% ROI)**. The break-even rate at 1.40 is 71.4%.
- Exact three-player weekend combinations: **1/4 clean weekends — 25.0%**, combined hypothetical odds 2.744, $40 staked, $27.44 returned, **-$12.56 (-31.4% ROI)**.
- A full-return weekend rollover lost its first three eligible attempts and won the fourth. With a fresh $10 deposit after each loss, total deposits were $40 and the ending active balance was $27.44.

The simulation does not support treating three 3+ shots selections as a reliable weekend combination at the assumed price. Historical market availability, pricing and correlation were not tested. Full records are saved in `plan_b_top3_three_shots_simulation/`.

The ranking was then corrected specifically for the 3+ target. The unchanged Plan B/environment gate was retained, but candidates were reordered using previous-five 3+ frequency, average player share of team shots, average shots, minutes and environment rank. All 23 Plan B candidates had complete feature histories. The corrected ranking changed one top-three selection—Leroy Sane replaced Harry Kane on 2023-10-07—and both players reached 3+ shots. Consequently, the measured result remained **12/17 singles** and **1/4 clean exact-three weekends**. This indicates the weak accumulator result was not explained by the original ordering alone. The corrected run is saved in `plan_b_top3_three_shots_reranked/` and still requires untouched validation.

## Recent big-five pre-break test: no bets

The requested four common weekends before the September 21, 2026 international break were August 29–30, September 5–6, September 12–13 and September 19–20. The exact frozen formula returned **zero eligible fixtures and zero picks** across the Premier League, La Liga, Serie A, Bundesliga and Ligue 1.

This is expected: both teams need eight earlier same-season league results. By the final weekend, the leagues had only reached approximately Matchdays 4–7. A hit rate is therefore undefined. Carrying previous-season history forward would be a different rule and was not silently substituted.

## Weekend operating simulation

Five frozen, non-overlapping validation datasets were restricted to Saturday/Sunday fixtures and grouped into historical weekends. Across 124 match-weekends:

| Plan | Active weekends | Picks | Picks per active weekend | Individual hits | Entire weekend won |
|---|---:|---:|---:|---:|---:|
| A | 56/124 — 45.2% | 116 | 2.07 | 98/116 — 84.5% | 41/56 — 73.2% |
| B | 39/124 — 31.5% | 61 | 1.56 | 57/61 — 93.4% | 35/39 — 89.7% |

This suggests A would generate a playable weekend roughly twice every five match-weekends, usually with two candidates. B would act less often—roughly one weekend in three—but historically produced a clean weekend more often.

If every active weekend started a fresh $10 all-in rollover, the mathematical totals were +$388.73 for A at 1.50 and +$750 for B at 2.00. Those are not market-tested returns: 32 A weekends and 12 B weekends contained same-kickoff selections that could not literally be rolled sequentially, and the prices are hypothetical.

## Latest random backtest: WSL 2018/19

The random pool contained five unused league-format catalog entries. NWSL 2018 was drawn first but rejected before player outcomes because only 36 scattered fixtures were available. WSL 2018/19 was drawn second and accepted at 107/110 fixtures (97.3% coverage). The choice, rejection and redraw timestamps are saved.

- Pattern A: **12/13 — 92.3%**.
- Pattern B: **11/12 — 91.7%**.
- A continuous rollover: seven wins grew $10 to **$170.86**, then the next loss wiped it out. After restarting with $10, the final five wins ended at **$75.94**.
- B continuous rollover: six wins grew $10 to **$640**, then the next loss wiped it out. After restarting with $10, the final five wins ended at **$320**.

After two $10 deposits, the ending active balances correspond to +$55.94 for A and +$300 for B. These figures assume no cash-out during a streak; peak balances that were followed by a loss were not realized.

## Previous backtest: WSL 2020/21 with $10 betting simulation

The rules, hypothetical odds and rollover method were frozen before player-event acquisition. StatsBomb contains 131/132 expected fixtures; Tottenham Hotspur Women vs Birmingham City WFC is absent and was not invented.

| Plan | Hits | Fixed odds | $10 flat stake | Return | Profit | ROI |
|---|---:|---:|---:|---:|---:|---:|
| A | 23/28 — 82.1% | 1.50 | $280 | $345 | **+$65** | 23.2% |
| B | 14/15 — 93.3% | 2.00 | $150 | $280 | **+$130** | 86.7% |

The user clarified the intended rollover after the first report: **start at $10 and use `$10 × odds^n` after `n` consecutive wins**. The full accumulated balance is staked again, so the next loss reduces it to $0.

| Plan | Consecutive-win streaks | Highest balance reached | Next result | Final active balance after a new $10 restart |
|---|---|---:|---|---:|
| A at 1.50 | 6, 8, 2, 0, 4, then 3 | **$256.29** after 8 wins | Lost — balance became $0 | $33.75 |
| B at 2.00 | 13, then 1 | **$81,920.00** after 13 wins | Lost — balance became $0 | $20.00 |

The $81,920 was a temporary mathematical balance, not realized profit: the simulation rolled all of it onto the fourteenth B selection and lost. Without a cash-out rule, every completed streak that ends in a loss returns $0. The earlier 2–5 pick block calculations remain saved only as an alternative diagnostic and are no longer labelled as the requested rollover method.

The odds were supplied by the user rather than observed historically. Same-kickoff selections also make a strict live sequence potentially impossible. Selection rules and outcomes were not changed by this accounting correction.

## Previous proof: complete Frauen-Bundesliga 2023/24 stress test

This third A/B plan was frozen before player-event acquisition. The complete 132-match Frauen-Bundesliga season was unused and non-overlapping with every earlier evaluation, and all 4,056 player appearances were preserved.

| Check | A: original | B: >=3 prior shots + >=80 prior minutes |
|---|---:|---:|
| Full season | 15/19 — 78.9% | 3/5 — 60.0% |
| Rounds 1–11 | 3/5 — 60.0% | 1/1 — 100.0% |
| Rounds 12–22 | 12/14 — 85.7% | 2/4 — 50.0% |
| A picks excluded by B | 12/14 — 85.7% | — |

This is important negative evidence for the refinement: B retained only 26.3% of A and was 18.9 percentage points worse. Its paired-week bootstrap interval was **-62.5 to +20.0 points**. With only five B picks, the estimate is highly uncertain, but B did not generalise here and must not replace A as the primary rule.

Pattern A still produced 15/19, broadly consistent with the original environment-first hypothesis. This remains a women's cross-population test—not direct men's MLS proof—and it shares the 2023/24 era and StatsBomb provider with the WSL test.

## Previous completed proof: complete WSL 2023/24 stress test

The second A/B plan was frozen before acquiring player-event outcomes. The complete 132-match FA Women's Super League season was unused by this project and contains 3,984 saved player appearances.

| Check | A: original | B: >=3 prior shots + >=80 prior minutes |
|---|---:|---:|
| Full season | 23/27 — 85.2% | 13/14 — 92.9% |
| Rounds 1–11 | 7/8 — 87.5% | 4/4 — 100.0% |
| Rounds 12–22 | 16/19 — 84.2% | 9/10 — 90.0% |
| A picks excluded by B | 10/13 — 76.9% | — |

B retained 51.9% of A's picks and improved the observed rate by 7.7 percentage points. Its approximate paired-week bootstrap interval for B-minus-A was **-3.12 to +21.43 points**, so this supports the direction but does not establish B as reliably superior. The sample is small: 27 A picks and 14 B picks.

This is a **cross-population stress test in women's football**, not direct proof of a men's MLS betting rate. It is historical, uses the same StatsBomb provider family as the other European tests, assumes the actual starting XI is known, and does not test odds or profit. Do not merge it into the men's validation totals.

All 3,984 appearances, 27 A picks, 14 B picks, exclusions, weekly results, frozen plan, raw source files and integrity checks are saved in `wsl_2023_24_ab_validation/`.

## Recommended next step

### Latest completed validation: Ligue 1

The A/B plan was saved before analysing new player outcomes. A and B remained unchanged. Dataset selection was based on coverage, not outcomes. No match from this season was in the 431-pick refinement-discovery cohort.

| Check | A: original | B: >=3 prior shots + >=80 prior minutes |
|---|---:|---:|
| All available records | 44/55 — 80.0% | 26/29 — 89.7% |
| Complete earlier scheduled rounds only | 24/32 — 75.0% | 14/17 — 82.4% |
| Excluding three most-selected B players | 24/34 — 70.6% | 7/9 — 77.8% |

B retained 52.7% of A's picks. Rejected A picks hit 18/26 (69.2%). The approximate paired-week bootstrap interval for B-minus-A was **-1.33 to +21.30 percentage points**: this does not establish a dependable improvement.

Zlatan Ibrahimovic, Edinson Cavani and Andy Delort accounted for 20 of B's 29 picks. The missing fixture pairings are Troyes–Bordeaux, Bastia–Gazelec Ajaccio, and Saint-Etienne–Paris Saint-Germain. No missing dates or stats were invented. The prior-round sensitivity is conservative and also removes cases where earlier rounds had been postponed.

All 10,479 appearances, both selection flags, exclusions, raw data, coverage checks and weekly results are saved. Do not merge this evaluation into the 431-pick discovery cohort and then describe it as untouched evidence again. Across the baseline discovery and this new evaluation, A has 397/486 hits; keep those cohorts separately reported.

The steps below remain the framework for further confirmation, not a claim that another suitable untouched season has been found.

### 1. Specify two fixed versions before looking at new outcomes

- **A — baseline:** the original home-environment + consistent-main-shooter rule.
- **B — practical challenger:** A plus average >=3 shots and >=80 minutes over the same previous five starts.

Keep the 25% shot-share idea as a secondary hypothesis, not another rule to keep adjusting. Neither refinement has replaced the baseline.

### 2. Find genuinely unused, suitable StatsBomb history

Check season completeness and ordinary home/away competition structure before acquiring it. Choose the dataset for coverage, not because its outcomes look favourable. Prefer another era if a complete compatible season exists. Do not use India, mislabel a selected-team dataset as a full league, or reuse our discovery matches as independent evidence.

If no suitable unused season is available within the source preference, report the gap and agree a prospective paper-test/data-source plan with the user. Do not quietly restart SportsAPI Pro or expand into another competition type.

### 3. Run A and B side by side

Record every eligible fixture and candidate before settlement, including exclusions and unknowns. Report:

- Hits, misses and number of opportunities for each version.
- Weekly and per-league/season rates, with the size of each sample.
- Performance of picks B excludes from A.
- Concentration in a few players or teams and the effect of removing the most-selected players.
- Bad weeks as well as good ones.

Decide the evaluation window and minimum evidence requirement before inspecting results. A higher percentage on a tiny subset is not sufficient to promote B. Do not repeatedly retune after each loss.

### 4. Only then build the weekend scanner

If the evidence supports a stable rule, build a shortlist that ranks environments first, then players. Confirm lineups and log selections prospectively. Keep 1+ shot and 1+ SOT as separate later research targets; do not transfer the 2+ shots hit rate to them.

## Roadmap

| Phase | State |
|---|---|
| 1. Collect and organise history | Main research datasets available; original ticket uncertainties preserved |
| 2. Define the first 2+ shots pattern | Complete: baseline specified and replayed |
| 3. Test consistency and refinements | **Current phase:** two frozen ranked Big Five replications now total 32/40 for home-shot dominance, candidate A 37/44 (84.1%) and B 20/23 (87.0%). B was only 11/14 in the newest season and 5/8 active weekends were completely clean, so it is the primary shortlist but not proven superior; direct prospective confirmation remains pending |
| 4. Build weekend environment/candidate scanner | Historical MLS weekend browser prototype built; current/live data and starter integration incomplete |
| 5. Log and assess fresh selections | **Active:** first prospective shadow weekend locked for 10–11 October 2026; environment snapshot saved before outcomes, lineup selections pending, recurring lineup/settlement checks enabled |
| 6. Develop 1+ shot and 1+ SOT rules | Not tested by the current pattern research |

The older SOT application already contains model/analytics code. That is separate from proving and deploying this newly researched total-shots pattern; the existence of that code does not mean this scanner is ready.

## Cleaning, limitations and original selection history

- All 31,617 appearances across the three European seasons passed the defined duplicate, numerical, starter-count and shot-total checks; none needed quarantine. All 73 downloaded Bundesliga matches passed their checks. Passing consistency checks is not independent verification of every provider observation.
- Raw data is preserved. Unknown values stay unknown. StatsBomb zero-shot counts are derived from the absence of shot events in a downloaded match; SportsAPI missing shots are not filled with zero.
- StatsBomb minutes are derived from merged lineup intervals, rounded up and capped at regulation length. Providers may define minutes or shots differently.
- Historical publication timestamps are not certified. The replay is conditional on knowing the actual starting XI; it does not prove that a pre-lineup forecast would select the same players.
- Observations share fixtures, players, teams and seasons. Simple displayed confidence intervals do not account for all such dependence.
- No historical odds, staking returns or profitability were tested. A high hit rate alone does not establish profitable betting.
- The original ticket report contains 150 assessed 2+ shots groups: 119 hits and 31 misses. These undated report groups are separate from the provider backtests and are NOT added to the 431 picks.
- Preserve the correction: **12 of 15 replacement cases are provisional original-player shot totals**. **Antony, Denis Bouanga and Pep Biel remain unresolved** unless dated evidence resolves them.
- The original Phase 3 matrix contains 51 rows: 31 failures and 20 comparison hits. Dated ticket-to-match links remain unverified. Current-match shot share is diagnostic only, never a pre-match predictor.

## Files to open

All links below are relative to this README in the existing `outputs` folder.

| Artifact | Purpose |
|---|---|
| [Project dashboard](project_site/dist/index.html) | Progress and links to every research stage |
| [MLS 2026 historical weekend scanner](mls_2026_weekends/index.html) | Weekend selector, ranked environments, A/B candidates, outcomes and explicit coverage gaps |
| [MLS internet-source investigation](mls_2026_source_research.md) | Research-agent findings, current fixture/stat sources and exact-replay blockers |
| [Winning-pick research](winning_pattern_research.html) | Ten refinement tests, volume trade-offs and caveats |
| [Winner research data](winning_pattern_research.json) | All 431 picks, pre-match features and filter decisions |
| [New Ligue 1 A/B test](ligue1_2015_16_ab_validation/index.html) | New evaluation, missing-history sensitivity, every sample and complete archive |
| [Complete WSL A/B stress test](wsl_2023_24_ab_validation/index.html) | Frozen-rule replay on 132 unused matches, every sample and complete archive |
| [Complete Frauen-Bundesliga A/B stress test](frauen_bundesliga_2023_24_ab_validation/index.html) | Third frozen replay; important negative evidence against promoting B |
| [WSL 2020/21 rollover backtest](wsl_2020_21_rollover_validation/index.html) | Frozen A/B replay with corrected continuous all-in $10 rollover streaks |
| [Random WSL 2018/19 rollover backtest](random_wsl_2018_19_rollover_validation/index.html) | Audited random draw, frozen A/B replay and continuous $10 rollover streaks |
| [Every-weekend operating simulation](weekend_operation_simulation/index.html) | Saturday/Sunday frequency, picks, hit rates and perfect-weekend rates across five frozen datasets |
| [Recent big-five pre-break test](recent_big5_prebreak_backtest/index.html) | Exact frozen-rule no-bet result caused by the eight-match history gate |
| [Big-five previous-season carryover test](big5_2026_prebreak_carryover/index.html) | Separate early-season variant: 784 source matches, 156 target fixtures, every sample and pick, frozen rules and integrity checks |
| [Big-five carryover replication](big5_2025_carryover_replication/index.html) | Untouched second-season replay: A 6/13 and B 3/5; every sample, exclusion and integrity check |
| [Combined carryover assessment](big5_carryover_combined_assessment.md) | Honest two-season conclusion: combined A 19/29; do not promote the carryover variant yet |
| [Big-five environment rankings](big5_environment_rankings/index.html) | Ranks comparable fixtures even with limited current-season data and displays A/B/C evidence confidence separately |
| [Third-season ranked-candidate validation](big5_2024_ranked_candidate_validation/index.html) | Frozen top-five Tier A/B environment workflow: 20 selected environments, A 19/22, B 9/9, every rank and selection audited |
| [Prospective shadow ledger — 10 October 2026](shadow_testing/2026-10-10/index.html) | Immutable environment snapshot, confirmed-lineup pick locks and later settlement records |
| [Cross-league research](cross_league_research.html) | European comparisons, concentration research and downloads |
| [Clean European samples](cross_league_clean_samples.zip) | 31,617 records plus cleaning/quarantine research |
| [MLS weekly replay](weekly_pattern_replay.html) | Every qualifying pick and calendar week |
| [Premier League](epl_2015_16_validation/index.html) | Season results and all-data archive link |
| [La Liga](laliga_2015_16_validation/index.html) | Season results and all-data archive link |
| [Serie A](seriea_2015_16_validation/index.html) | Season results and all-data archive link |
| [Bundesliga partial batch](bundesliga_2024_25_validation/index.html) | Incomplete recent-season collection, samples and limitations |
| [Original hit/miss report](phase3_hit_miss_report.md) | Original selection-history investigation |
| [Reconciliation](replacement_reconciliation.md) | Replacement-case findings |
| [Integrity corrections](DATA_INTEGRITY_UPDATE.md) | Team attribution and ticket-linkage cautions |
| [Other local history inventory](other_history_screening_report.md) | Duplicate/sparse source coverage |

## Working files and safe continuation

Workspace: `C:\Users\bjpro\Documents\Codex\2026-09-24\referenced-chatgpt-conversation-this-is-an`.

The current scripts live under `work/`:

- `test_home_pattern.py`: shared baseline historical feature/replay logic.
- `weekly_pattern_replay.py`: frozen rule definitions and MLS weekly replay.
- `download_epl_validation.py`: parameterised, cached StatsBomb acquisition.
- `replay_epl_validation.py`: parameterised European season replay; currently assumes a 380-match 2015/16 season. Do not point it at a different season without making the coverage/season assumptions explicit.
- `cross_league_research.py`: European cleaning and concentration analysis.
- `study_winning_picks.py`: ten-filter exploratory comparison; does not alter baseline rules.
- `mls_2026_weekends.py`: Saturday/Sunday Denver-time historical scanner from existing MLS data; midweek matches remain available as prior history. No network requests or new paid calls.
- `ligue1_ab_plan.json` and `validate_ligue1_ab.py`: saved fixed A/B plan and new-dataset evaluation with coverage sensitivity and weekly paired bootstrap.
- `wsl_2023_24_ab_plan.json`, `download_statsbomb_season_standalone.py` and `validate_wsl_ab.py`: frozen complete-season cross-population stress test and reproducible acquisition/replay.
- `frauen_bundesliga_2023_24_ab_plan.json` and `validate_frauen_bundesliga_ab.py`: third frozen test, including the failed B refinement and full audit trail.
- `wsl_2020_21_rollover_plan.json`, `wsl_2020_21_rollover_method_correction.json` and `validate_wsl_2020_rollover.py`: fixed-odds policy, corrected continuous rollover and every streak.
- `random_wsl_2018_19_plan.json` and `validate_random_wsl_2018_rollover.py`: random-selection audit, coverage rejection/redraw and continuous rollover replay.
- `simulate_weekend_operation.py`: Saturday/Sunday-only replay across the frozen validation datasets.
- `download_fotmob_big5_carryover.py`, `validate_big5_carryover.py` and `check_big5_carryover.py`: bounded FotMob acquisition and audited replay for the separate previous-season carryover variant.
- `big5_carryover_replication_plan.json` and `download_fotmob_big5_carryover_replication.py`: frozen second-season carryover replication and bounded acquisition.
- `big5_environment_ranking_spec.json`, `build_big5_environment_rankings.py` and `check_big5_environment_rankings.py`: exploratory environment-ranking layer, confidence tiers, candidate ranks and integrity audit.
- `big5_ranked_candidate_validation_plan.json`, `download_fotmob_ranked_candidate_validation.py`, `validate_big5_ranked_candidates.py` and `check_big5_ranked_candidates.py`: frozen third-season validation of ranking environments first and candidates second.
- `shadow_weekend.py`, `build_possible_lineups.py`, `build_shadow_dashboard.py` and `check_shadow_weekend.py`: prospective environment locking, versioned recent-start possible XIs, confirmed-lineup selection locking, settlement and integrity checks. Possible-XI names remain provisional and are never counted as official picks.
- `download_recent_bundesliga.py`: cached SportsAPI acquisition; **do not run under the current StatsBomb-only preference**.
- `check_*.py` / `check_*.cjs`: data, rule, chronology, link and layout checks.

Some scripts depend on the original SOT project's Python environment/provider adapter and local browser runtime. This is not a standalone packaged application. Do not overwrite unrelated changes in that project.

Verification commands, run from the workspace, which do not fetch provider data:

```powershell
python work/check_winning_research.py
python work/check_weekly_replay.py
python work/check_epl_validation.py --slug epl_2015_16_validation
python work/check_epl_validation.py --slug laliga_2015_16_validation
python work/check_epl_validation.py --slug seriea_2015_16_validation
python work/check_recent_bundesliga.py
python work/check_ligue1_ab.py
python work/check_wsl_ab.py
python work/check_frauen_bundesliga_ab.py
python work/check_wsl_2020_rollover.py
python work/check_random_wsl_2018_rollover.py
python work/check_mls_weekends.py
python work/check_big5_carryover.py
node work/check_mls_weekend_site.cjs
node work/check_winning_site.cjs
```

These checks passed when their corresponding artifacts were generated. Read the current files before resuming; do not restart the project or duplicate a prior dataset as new evidence.

Data sources: [StatsBomb Open Data](https://github.com/statsbomb/open-data), [FotMob](https://www.fotmob.com/) public match pages/data for the new carryover replay, and the previously configured [SportsAPI Pro](https://sportsapipro.com/) feed. Respect source attribution and licensing when sharing the data or research.
