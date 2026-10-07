# MLS 2026 source research

Checked 2026-09-27. Read-only public-source investigation; no paid API, account, credentials, production mutation, or scheduled job used.

## Outcome

**American Soccer Analysis (ASA) is a practical, documented free source for current MLS completed fixtures and per-match player shots.** Its current public API returned **401 completed 2026 regular-season games**, from **2026-02-21 19:30 UTC through 2026-09-27 02:30 UTC**. This is retrieved coverage, not proof that every expected fixture has complete statistics. An exact unchanged A/B replay still needs starter status and comparable minutes.

## Verified sources

| Source | Actual access / coverage checked | Limitations |
|---|---|---|
| [StatsBomb competition catalogue](https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json) | Only MLS 2023 listed. [Match JSON](https://raw.githubusercontent.com/statsbomb/open-data/master/data/matches/44/107.json) contains six games, August 27–October 22, 2023. | No MLS 2026. A 2026 update timestamp on old games is not a 2026 season. |
| [ASA public API documentation](https://app.americansocceranalysis.com/api/v1/__docs__/) and [OpenAPI specification](https://app.americansocceranalysis.com/api/v1/openapi.json) | Readable anonymously; games, players, teams, game-level xGoals and shots endpoints. | No documented lineup or starter endpoint found. Respect rate limits and cache responses. |
| [ASA 2026 completed regular-season games](https://app.americansocceranalysis.com/api/v1/mls/games?season_name=2026&status=FullTime&stage_name=Regular%20Season) | 401 games; IDs, UTC kickoff, home/away IDs, scores, status, expanded minutes, last-updated UTC. | Season ongoing; require actual cutoff and compare fixture coverage. Last-updated timestamp is not the original publication time. |
| [ASA player-game sample, September 24](https://app.americansocceranalysis.com/api/v1/mls/players/xgoals?start_date=2026-09-24&end_date=2026-09-24&split_by_games=true&split_by_teams=true&minimum_minutes=0&minimum_shots=0&minimum_key_passes=0) | 32 appearances for game Vj589JB3q8: player/game/team IDs, position, minutes, shots, SOT, goals. Includes zero-shot appearances. | No started flag. Full-game minutes observed as 98: expanded/stoppage-inclusive, not automatically equivalent to nominal 90-minute provider records. |
| [ASA team-game sample](https://app.americansocceranalysis.com/api/v1/mls/teams/xgoals?start_date=2026-09-24&end_date=2026-09-24&split_by_games=true) | Team/game IDs, shots for/against, goals, points. | Validate sums against player rows and zero-shot player inclusion; not yet full-season audited. |
| [Official MLS schedule](https://www.mlssoccer.com/schedule/) | Current 2026 fixture list and completed-game links accessible in search index. | Some pages return client-rendered shells to text extraction; not a verified bulk data export. Dates displayed can be UTC rather than local weekend dates. |
| [Official Columbus–Red Bull New York September 12 stats](https://www.mlssoccer.com/competitions/mls-regular-season/2026/matches/clbvsrbny-09-12-2026/stats) / [feed](https://www.mlssoccer.com/competitions/mls-regular-season/2026/matches/clbvsrbny-09-12-2026/feed) | Completed 2026 match confirmed; search index exposes team shots and event commentary. Direct HTML contains match and team identity metadata. | Direct stats extraction returned a JS shell. Search-index team shots/SOT disagree with other match sources; unsuitable to silently merge. |

## Why ASA is suitable for collection

ASA explicitly provides a [public API client](https://github.com/American-Soccer-Analysis/itscalledsoccer) and explains [programmatic access and attribution](https://www.americansocceranalysis.com/home/2022/2/9/introducing-itscalledsoccer). Its [app](https://app.americansocceranalysis.com/) supports downloading data. This is preferable to reverse-engineering private endpoints or working around blocks.

Read the documented client paging behavior: it handles 1,000-row responses with offsets. A season-wide player query must not be mistaken for complete merely because one request succeeds. A bounded date-by-date/week-by-week fetch with manifest, cache and row counts is easier to audit. Query all appearances with zero minimum filters, not only shooters.

Additional checked endpoints:

- `/mls/players`: player-ID/name lookup; use stable IDs, not fuzzy name-only joins.
- `/mls/teams`: team lookup (documented; full payload not inspected in this investigation).
- `/mls/games/periods?game_id=Vj589JB3q8`: first-half expanded 0–46, second-half expanded 46–98; useful for clock semantics but not individual starts/substitution times.
- `/mls/games/game-flow?game_id=Vj589JB3q8`: per-minute team values, not individual lineup data.

## Exact-replay limitations and next steps

1. Cache the ASA game manifest, player-game and team-game records with source URLs, retrieval timestamps, hashes, pagination counts and exclusions. Keep original raw values.
2. Reconcile expected completed fixtures against the official schedule, excluding future, unplayed and out-of-scope competitions. Use one declared local time zone for weekend grouping.
3. Obtain trustworthy starters and substitution clocks from accessible official match reports/lineups or existing local records with verified match identity. **Do not infer starters from minutes played.**
4. Preserve expanded minutes separately. The B rule's prior-five-start average of 80 minutes cannot silently use stoppage-inclusive minutes if earlier tests used nominal minutes. Period length alone cannot determine player nominal minutes for substituted players.
5. Run unchanged A/B only for sufficiently complete history. Until starts/minutes are reconciled, ASA provides shooting/team-environment data but not an exact full-pattern validation. Missing records must remain unknown/excluded, not zero.
6. Prior MLS records may already have been examined during discovery. Label overlap; only newly unexamined match periods are additional holdout evidence. This is retrospective chronological replay, not proof of original pre-kickoff data availability.

## Concrete source conflict

For Columbus–Red Bull New York, September 12, 2026, the official MLS stats search extract showed Columbus 13 shots/3 SOT, while the official match-page recap said 12 shots. The indexed [FBref match report](https://fbref.com/en/matches/20a34111/Columbus-Crew-Red-Bull-New-York-September-12-2026-Major-League-Soccer) showed 12/4. Direct FBref opens failed in the web tool. These are evidence of differing/revised source counters, not a resolved truth. Do not combine their numerators/denominators or use a narrative recap to override structured records without reconciliation.

## Archived data from this investigation

The follow-up bounded download is complete in `outputs/mls_2026_sources/`:

- `asa_games_2026.json`: 401 completed regular-season fixture records, with separate source URL/retrieval timestamp/SHA-256 metadata.
- 32 seven-day-or-shorter player response files: **12,361 appearance records**, **12,361 unique game/team/player keys**, **zero duplicate keys**, covering **all 401 retrieved completed fixture IDs**; no unmatched or missing game IDs.
- **6,788 zero-shot appearances** retained. This confirms zero-shot rows were not filtered away; it does not establish full lineup completeness.
- Each weekly response was below the documented client's 1,000-row paging boundary (largest 928), so no offset page was required. The downloader supports offsets if a window reaches that boundary.
- `asa_player_coverage_2026.json`: machine-readable counts and per-file manifest. Scope cutoff **2026-09-27 12:03:26 UTC**; latest archived kickoff was 02:30 UTC that day. Raw retrieval metadata timestamps are preserved separately.
- Reproducible cached downloader: `work/cache_asa_2026.py`.

Official lineup text checks for [St. Louis–Toronto September 19](https://www.stlcitysc.com/competitions/mls-regular-season/2026/matches/stlvstor-09-19-2026/lineups) and [Charlotte–Red Bull March 21](https://www.mlssoccer.com/competitions/mls-regular-season/2026/matches/cltvsrbny-03-21-2026/lineups) returned shells rather than usable starting-XI tables. No access bypass was attempted.

**These new raw records are not a new A/B performance result.** Starter status and nominal-minute comparability are still unresolved; the records remain separate from the model-ready historical replay dataset. No recurring monitoring was created.
