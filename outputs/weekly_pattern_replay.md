# Fixed-rule weekly backtest

Completed retrospective replay of the existing MLS sample. Rules unchanged; no threshold optimisation. This breaks the earlier result into weeks, not a new independent sample.

| Version | All picks | Later picks | Active weeks | Active weeks below 70% |
|---|---:|---:|---:|---:|
| full_pattern | 150/185 (81.1%) | 46/57 (80.7%) | 44 | 12 |
| benchmark | 523/660 (79.2%) | 152/184 (82.6%) | 53 | 8 |

## Year-by-year stability

| Year | Full pattern | Consistent-shooter benchmark |
|---|---:|---:|
| 2024 | 19/23 (82.6%) | 75/88 (85.2%) |
| 2025 | 96/117 (82.1%) | 321/419 (76.6%) |
| 2026 | 35/45 (77.8%) | 127/153 (83.0%) |

## Meaning

The full pattern remains promising, but the home-environment filter has not demonstrated additional value beyond consistent main shooters in later matches. Both versions use eligible HOME starters; the benchmark is not an all-home-and-away player pool.
The environment filtered out 373/475 (78.5%) overall and 106/127 (83.5%) in the later period. These are disjoint from the full-pattern picks; the benchmark includes both groups.

## Replay rules and limitations

- Full pattern: home side stronger on season and last-five PPG; home venue shots >=12, away venue shots conceded >=12, home shot proxy exceeds away; top-two eligible home starters by prior shots per start; prior five-start average minutes >=70; at least four of five starts with 2+ shots.
- At least eight saved season results and three venue matches per team. Player history: five starts in 180 days, same team/competition. Rank ties use earlier shot share then ID. No threshold changes.
- Monday–Sunday UTC weeks, including zero-pick weeks. Histories roll forward at each match with a >24-hour buffer. This is a lineup-time replay, not a Saturday-morning shortlist: actual starting status is assumed available.
- Current results never enter selection. Personal and team features independently checked against read-only source records. Actual publication timestamps and historic lineup announcements are not available, so live availability cannot be certified.
- All qualifying picks appear in the JSON/HTML ledger. Missing outcomes stay unknown and are not losses. No odds or return calculations.
- Saved match coverage is incomplete; a zero-pick week does not prove zero opportunities in the full league. Offseason/gaps remain visible. Short weeks can have very volatile rates; picks share players and fixtures.
- Later period starts 2025-10-26 and was already examined. Freeze both variants for fresh forward testing. Existing replacement reconciliation is unchanged.

## Every week

| Week starting (UTC) | Saved finished MLS fixtures | Eligible fixtures | Full pattern | Benchmark |
|---|---:|---:|---:|---:|
| 2024-09-16 | 27 | 10 | 1/1 (100.0%) | 8/8 (100.0%) |
| 2024-09-23 | 14 | 12 | 1/1 (100.0%) | 6/8 (75.0%) |
| 2024-09-30 | 28 | 28 | 9/9 (100.0%) | 20/22 (90.9%) |
| 2024-10-07 | 2 | 2 | — | — |
| 2024-10-14 | 14 | 14 | 4/7 (57.1%) | 13/17 (76.5%) |
| 2024-10-21 | 5 | 5 | 3/3 (100.0%) | 4/4 (100.0%) |
| 2024-10-28 | 12 | 12 | 1/2 (50.0%) | 12/14 (85.7%) |
| 2024-11-04 | 5 | 5 | — | 5/6 (83.3%) |
| 2024-11-11 | 0 | 0 | — | — |
| 2024-11-18 | 4 | 4 | — | 3/5 (60.0%) |
| 2024-11-25 | 2 | 2 | — | 2/2 (100.0%) |
| 2024-12-02 | 1 | 1 | — | 2/2 (100.0%) |
| 2024-12-09 | 0 | 0 | — | — |
| 2024-12-16 | 0 | 0 | — | — |
| 2024-12-23 | 0 | 0 | — | — |
| 2024-12-30 | 0 | 0 | — | — |
| 2025-01-06 | 0 | 0 | — | — |
| 2025-01-13 | 0 | 0 | — | — |
| 2025-01-20 | 0 | 0 | — | — |
| 2025-01-27 | 0 | 0 | — | — |
| 2025-02-03 | 0 | 0 | — | — |
| 2025-02-10 | 0 | 0 | — | — |
| 2025-02-17 | 14 | 0 | — | — |
| 2025-02-24 | 15 | 0 | — | — |
| 2025-03-03 | 16 | 0 | — | — |
| 2025-03-10 | 15 | 0 | — | — |
| 2025-03-17 | 14 | 0 | — | — |
| 2025-03-24 | 15 | 0 | — | — |
| 2025-03-31 | 15 | 0 | — | — |
| 2025-04-07 | 15 | 0 | — | — |
| 2025-04-14 | 15 | 11 | 3/3 (100.0%) | 11/12 (91.7%) |
| 2025-04-21 | 14 | 14 | 4/5 (80.0%) | 13/16 (81.2%) |
| 2025-04-28 | 16 | 15 | 3/3 (100.0%) | 10/13 (76.9%) |
| 2025-05-05 | 15 | 15 | 2/3 (66.7%) | 13/17 (76.5%) |
| 2025-05-12 | 27 | 27 | 8/9 (88.9%) | 22/30 (73.3%) |
| 2025-05-19 | 16 | 16 | 4/5 (80.0%) | 10/13 (76.9%) |
| 2025-05-26 | 26 | 26 | 10/16 (62.5%) | 15/26 (57.7%) |
| 2025-06-02 | 3 | 3 | 3/3 (100.0%) | 3/3 (100.0%) |
| 2025-06-09 | 15 | 15 | 2/2 (100.0%) | 7/14 (50.0%) |
| 2025-06-16 | 0 | 0 | — | — |
| 2025-06-23 | 24 | 24 | 1/2 (50.0%) | 11/15 (73.3%) |
| 2025-06-30 | 15 | 15 | 4/6 (66.7%) | 13/18 (72.2%) |
| 2025-07-07 | 17 | 17 | 2/4 (50.0%) | 10/17 (58.8%) |
| 2025-07-14 | 28 | 28 | 6/7 (85.7%) | 25/28 (89.3%) |
| 2025-07-21 | 14 | 14 | 3/3 (100.0%) | 15/16 (93.8%) |
| 2025-07-28 | 0 | 0 | — | — |
| 2025-08-04 | 12 | 12 | — | 11/14 (78.6%) |
| 2025-08-11 | 16 | 16 | 4/4 (100.0%) | 12/15 (80.0%) |
| 2025-08-18 | 15 | 15 | 3/3 (100.0%) | 12/16 (75.0%) |
| 2025-08-25 | 11 | 11 | 0/1 (0.0%) | 10/13 (76.9%) |
| 2025-09-01 | 5 | 5 | 1/2 (50.0%) | 4/6 (66.7%) |
| 2025-09-08 | 15 | 15 | 1/1 (100.0%) | 9/11 (81.8%) |
| 2025-09-15 | 17 | 17 | 2/4 (50.0%) | 13/18 (72.2%) |
| 2025-09-22 | 18 | 18 | 3/3 (100.0%) | 14/17 (82.4%) |
| 2025-09-29 | 15 | 15 | 6/6 (100.0%) | 9/13 (69.2%) |
| 2025-10-06 | 7 | 7 | 4/4 (100.0%) | 6/7 (85.7%) |
| 2025-10-13 | 15 | 15 | 4/4 (100.0%) | 15/16 (93.8%) |
| 2025-10-20 | 5 | 5 | 2/2 (100.0%) | 7/8 (87.5%) |
| 2025-10-27 | 11 | 11 | 5/5 (100.0%) | 9/12 (75.0%) |
| 2025-11-03 | 6 | 6 | 2/2 (100.0%) | 4/4 (100.0%) |
| 2025-11-10 | 1 | 1 | 1/1 (100.0%) | 1/1 (100.0%) |
| 2025-11-17 | 2 | 2 | — | 1/3 (33.3%) |
| 2025-11-24 | 4 | 4 | 3/4 (75.0%) | 4/5 (80.0%) |
| 2025-12-01 | 1 | 1 | — | 2/2 (100.0%) |
| 2025-12-08 | 0 | 0 | — | — |
| 2025-12-15 | 0 | 0 | — | — |
| 2025-12-22 | 0 | 0 | — | — |
| 2025-12-29 | 0 | 0 | — | — |
| 2026-01-05 | 0 | 0 | — | — |
| 2026-01-12 | 0 | 0 | — | — |
| 2026-01-19 | 0 | 0 | — | — |
| 2026-01-26 | 0 | 0 | — | — |
| 2026-02-02 | 0 | 0 | — | — |
| 2026-02-09 | 0 | 0 | — | — |
| 2026-02-16 | 13 | 0 | — | — |
| 2026-02-23 | 15 | 0 | — | — |
| 2026-03-02 | 16 | 0 | — | — |
| 2026-03-09 | 15 | 0 | — | — |
| 2026-03-16 | 15 | 0 | — | — |
| 2026-03-23 | 0 | 0 | — | — |
| 2026-03-30 | 15 | 0 | — | — |
| 2026-04-06 | 14 | 0 | — | — |
| 2026-04-13 | 15 | 0 | — | — |
| 2026-04-20 | 26 | 20 | 4/9 (44.4%) | 17/22 (77.3%) |
| 2026-04-27 | 15 | 14 | 4/5 (80.0%) | 11/15 (73.3%) |
| 2026-05-04 | 10 | 9 | 3/3 (100.0%) | 6/7 (85.7%) |
| 2026-05-11 | 29 | 29 | 5/7 (71.4%) | 19/24 (79.2%) |
| 2026-05-18 | 15 | 15 | 4/4 (100.0%) | 17/18 (94.4%) |
| 2026-05-25 | 1 | 1 | — | 1/1 (100.0%) |
| 2026-06-01 | 0 | 0 | — | — |
| 2026-06-08 | 0 | 0 | — | — |
| 2026-06-15 | 0 | 0 | — | — |
| 2026-06-22 | 0 | 0 | — | — |
| 2026-06-29 | 0 | 0 | — | — |
| 2026-07-06 | 0 | 0 | — | — |
| 2026-07-13 | 5 | 5 | 1/2 (50.0%) | 2/5 (40.0%) |
| 2026-07-20 | 30 | 30 | 7/7 (100.0%) | 28/31 (90.3%) |
| 2026-07-27 | 15 | 15 | 3/3 (100.0%) | 15/17 (88.2%) |
| 2026-08-03 | 1 | 1 | — | 2/2 (100.0%) |
| 2026-08-10 | 13 | 13 | 4/5 (80.0%) | 9/11 (81.8%) |
| 2026-08-17 | 2 | 2 | — | — |
