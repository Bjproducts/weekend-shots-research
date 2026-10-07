# Data integrity update — 26 September 2026

The attribution corrections, timing safeguards and ticket-reference audit are complete. No missing football statistics, dated ticket links or source timestamps were invented. No production model was retrained and no database migration or canonical database edit was performed.

## Research matrix corrections

Team-shot lookup now requires both report fixture ID and the player's recorded team. Previously the same fixture-level total could be attached to opposing players.

| Record | Previous team shots / share | Corrected value | Reason |
|---|---|---|---|
| Marcus Ingvartsen, F130 | 9 / 0% | Unknown / Unknown | The saved 9-shot evidence belongs to Colorado; Ingvartsen's recorded team is San Diego. |
| Harry Kane, F222 | 15 / 6.67% | Unknown / Unknown | The saved 15-shot evidence belongs to Argentina; Kane's recorded team is England. |
| Rafael Navarro, F130 | 9 / 11.11% | Retained | Matches the recorded Colorado team context. |
| Lionel Messi, F222 | 15 / 6.67% | Retained | Matches the recorded Argentina team context. |

The two removed denominators were outside the same-player comparison subset. Its descriptive means remain 13.2 team shots / 29.2% personal share for 15 hits with context and 11.5 / 9.0% for 8 misses with context. These are candidate-match, outcome-selected observations. Personal shot share includes the outcome numerator, so this difference cannot establish predictive value. The denominator is full-match team shots, not team shots while the player was on the pitch.

The 51-row matrix now explicitly includes ticket references, source page, ticket-match verification status, denominator basis and team-context identity. Hit dates are labelled candidate fixture dates; earlier wording that implied ticket identity was resolved has been removed. The dashboard displays the correction and the remaining linkage requirement.

## Ticket-to-match audit

All **51/51** matrix records have supporting references to the saved raw selections, matched by ticket, fixture pairing, original selected identity and Shots/2+ market. This verifies report provenance only.

**0/51 dated match links are independently verified.** The saved raw tickets have `id`, `status`, `stake` and `type`; their selection rows contain no match date or provider fixture ID. A candidate match found elsewhere does not supply the missing ticket date. See [the structured link audit](ticket_match_link_audit.json) for each record and the evidence needed.

To verify those links, the required source is a dated original ticket or individual-leg record that identifies the fixture and selected player, followed by a provider fixture-ID match. No selection is silently promoted to a verified dated observation.

Twelve of fifteen replacement cases remain provisional original-player totals. Antony, Denis Bouanga and Pep Biel remain unresolved. The original reported counters and original failure dataset were preserved.

## Timing and split safeguards

Changes were made in the original `C:/Users/bjpro/OneDrive/Desktop/SHOT ON TARGET/backend`:

- `app/analytics/models.py`: `MatchStatLine` can carry optional verified `completed_at` and `available_at`; invalid or timezone-naive metadata is rejected.
- `app/analytics/discovery.py`: `PreMatchFeatureBuilder(strict_availability=True)` excludes history with missing completion/availability metadata or timestamps after the cutoff. Known delayed timestamps are respected even in retrospective mode. Equal-kickoff outcome isolation remains intact.
- Upcoming feature construction accepts an actual `as_of` analysis time, defaults to the current UTC time, and caps it strictly before target kickoff. It no longer assumes information through the future target kickoff was already available at analysis time.
- Historical output states its timing policy: `retrospective_kickoff_only` or `strict_history_availability`. The latter describes historical-stat availability checks, not a certification of archived pre-match lineups or all model inputs.
- `app/analytics/dataset.py`: exported records include timing policy; retrospective datasets carry an explicit warning.
- `app/analytics/patterns.py`: season-based holdout is used only when other seasons end before the held-out season starts. Otherwise the splitter uses global chronological kickoff blocks, keeping simultaneous matches together.
- `app/analytics/league_research.py` and `app/services/fixture_previews.py`: retrospective history cannot establish live readiness/qualification, including when an old stored league flag says READY. Preview methodology explains the limitation.

Existing database imports do not yet provide verified completion/publication timestamps through the repository. Consequently, existing research remains explicitly retrospective; strict mode must exclude records lacking metadata. No historical timestamp was backfilled from kickoff or guessed from match duration. Future ingestion/versioned provenance work is necessary before strict historical replay or live readiness can be claimed. The strict guard is implemented and tested; the missing source evidence is still missing.

For safety, no existing database readiness records were rewritten. Runtime qualification checks prevent stale flags from bypassing the new guard. Actual model predictions and past outcomes were not recalculated by this task.

## Verification

- Entire original backend suite: **308 tests passed**.
- Ruff checks passed for all changed Python source/test files.
- Mypy checks passed for the six changed backend source modules.
- Research regression checks passed for fixture/team attribution, computed shares, ticket references, all 51 provisional links and unresolved replacement preservation.
- Dashboard checks passed for 31 failure cases, 15 replacement cases, 11 comparison groups, report links, expandable records and desktop/mobile overflow checks.

New checks cover unknown/late completion and publication times, analysis-time cutoff, invalid timestamps, overlapping-season splits and stale readiness flags. The test suite uses test fixtures; passing it does not verify the source football facts.

## Next evidence step

Collect dated ticket/leg exports for the unresolved joins, and obtain verified observation/completion metadata for historical provider records. Then re-run linkage and timing checks before testing pre-match shot-share or environment hypotheses. More agent implementation is not required to do that work.

Updated outputs: [Phase 3 report](phase3_hit_miss_report.md), [matrix JSON](phase3_hit_miss_matrix.json), [matrix CSV](phase3_hit_miss_matrix.csv), [dashboard](project_site/dist/index.html).
