# Phase 3 — Hit vs Miss Matrix

Updated 26 September 2026. Research revision: attribution and ticket-linkage audit.

The matrix contains **51 rows**: all **31 saved failure records** plus **20 successful selections** for the **11 players** who also have a failure under the corrected selected-player identity. Repeated ticket appearances are not counted as new observations.

## Same-player coverage

| Player | Miss rows | Hit rows | Miss status |
|---|---:|---:|---|
| Ante Budimir | 1 | 1 | reported_miss |
| Antony | 1 | 2 | unresolved_original_player |
| Guilherme Augusto | 1 | 1 | reported_miss |
| Joao Pedro | 1 | 2 | reported_miss |
| Kristoffer Velde | 1 | 4 | provisional_reconciled |
| Lionel Messi | 1 | 2 | reported_miss |
| Omar Marmoush | 1 | 1 | provisional_reconciled |
| Pep Biel | 1 | 2 | unresolved_original_player |
| Petar Musa | 1 | 2 | reported_miss |
| Rafael Navarro | 1 | 1 | reported_miss |
| Simon Becher | 1 | 2 | provisional_reconciled |

## Early repeated differences

- **Observation:** The supported within-player totals separate sharply by construction: saved hits average 4.00 shots; the nine same-player misses with supported counters average 0.89.
  **Status:** Descriptive only. This confirms the comparison cohort but does not identify a pre-match cause.
- **Observation:** Long minutes did not guarantee 2+ shots: at least five same-player misses have supported 90-minute appearances (Joao Pedro, Ante Budimir, Rafael Navarro, Guilherme Augusto and Lionel Messi).
  **Status:** Hypothesis: opportunity quality, team volume and player share may matter more than minutes after a basic playing-time threshold. Hit-side context is still missing, so this is not yet tested.
- **Observation:** Supported team context now covers 15 hits and 8 same-player misses. Hit teams averaged 13.2 shots and selected players averaged a 29.2% share; misses averaged 11.5 team shots and a 9.0% player share.
  **Status:** Descriptive only: post-match share contains the outcome numerator, so separation is partly induced by selecting hits and misses. Test lagged pre-match share on verified dated records before claiming predictive value. Denominator is full-match team shots, not on-field shots.
- **Observation:** A goal or creative return did not ensure repeated shooting: Ante Budimir scored with his only shot; Joao Pedro had a goal and assist from one shot; Lionel Messi had two assists from one shot.
  **Status:** Hypothesis: avoid using goals or general attacking involvement as a substitute for shot-volume evidence.

## Evidence limits

- Antony, Denis Bouanga and Pep Biel remain unresolved. Twelve of 15 replacement counters are only provisional original-player totals.
- All 20 successful rows have candidate fixture dates; 20 have candidate-match minutes and 15 have candidate-match team shots/share. No ticket-to-match link is independently verified.
- Candidate dates on hits and misses are not confirmed ticket dates. Every row retains source page and ticket references. Unknown fields remain explicitly marked `Unknown`.
- Removed unsupported team totals for Marcus Ingvartsen F130 and Harry Kane F222. Team context now requires fixture AND team identity; those opposing-team totals and shares remain Unknown. Same-player aggregate means are unchanged.
- The next valid test is completing hit-side minutes, team shots/share and role coverage, followed by paired/descriptive comparisons. No formula or model is justified yet.
