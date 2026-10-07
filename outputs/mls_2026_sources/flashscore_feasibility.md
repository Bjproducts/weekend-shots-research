# Flashscore feasibility check — 27 September 2026

## Result

Three completed MLS 2026 matches were readable in the public browser without login or bypass: Toronto–Charlotte August 19, St. Louis–Toronto September 19 local, and Orlando–Toronto September 12. Explicit starting lineups, substitution information, player shots and Minutes played tables are available in these samples. This establishes small-scale feasibility, **not season-wide collection or a new backtest**.

`flashscore_feasibility.json` preserves source links, all 66 starting-name entries and 13 partial player examples. Player examples illustrate source fields, not model selections; never calculate model performance from them. They are a convenience sample involving Toronto, not representative league-wide validation. Dashes remain unknown. Raw source labels are retained; cross-provider player IDs are not yet matched.

## Important cleaning decisions

- Use the explicit Starting Lineups section, never infer starts from minutes.
- Flashscore's General player-stat table has nominal-looking minutes (full game 90), unlike ASA expanded minutes. But values need comparison with the original provider: Dorsch at 90+5 is listed as 89 minutes, and Holse at 90+1 as 89. Preserve these values and substitution clocks separately.
- Match by verified home/away identities and UTC kickoff. St. Louis–Toronto has a September 20 header but September 19 displayed local kickoff.
- Preserve ASA shots and Flashscore shots in separate fields until matched and reconciled. Do not overwrite conflicts.
- Existing original-ticket replacement corrections stay unchanged; this dated Biel appearance does not resolve the undated case.

## Next bounded test

Target August 22–23, 2026 in America/Denver: the first weekend after the saved replay's latest match. Freeze A/B rules. Before settlement, assemble every MLS fixture in the weekend, all eligible home starters, and enough previous starts to rank the top two fairly. Include relevant midweek matches and preserve the 24-hour history buffer. Do not select only the players whose later shots look good.

First reconcile several **overlapping older matches** against the existing database for player identity, starts, minutes and shot counts. Then fill the target weekend and missing history. Run only after a coverage audit; otherwise report unknown/excluded fixtures, not losses or no-pick weekends. Record every candidate and rejection reason, then report A/B wins, losses, sample sizes and fixture counts. Keep inspected source samples separate from pristine holdout claims.

No model changes, new win-rate claim, paid requests or automation. Browser tab clicks were unreliable; reading observed destination links and navigating to those public pages worked. No bulk exporter was verified.
