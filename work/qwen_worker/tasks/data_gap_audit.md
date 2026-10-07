# Audit data gaps without collecting new data

First read:

- `outputs/README.md`
- schemas, manifests, and summary files directly referenced by that README
- collector and normalization scripts under `work/` only when referenced by those summaries

Do not download data and do not edit files.

Produce a compact inventory of:

1. fields required by the frozen environment and player-selection formulas,
2. fields already available by league/season/source,
3. fields that are missing, stale, or low-confidence,
4. the smallest on-demand retrieval task that could fill each gap,
5. which gaps block official prospective picks versus only optional research.

Use counts and schemas rather than raw rows. Identify any possible look-ahead leakage or missing source timestamps. Do not propose changing the formula to fit available data.
