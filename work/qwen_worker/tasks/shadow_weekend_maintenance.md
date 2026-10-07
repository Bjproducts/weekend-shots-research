# Maintain the current prospective shadow weekend

First read:

- `outputs/README.md`
- `work/shadow_weekend.py`
- `work/build_possible_lineups.py`
- `work/build_shadow_dashboard.py`
- the manifest and immutable environment snapshot under the currently active `outputs/shadow_testing/<weekend>/` directory

Determine the currently locked weekend from existing project state. Do not choose a different weekend when a locked, unsettled weekend exists.

Then perform only the applicable existing workflow steps:

1. Run the existing lineup check. Lock official selections only when a complete confirmed home starting XI is available and the fixture has not started.
2. Run the existing settlement check only for finished fixtures with official locked selections.
3. Rebuild the existing shadow dashboard only if a lock or settlement changed.

Restrictions:

- Never edit strategy thresholds or derive rules from outcomes.
- Never overwrite or edit an existing environment snapshot, manifest, confirmed-lineup lock, settlement, or versioned possible-lineup file.
- Do not count possible-lineup candidates as official picks.
- Keep Tier C informational only.
- If an existing validation fails, stop and report it; do not repair immutable records.
- Do not create a new environment snapshot as part of this task.
- Stay within the existing FotMob-based workflow and sources already approved by the project.

In the completion report, clearly separate provisional possible-lineup candidates, confirmed-lineup locked picks, and settled outcomes. If nothing changed, say so concisely.

