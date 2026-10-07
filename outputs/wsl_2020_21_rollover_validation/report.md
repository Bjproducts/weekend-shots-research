# Frozen WSL 2020/21 backtest + $10 rollover simulation

Coverage: 131/132 expected matches. Missing pairing: Tottenham Hotspur Women vs Birmingham City WFC. No data invented.

A: 23/28 (82.1%) at hypothetical decimal odds 1.50. B: 14/15 (93.3%) at hypothetical decimal odds 2.00.

## Betting results

| Strategy | Staked | Returned | Profit | ROI |
|---|---:|---:|---:|---:|
| A flat $10 | $280.00 | $345.00 | $65.00 | 23.2% |
| B flat $10 | $150.00 | $280.00 | $130.00 | 86.7% |

## Continuous rollover — corrected user definition

| Plan | Outcome sequence | Winning streaks | Maximum balance | What happened next | Final active balance after restarts |
|---|---|---|---:|---|---:|
| A at 1.50 | `WWWWWWLWWWWWWWWLWWLLWWWWLWWW` | 6, 8, 2, 0, 4, then 3 | $256.29 after 8 wins | Next pick lost it | $33.75 after final 3 wins |
| B at 2.00 | `WWWWWWWWWWWWWLW` | 13, then 1 | $81920.00 after 13 wins | Next pick lost it | $20.00 after restarting and winning once |

**This is the actual rollover formula requested:** `$10 × odds^number of consecutive wins`. If the next bet loses and the whole balance was staked, that streak ends at $0. The maximum balance is not realized profit unless it is cashed out before the loss.

## Alternative fixed-size block diagnostics (not the user-defined continuous rollover)

| A 2-selection block | $140.00 | $225.00 | $85.00 | 60.7% |
| A 3-selection block | $90.00 | $168.75 | $78.75 | 87.5% |
| A 4-selection block | $70.00 | $151.89 | $81.89 | 117.0% |
| A 5-selection block | $50.00 | $151.88 | $101.88 | 203.8% |
| B 2-selection block | $70.00 | $240.00 | $170.00 | 242.9% |
| B 3-selection block | $50.00 | $320.00 | $270.00 | 540.0% |
| B 4-selection block | $30.00 | $480.00 | $450.00 | 1500.0% |
| B 5-selection block | $30.00 | $640.00 | $610.00 | 2033.3% |

Each rollover uses non-overlapping chronological blocks. A block wins only if every selection hits; the entire return is rolled through the block. Incomplete final blocks are ignored.

**Important:** some blocks contain selections with the same kickoff and therefore may not have been executable sequentially. These figures are mathematical diagnostics. The supplied fixed odds are not historical prices.

## Limits

- One expected fixture is absent; no missing date or result was invented.
- Fixed odds are hypothetical user inputs, not historical market prices.
- Rollover blocks use deterministic selection order and can contain simultaneous selections; they are mathematical simulations, not necessarily executable live sequences.
- No commission, limits, voids, stake caps or bookmaker settlement differences. Historical replay assumes actual starters are known.
- Women's football and repeated StatsBomb data do not directly validate men's MLS. No retuning after outcomes.
