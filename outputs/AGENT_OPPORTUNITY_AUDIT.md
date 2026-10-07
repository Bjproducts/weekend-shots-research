# Agent opportunity audit

Audit date: 26 September 2026. Scope: architecture and reuse assessment only. No agents implemented; no application code, research records, model settings, or database contents changed.

## 1. What actually exists

Three related local systems were located. Paths below define the aliases used throughout all three audit documents.

| Alias | Absolute root | Observed purpose |
|---|---|---|
| SOT | `C:/Users/bjpro/OneDrive/Desktop/SHOT ON TARGET` | Original FastAPI/SQLAlchemy/Python analytics application with a Next.js frontend, ingestion, feature discovery, model training and evaluation code. |
| TL | `C:/Users/bjpro/Documents/Codex/2026-09-14/files-pasted-by-the-user-build/outputs/soccer-analytics` | Newer Touchline Next.js/TypeScript/PostgreSQL dashboard with deterministic evidence filters for 1+ shot, 2+ shots and 1+ SOT, official lineup refresh, saved picks and settlement. |
| R | `C:/Users/bjpro/Documents/Codex/2026-09-23/referenced-chatgpt-conversation-this-is-an` | Selection-history extraction, replacement reconciliation, failure research and Phase 3 Hit vs Miss matrix. |
| M | `C:/Users/bjpro/Documents/Codex/2026-09-24/referenced-chatgpt-conversation-this-is-an/outputs` | Mirrored research deliverables, current browser dashboard and these audit documents. |

TL documents/import scripts show a historical export from SOT into TL. No ongoing shared service, unified identity mapping or automatic synchronization between SOT, TL and R was found. R's report fixture IDs are not official fixture IDs. Do not join these stores on names or fixture labels alone.

The original repository already contains `LogisticSotModel`, chronological pattern discovery, walk-forward evaluation and ranking. The earlier statement that no model exists applies to the Phase 3 research workspace and TL's live evidence filter, not the entire project. Existence of model code does not establish production readiness, calibrated performance for every league, or support for all three target markets. The original trained target is 1+ SOT; separate 1+ shot and 2+ shots models were not found.

Method: inventory of first-party source/configuration/test trees, review of API/service/repository/data/model boundaries and principal implementations, inspection of saved research JSON, and focused existing tests. Dependencies, secrets, binary databases, generated bundles and unrelated files were excluded from source review. A protected pytest temporary directory was inaccessible; it is not application source. Existing tracked and untracked changes in SOT were left intact. Live database counts, live provider coverage, deployed behavior and production model artifacts were not independently verified. This is not a claim that every source line or every test has been exhaustively reviewed.

## 2. Architecture and module classification

A = should remain deterministic. B = could benefit from an agent around the workflow. C = strong agent use case for the specified investigation/synthesis. D = not enough information to authorize or specify it yet. A/C means the computation is A and the surrounding investigation is C.

| Area | Existing implementation | Class and reason |
|---|---|---|
| Frontend | SOT `frontend/app/{page,upcoming,compare,players/[id],teams/[id]}`, `PlayerAnalyticsView`, `MatchTable`, `SotTrendChart`, `PlayerSearch`, `ApiStatus`; TL `components/{dashboard,imported-data,weekend-shortlist}.tsx` | A. Rendering, filters, accessible controls and state are ordinary UI code. Optional evidence narration is B. |
| HTTP/backend | SOT `app/main.py`, `api/router.py`, routes for players, teams, fixtures, datasets, ingestion and health; `api/deps.py` | A. Typed routes, authentication and validation remain services. |
| Data access | SOT `repositories/players.py`, `database.py`, SQLAlchemy models and two Alembic migrations; TL `lib/db.ts`, two SQL migrations | A. Queries, constraints, transactions and permissions must be reproducible. |
| Provider integrations | SOT `ingestion/provider.py`, `factory.py`, `sports_api_pro.py`, `api_football.py`, `statsbomb.py`, `fake.py` | A/B. Fetching and normalization A; ambiguous provider contradictions and missing coverage investigation B. Fake/demo data must remain excluded from real research. |
| Imports and jobs | SOT `IngestionService`, `sync.py`, sync CLIs, `rollover.py`, `research_registry.py`, `IngestionJob`, `LeagueResearchState`; TL sync/import scripts | A/B. Existing state, quota, retry and transaction logic is reusable. Agents can explain or prioritize exceptions within a fixed budget. |
| Fixtures | SOT fixture routes and `FixturePreviewService.daily`; TL `weekendCandidates()` plus client weekend filters | A/B. Schedule, UTC conversions and cancellation rules A. Conflicting schedule evidence B. SOT uses UTC dates; TL displays Denver weekends. |
| Player identity | SOT provider IDs, `PlayerRepository.search`, `core/text.py`, ingestion upserts; TL provider/external IDs; R replacement records | A/C. Exact IDs and text folding A; ambiguous original/replacement and cross-store identity investigation C. |
| Historical summaries | SOT `analytics/{summary,form,splits,streaks,filters,rules,math}.py`, player/team services; TL `analytics()` | A. Denominators, missingness, starts, venue and windows must stay in code. |
| Features | SOT `PreMatchFeatureBuilder.build_historical/build_upcoming`, typed `PreMatchFeatureRow`, `MatchStatLine` | A/C. Feature values and timing rules A; investigate failed checks and evidence gaps C. |
| Dataset quality | SOT `audit_historical_dataset`, `historical_dataset_records`, audit CLI and `/api/admin/datasets/*`; constraints and tests; R evidence files | A/C. Generate objective diagnostics in code; agent traces anomalies across records and sources. |
| Pattern discovery | SOT `chronological_split`, `discover_patterns`, `PatternLibrary.match`, elite/league research | A/B. Search, rates, lift and validation A; bounded hypothesis selection and explanation B. |
| Models/calibration | SOT `LogisticSotModel.fit/predict_probability`, `evaluate_probabilities`, `walk_forward_evaluate`, `train_and_evaluate_model` | A. No LLM probability calculation, calibration or training decision. |
| Ranking | SOT `SotEngineArtifact.rank`, `CandidateRankingConfig`, `FixturePreviewService._qualification`, legacy `score_candidate`; TL `evidence()`, shortlist sort | A/C. Rank math and eligibility A; challenge evidence behind a candidate C. |
| Prediction pipeline | SOT `fit_sot_engine` called by `FixturePreviewService.daily`; TL evidence calculation and server save actions | A/B. Current SOT preview trains in the request. Agents must not accidentally trigger fitting through a purported inference-only tool. |
| Explanations | SOT `_explanations`, preview reasons/risks and typed responses; TL warnings and templates | A/B. Existing templates already do useful work. Agent synthesis is worthwhile for complex or conflicting evidence, not every row. |
| Post-match research | SOT `analyze_high_confidence_failures`; TL `settle-picks.mjs`; R matrix and reconciliation | A/C. Settlement and statistical aggregation A; identity/event investigation and hypothesis narratives C. |
| Schedules | SOT manual CLIs and research checkpoints; TL manual refresh/import/settlement | A/D. No durable weekend scheduler found in inspected app configuration. External OS/cloud schedules were not audited. Routine polling needs a scheduler, not an LLM. |
| Logs/caches | SOT structured logging/redaction, ingestion jobs, provider season/lineup caches, per-service engine/defense caches; frontend query cache; TL sync logs and lineup cooldown | A/B. Preserve existing facilities; add agent trace linkage only where needed. |
| Configuration | SOT Pydantic settings, environment examples, Docker/Netlify/CI; TL environment example, local Postgres scripts | A. Agents cannot freely change quotas, credentials or deployment. Some TL documentation describes older intended architecture rather than current code. |
| Tests | SOT analytics/provider/API/model/migration/research tests and CI; TL seven weekend tests and SQL checks; R `verify.py`, assertions and `check_site.cjs` | A. Agents can triage test failures, not replace regression checks or declare success without execution. |
| Research outputs | R `analyze.py`, `deliver.py`, `enrich.py`, `save_reconciliation.py`, `build_phase3.py`, `build_progress_site.py` | A/C. Existing extraction/build steps A; external evidence reconciliation C. Most scripts execute and write files at module import. |

Current flow:

```text
SOT: authorized provider -> IngestionService -> SQL database -> repositories
     -> pure summaries / PreMatchFeatureBuilder -> patterns + logistic model
     -> SotEngineArtifact.rank -> FixturePreviewService -> FastAPI -> Next.js

TL:  historical SOT export + SportsAPI sync -> separate PostgreSQL
     -> analytics()/weekendCandidates() -> evidence() -> shortlist
     -> human save/finalize -> weekend_picks -> deterministic settlement

R:   saved report text -> analyze.py -> data.json -> deliver.py
     -> evidence/manual enrichment -> failure_analysis_data.json
     -> build_phase3.py -> matrix + report + static dashboard -> M mirror
```

## 3. Concrete findings that determine agent priorities

1. **Team context can be assigned to the wrong side in R.** `build_phase3.py:failure_matrix_row()` uses `team_shots.get(f['fixture_id'])`, without team identity. F130 gives both Rafael Navarro (Colorado) and Marcus Ingvartsen (San Diego) the same Colorado total of 9; F222 applies Argentina's stored 15 to both Messi and Kane. These assignments are unsupported for the opposing player, regardless of whether actual totals coincidentally match. Use fixture + team identity in a future correction. Do not let an agent infer the missing opposing total. These two other-player rows are outside the same-player subset, so this alone does not prove its aggregate means wrong.
2. **Report-to-match linkage remains provisional.** `deliver.py` explicitly says original tickets lack dates and report pairing IDs may combine meetings. `hit_matrix_row()` marks dates confirmed when enrichment exists; that is a confirmed candidate fixture date, not proof of the ticket join. Names, ticket identity and source timestamps require investigation before model ingestion.
3. **Strict information availability is incomplete in SOT.** `MatchStatLine` lacks completion/publication availability timestamps; `build_historical()` batches equal kickoffs and snapshots at kickoff minus one microsecond, then consumes earlier-kickoff results. Equal-kickoff protection exists and is tested, but an earlier match may still be in progress or have results published later. `build_upcoming()` filters before target kickoff rather than a supplied actual analysis cutoff. A synthetic pre-kickoff timestamp alone does not establish what was known. TL has `available_at` filtering but imported completion times remain unknown; it is a different implementation.
4. **Season-aware split deserves an additional invariant.** In `patterns.py:chronological_split`, latest-season rows are held out while all other season IDs go to train. With overlapping competitions/seasons this can place later timestamps in train. Single-league usage reduces the risk but does not replace checking `max(train time) < min(validation time) < min(test time)` and preventing shared kickoff blocks across partitions.
5. **Read preview can perform model training.** `FixturePreviewService.daily()` calls `fit_sot_engine(...include_walk_forward=False)` and keeps an instance cache. An agent wrapper around this route is not inference-only. Model routing should remain fixed and use approved persisted artifacts before unattended preview orchestration.
6. **Scores have different meanings across systems.** SOT's `combined_probability` blends a 1+ SOT model with pattern rates and negative penalties; it is not the joint event 2+ shots AND 1+ SOT. TL's blueprint uses combined to mean that joint event, while its live code uses three observed-rate filters. A future explanation agent must preserve target, metric type and model/policy version explicitly.
7. **Source provenance needs a field-level layer.** R stores source lists and narrative confidence; a link alone does not identify which field it supports or when it was retrieved. Original provider payloads in SOT are useful but overwritten by subsequent upserts; they are not a versioned evidence ledger. TL's `count >= 20` cache shortcut is not statistical completeness and can skip missing fields/corrections.
8. **Outcome comparisons need careful interpretation.** R's post-match personal shot share contains the outcome numerator. The 29.2% hit versus 9.0% miss contrast is descriptive and partly induced by selecting hits/misses. It does not establish pre-match predictive value. Full-match team shots also differ from team shots while the player was on field. An agent should propose a lagged-history test, not turn that contrast into a rule.
9. **Some context is explicitly absent.** SOT's dataset audit lists formation, injury/tactical context, penalty/non-penalty detail and other provider-dependent fields; post-match red-card diagnostics are separate. Research may attach evidence, but these gaps cannot be filled with football intuition.
10. **Preserve existing unresolved cases.** R still has 12/15 provisional original-player counter matches. Antony, Denis Bouanga and Pep Biel remain unresolved. The current matrix has 51 rows, including 31 failures and 20 hits across 11 same-player groups. These are saved research counts, not independent verification of every football fact.

These findings were recorded only. No fixes were made as part of this audit.

## 4. Opportunity register

All permissions below describe a proposed future system, not authorization granted by this audit. P0 = first foundation/pilot; P1 = next high-value step; P2 = later conditional workflow; P3 = defer. Read-only means source stores are read-only; reports and action logs may be appended to a designated audit store. Human approval is required for canonical data corrections, new training runs, model promotion, threshold changes and final selections.

### 1. Fixture discovery and schedule exceptions — B

- **Current code / reuse:** SOT `FootballDataProvider.get_fixtures`, `SportsApiProProvider.get_fixtures`, `IngestionService.ingest_fixtures`, `sync_leagues`, `run_historical_rollover`; `api/routes/fixtures.py:list_fixtures`. TL `scripts/sync-sportsapi.mjs:request/fixture`, `lib/weekend.ts:weekendCandidates`.
- **Current workflow:** Provider adapters import fixtures; services query stored schedules. UTC date previews and Denver weekend filters differ.
- **Problem / agent opportunity:** Investigate contradictory postponements, incomplete pages and league coverage; propose targeted repair jobs with cited reasons.
- **Why appropriate:** Exception paths require choosing among sources. Routine date filtering, pagination, cancellation handling and polling remain deterministic.
- **Tools / inputs:** Read fixture/ingestion records, bounded provider fetch, timezone utility; fixture IDs, status history, enabled leagues, run budget.
- **Outputs:** Missing/conflicting fixture report and proposed job IDs, not invented fixtures.
- **Permissions:** Read plus proposed-job output; scheduler alone dispatches approved ingestion.
- **Risk:** MEDIUM. **Failure modes:** Wrong weekend, duplicate match, stale cancellation, exhausted quota. **Guardrails:** Exact IDs, UTC instants, half-open local weekend bounds, status freshness, budget and idempotency.
- **Human approval:** NO for investigation; YES for changing competitions or provider budget. **Priority:** P2. **Difficulty:** MEDIUM. **Expected benefit:** MEDIUM.

### 2. Lineup and starter evidence — C for research; A for official status

- **Current code / reuse:** TL `services/lineups.ts:refreshOfficialLineups`, `weekendCandidates`, `evidence`; SOT provider `get_lineups`, `UpcomingPlayerContext`, `FixturePreviewService._qualification`.
- **Current workflow:** TL requires confirmed complete official lineups; SOT previews use squad membership and historical likely-starter evidence, with unconfirmed context.
- **Problem / agent opportunity:** Research injuries, suspensions, rotation and conflicting expected lineups before official teams are available.
- **Why appropriate:** Unstructured, time-sensitive evidence needs synthesis. Official versus predicted status must remain a deterministic rule.
- **Tools / inputs:** Approved provider/club sources, stored lineup observations and recent starts; candidate IDs, kickoff and as-of cutoff.
- **Outputs:** Sourced availability/role assessment, unresolved conflicts and evidence for an expected-minutes adjustment. No invented minutes or starting probability.
- **Permissions:** Append research annotations only; cannot mark an official starter or finalize picks.
- **Risk:** HIGH. **Failure modes:** Rumour treated as official, stale injury, wrong same-name player. **Guardrails:** Timestamps, identity matching, source type, official precedence, uncertainty status and expiring evidence.
- **Human approval:** NO for reports; YES for manually applying an unvalidated minutes override. **Priority:** P1 after quality pilot. **Difficulty:** HIGH. **Expected benefit:** HIGH.

### 3. Player data and identity investigation — C for ambiguous cases

- **Current code / reuse:** SOT `PlayerRepository.get/search`, `PlayerMatchRepository.list`, `IngestionService._upsert_player` via its public ingestion methods, `core/text.py`; TL external-ID keys; R `failure_matrix_row`, `hit_matrix_row` and reconciliation data as read-only reference.
- **Current workflow:** Structured sources use provider IDs; research uses displayed/original player names and report pairing IDs.
- **Problem / agent opportunity:** Resolve replacement identity, transfers, aliases and candidate ticket-to-match links with evidence.
- **Why appropriate:** Exact-ID joins are easy code; ambiguous identity resolution benefits from a documented investigation.
- **Tools / inputs:** Player profiles, histories, provider raw payloads, saved report/ticket evidence; original/replacement IDs and source references.
- **Outputs:** Proposed identity mapping with alternatives, confidence reasons and unresolved status.
- **Permissions:** Read; no automatic merges, reassignment or record deletion.
- **Risk:** HIGH. **Failure modes:** Attaching substitute shots to original, merging different matches or players. **Guardrails:** Require dated evidence and provider-scoped IDs; preserve originals and the 12/15 provisional correction.
- **Human approval:** YES for canonical mapping changes; NO for draft evidence. **Priority:** P0 as part of quality pilot. **Difficulty:** MEDIUM. **Expected benefit:** HIGH.

### 4. Data Quality Investigator — C; best first agent

- **Current code / reuse:** SOT `PlayerMatchRepository.list_all_finished`, `PreMatchFeatureBuilder.build_historical`, `audit_historical_dataset`, `audit_as_dict`, `historical_dataset_records`; `/api/admin/datasets/sot-audit`, `/sot-records`; `MatchStatLine`, DB constraints, ingestion job/raw payload records. TL read-only queries and R saved matrix/evidence.
- **Current workflow:** Deterministic audits expose coverage, sample sufficiency and gaps; research contradictions are manually handled.
- **Problem / agent opportunity:** Turn flagged rows into reproducible evidence investigations: wrong team denominator, missing matches, suspicious timestamps, contradictory statistics and identity attribution.
- **Why appropriate:** The agent chooses the next safe source/check and explains the chain. Rules detect impossible values, duplicates and date violations deterministically.
- **Tools / inputs:** Read-only repository/API adapters, existing audit functions, scoped file reader, optional bounded external research; run manifest, snapshot ID, flagged record keys.
- **Outputs:** Structured issue register with severity, observed values, source/field references, reproducible check, confidence, unresolved reason and proposed correction.
- **Permissions:** Read canonical data; append audit reports/logs only. Do not grant the current broad admin token directly to an LLM; use a constrained gateway.
- **Risk:** MEDIUM, despite read-only scope, because a false clearance can mislead users. **Failure modes:** Fabricated correction, stale evidence, confusing unknown with zero, malicious instructions in source pages. **Guardrails:** Code verifies claims and arithmetic, sources are data not instructions, explicit missing/conflicting state, no write tools, bounded calls, full trace.
- **Human approval:** NO to generate a report; YES to apply corrections. **Priority:** P0. **Difficulty:** MEDIUM. **Expected benefit:** HIGH.

### 5. Feature Audit Investigator — C around deterministic checks

- **Current code / reuse:** SOT `PreMatchFeatureBuilder`, `PreMatchFeatureRow.__post_init__`, `audit_historical_dataset`, `chronological_split`, `test_discovery_features.py`, `test_pattern_discovery.py`; TL `evidence`, prediction-cutoff trigger.
- **Current workflow:** Kickoff batching and typed assertions protect some leakage paths; coverage audit reports gaps.
- **Problem / agent opportunity:** Explain timing, stale-feature, distribution and missingness alerts; trace why a feature changed across snapshots.
- **Why appropriate:** Cross-module evidence investigation is variable. Calculating distributions, recomputing features and testing leakage are deterministic.
- **Tools / inputs:** Versioned feature snapshots, read-only dataset audit, isolated regression checks; cutoff, source availability, schema version and baseline period.
- **Outputs:** Failed invariants and affected feature/record IDs, risk interpretation and repair proposals.
- **Permissions:** No feature mutation, imputation, model retraining or test suppression.
- **Risk:** HIGH. **Failure modes:** Assuming cutoff compliance from a timestamp alone, train/test leakage, silently filling missing features. **Guardrails:** Verify source availability and match completion, same-kickoff grouping, immutable input snapshot and train-only transforms.
- **Human approval:** NO for audit; YES for feature definitions/imputation changes. **Priority:** P0 deterministic prerequisites, P1 agent extension. **Difficulty:** MEDIUM. **Expected benefit:** HIGH.

### 6. Matchup Research — C

- **Current code / reuse:** SOT `FixturePreviewService._defensive_context` through the preview service, `PlayerAnalyticsService.get_splits`, `TeamAnalyticsService.rankings`, `PreMatchFeatureBuilder`; provider-dependent fields identified in `dataset.py`.
- **Current workflow:** Stored team/opponent histories supply numerical context; formation, injuries and detailed role changes are largely missing.
- **Problem / agent opportunity:** Investigate tactical deployment and structural team changes for already shortlisted fixtures.
- **Why appropriate:** Multiple narrative sources and contradictory tactical reports are difficult to represent as a single deterministic fetch.
- **Tools / inputs:** Read approved club/provider reports, stored profiles and cutoff-safe statistics; fixture/candidate identity, existing context and missing fields.
- **Outputs:** Cited tactical memo with known facts, interpretation and explicit unknowns.
- **Permissions:** Research annotation only; no probability adjustment or feature filling.
- **Risk:** HIGH. **Failure modes:** General football stereotypes substituted for actual data, hindsight contamination, positional vulnerability without sample. **Guardrails:** Evidence dates, counterevidence, sample sizes for quantitative claims, separate external research from model inputs.
- **Human approval:** NO for memo; YES to promote new derived features into a model. **Priority:** P2. **Difficulty:** HIGH. **Expected benefit:** MEDIUM until core data is trustworthy.

### 7. Historical Pattern Investigation — B

- **Current code / reuse:** SOT `PatternLibrary.match`, `discover_patterns`, `chronological_split`, `research_elite_tier`, `assess_league_research`; `historical_dataset_records` for auditable rows.
- **Current workflow:** Patterns are mined on train, filtered on validation and reported on test; candidate engine matches rules.
- **Problem / agent opportunity:** Select bounded research questions and explain actual matched examples, supporting and contradicting cases.
- **Why appropriate:** Choosing useful follow-ups can be adaptive; counting matches and calculating rates/lift belong to existing code.
- **Tools / inputs:** Read-only historical queries and approved frozen pattern library; target, cutoff, candidate features and permitted filters.
- **Outputs:** Match IDs, sample sizes, hits, rates and limitations from tool results; proposed next hypothesis.
- **Permissions:** Read/match only in screening. New discovery runs go through approved research jobs.
- **Risk:** MEDIUM. **Failure modes:** Cherry-picking, treating overlapping patterns as independent, tuning on test, confusing SOT with shots. **Guardrails:** Preregistered filters, target labels, frozen splits, record all attempted queries and negative findings.
- **Human approval:** NO for matching; YES for new training/mining policies. **Priority:** P2. **Difficulty:** MEDIUM. **Expected benefit:** MEDIUM because substantial functionality already exists.

### 8. Model orchestration — A now; D for autonomous model choice

- **Current code / reuse:** SOT `fit_sot_engine`, `LogisticSotModel.predict_probability/predict_many`, `SotEngineArtifact.rank`; `train_and_evaluate_model`; TL `PredictionEngine` is an interface, not an implemented live model.
- **Current workflow:** SOT previews fit an engine from history; offline research has evaluation routines.
- **Problem / limited opportunity:** A fixed service should retrieve an approved target/league/version artifact and invoke it. No evidence justifies discretionary agent model selection.
- **Why agent value is limited:** Model routing is a stable registry lookup. Agent involvement should only explain incompatibility or request human review.
- **Tools / inputs:** Future inference-only wrapper; versioned approved artifact, feature schema/hash, target and league.
- **Outputs:** Actual model probabilities and metadata or unavailable; never guessed probabilities.
- **Permissions:** Inference only. No call to `fit_sot_engine` in a read-only agent path.
- **Risk:** HIGH. **Failure modes:** Wrong target, implicit retraining, applying SOT probability to 2+ shots, presenting blend score as calibrated. **Guardrails:** Explicit target/version/calibration status, approval allowlist and schema checks.
- **Human approval:** YES for training/promotion; NO for approved inference. **Priority:** P3 for an agent, P1 for deterministic artifact separation. **Difficulty:** MEDIUM. **Expected benefit:** LOW for agent, HIGH for service boundary.

### 9. Prediction / Candidate Review — C

- **Current code / reuse:** SOT `SotEngineArtifact.rank`, `CandidateResult`, `FixturePreviewService._qualification`, dataset audit and pattern metrics; TL `weekendCandidates`, `evidence`, warnings and finalized-pick evidence.
- **Current workflow:** Code applies confidence/qualification rules and produces reasons/risks.
- **Problem / agent opportunity:** Challenge a shortlist against conflicting role, sample, lineup, penalty coverage and distribution evidence.
- **Why appropriate:** Cross-source contradictions require contextual review beyond a single score threshold.
- **Tools / inputs:** Frozen candidate evidence packet, audit issues, pattern samples, approved model metrics and external annotations.
- **Outputs:** Review verdict, evidence references, unresolved questions and proposed hold reasons. Verdict cannot override deterministic eligibility.
- **Permissions:** Append review only; no rank, probability, training or final-pick writes.
- **Risk:** HIGH. **Failure modes:** Rubber-stamping high scores, inventing penalty inflation, changing policy silently. **Guardrails:** Counterevidence required, explicit unknown penalty fields, code-enforced hold/eligibility, review all qualifying candidates consistently.
- **Human approval:** NO for review; YES for final selection and policy changes. **Priority:** P1. **Difficulty:** MEDIUM. **Expected benefit:** HIGH.

### 10. Evidence Explanation — B

- **Current code / reuse:** SOT `candidate_engine.py:_explanations` through `rank`, `preview.py:score_candidate`, response schemas and `RateResult.describe`; TL `Evidence.warnings`, `CATEGORY_LABELS` and UI templates.
- **Current workflow:** Structured templates already explain rates, samples and warnings.
- **Problem / agent opportunity:** Produce a concise synthesis when several evidence sources disagree or a user asks a follow-up question.
- **Why appropriate:** Readable synthesis may improve comprehension; simple per-row templates should remain the default.
- **Tools / inputs:** One validated evidence packet, containing exact values, units, targets, windows and source IDs.
- **Outputs:** Narrative whose numerical claims each point to an input field.
- **Permissions:** Read packet and write explanation only.
- **Risk:** MEDIUM. **Failure modes:** Invented statistics, calling history a probability, claiming full-match share is on-field share, overstating certainty. **Guardrails:** Deterministic numeric-claim validation; template fallback on mismatch; no ungrounded probability language.
- **Human approval:** NO after evaluation for routine output. **Priority:** P1 optional. **Difficulty:** LOW/MEDIUM. **Expected benefit:** MEDIUM.

### 11. Weekend screening coordinator — B, later

- **Current code / reuse:** SOT fixture repository/routes, ingestion services and research registry; TL `weekendCandidates`, `refreshOfficialLineups`, `evidence`; approved inference wrapper later reuses SOT model/ranking.
- **Current workflow:** Separate manual sync, UI refresh and on-demand preview steps, without one shared workflow or identity layer.
- **Problem / agent opportunity:** Triage exceptions and choose which unresolved fixture/candidate warrants investigation during an otherwise deterministic workflow.
- **Why appropriate:** Exception branching is useful; ordinary fixtures-to-features-to-rank sequencing is a fixed job graph.
- **Tools / inputs:** Scoped fixture/lineup/audit/review tools, persistent job state, quota and time budget; run cutoff, timezone and enabled leagues.
- **Outputs:** Run manifest, completed/held/skipped tasks, evidence-backed shortlist and unresolved items.
- **Permissions:** Stage 2 can dispatch allowlisted idempotent jobs within configured budgets; cannot place bets, finalize picks, retrain or change thresholds.
- **Risk:** HIGH. **Failure modes:** Duplicate work, same-key cross-store joins, loops, stale kickoff, budget overrun. **Guardrails:** Namespaced IDs, fixed maximum steps, checkpointing, deterministic gates and fail-closed incomplete runs.
- **Human approval:** NO per bounded run after setup approval; YES for new tools/budgets and final selection. **Priority:** P2. **Difficulty:** HIGH. **Expected benefit:** HIGH only after boundaries are reliable.

### 12. Post-match Review — C

- **Current code / reuse:** SOT `analyze_high_confidence_failures`, `evaluate_probabilities`; TL `settle-picks.mjs` as separate write job; R saved matrix, failure records and replacement reconciliation.
- **Current workflow:** SOT classifies high-confidence SOT misses; TL settles final picks; R compares selected hits and misses.
- **Problem / agent opportunity:** Investigate unexplained outcomes and source conflicts, including successful cases; distinguish football performance, identity and ticket settlement.
- **Why appropriate:** Event sequences and conflicting reports require evidence synthesis. Outcome classification and aggregation stay deterministic.
- **Tools / inputs:** Immutable pre-match prediction/pick snapshot, deterministic outcomes, dated event evidence and comparable hit/miss records.
- **Outputs:** Sourced review with mechanism hypotheses, missing evidence, sample sizes and candidate research questions.
- **Permissions:** Read outcomes; append research. No settlement edits or automatic retraining.
- **Risk:** MEDIUM. **Failure modes:** Hindsight stories, reviewing only misses, substitute/original confusion, equating cash-out with loss. **Guardrails:** Preserve unknown category, include successes, retain raw counters and original identities, causal claims require testing.
- **Human approval:** NO for review; YES for corrections or research-driven production changes. **Priority:** P1. **Difficulty:** MEDIUM. **Expected benefit:** HIGH.

### 13. Research hypothesis assistant — B

- **Current code / reuse:** SOT `audit_historical_dataset`, `research_elite_tier`, `assess_league_research`, `discover_patterns`, `evaluate_probabilities`, `analyze_high_confidence_failures`; R hypothesis/matrix outputs.
- **Current workflow:** Numerical research functions and manually written hypotheses already exist.
- **Problem / agent opportunity:** Propose a limited set of testable, data-supported questions and identify the necessary fields/cohort.
- **Why appropriate:** Question formation and interpretation are open-ended. Statistical testing is not.
- **Tools / inputs:** Read audit/results/matched cases; schema catalogue, target, sample coverage and prior tested hypotheses.
- **Outputs:** Hypothesis, rationale, fixed cohort/test specification, required data, leakage risks and proposed acceptance/rejection criteria.
- **Permissions:** Append proposals; testing runs use reviewed deterministic code and approved resources.
- **Risk:** MEDIUM. **Failure modes:** Multiple-testing overfit, repeatedly tuning against final test, invented historical rates. **Guardrails:** Register all hypotheses, preserve held-out periods, report null/negative results and selection bias.
- **Human approval:** NO for proposals; YES for new experiments that train models or alter production policies. **Priority:** P2. **Difficulty:** MEDIUM. **Expected benefit:** MEDIUM.

## 5. First-agent reuse boundaries

Start with a single Data Quality Investigator combining opportunity 4 with identity triage from opportunity 3. It consumes existing audit output and saved research anomalies. Avoid introducing thirteen independent agents.

| Existing item | Safe reuse | Caveat |
|---|---|---|
| SOT `PlayerMatchRepository.list_all_finished/list_all_before/list` | Read historical records through a restricted session | Existing APIs do not prove historical publication availability. |
| SOT `PreMatchFeatureBuilder.build_historical` | Generate diagnostic snapshots with existing semantics | Label timing limitations; do not certify strict replay. |
| SOT `audit_historical_dataset` / `audit_as_dict` | Existing coverage, samples and missing-field diagnostics | Supplement checks; it is not a universal integrity validator. |
| SOT `historical_dataset_records` | Trace selected diagnostic rows | Paginate and scope output; do not dump raw secrets. |
| SOT audit and records GET routes | Existing structured interface | Admin token is too broad for an agent; expose via allowlisted gateway. |
| SOT `core/logging.py:configure_logging/get_logger` | Existing structured logs/redaction | Add run/tool/evidence IDs and safe free-text handling. |
| R `failure_analysis_data.json`, `phase3_hit_miss_matrix.json`, `work/evidence.json` | Read source records and compare supported claims | URLs/notes are not independently verified truth. |
| R `failure_matrix_row/hit_matrix_row` | Reference current mapping semantics for diagnostics | Do not import `build_phase3.py`: top-level code writes outputs and rebuilds site. A later refactor could extract pure functions after approval. |
| TL `models/weekend.ts:evidence/eventValue/wilsonLower` | Reuse deterministic rates and checks through a typed boundary | No source-store merging without crosswalk; no conversion of rates to probabilities. |

Proposed new files, not created in this audit: `backend/app/agents/{contracts,policy,tools,data_quality,runner}.py`, `backend/app/cli/agent_audit.py`, `backend/tests/test_agent_quality.py`, and a small evidence-based evaluation case set. See the roadmap for responsibilities and gates.

## 6. Reliability rules for every proposed agent

1. Never invent player statistics; preserve reported and verified values separately.
2. Never invent probabilities or turn scores/historical rates into probabilities.
3. Model probabilities come only from an approved model artifact for the stated target.
4. Historical rates come from actual stored observations through deterministic functions/queries.
5. Every rate carries numerator, denominator, excluded/missing count, window and cohort.
6. Enforce `feature_as_of < kickoff` in code, with actual evaluation time recorded.
7. Require source availability and match completion before the feature cutoff; unavailable provenance blocks strict historical replay.
8. Preserve equal-kickoff batching and cross-partition timestamp invariants; no simultaneous-result leakage.
9. External research annotations stay distinct from frozen model evidence.
10. Missing/conflicting fields remain missing/conflicting. No silent numeric imputation.
11. Agents cannot silently mutate training data, canonical identities or outcomes.
12. Training/retraining, promotion and threshold changes require explicit human approval.
13. Recommendations reference immutable evidence IDs and source/field provenance.
14. Log each action, tool input/output reference, model/prompt version, time, budget and status; redact credentials.
15. Source disagreement produces a hold or unresolved issue, never an invented compromise.

Additional boundaries: no arbitrary SQL/shell tools; source text cannot authorize tool use; no permission to finalize picks or place bets; numerical transformations belong to tested code; production approval gates cannot be overridden by narrative confidence.

## 7. Verification and limits

Executed in SOT/backend: `../.venv/Scripts/python.exe -m pytest tests/test_dataset_audit.py tests/test_discovery_features.py tests/test_pattern_discovery.py tests/test_analytics_purity.py -q -p no:cacheprovider`.

Result: **14 passed**. This verifies those existing tests only; it does not negate the uncovered provenance/split risks or certify deployment. No provider sync, migration, training CLI, settlement command or dashboard rebuild was run during this audit. Current application code and saved Phase 3 evidence were preserved.

Deliverables: [Proposed architecture](PROPOSED_AGENT_ARCHITECTURE.md) and [Implementation roadmap](AGENT_IMPLEMENTATION_ROADMAP.md).
