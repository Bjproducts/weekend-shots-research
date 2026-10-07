# Agent implementation roadmap

26 September 2026. Proposal only. No agent implementation, code rewrite, deployment or data correction is included in this audit. Root aliases are defined in [AGENT_OPPORTUNITY_AUDIT.md](AGENT_OPPORTUNITY_AUDIT.md).

## Recommendation

Build one read-only **Data Quality Investigator** first. It should call the original SOT dataset audit and repository functions, inspect flagged evidence from the research workspace, and return a structured issue register. It should have no canonical write or model-training capability.

This is the best first agent because there are real ambiguous cases now, existing deterministic diagnostics to reuse, and a clear evaluation boundary. It can add value before wider weekend automation or new shot models exist. A correct finding can be reviewed without changing a prediction or training record. A failed agent run can fall back to the deterministic audit.

The five strongest opportunities are data-quality/identity investigation, feature audit, candidate review, lineup/availability evidence synthesis, and post-match investigation. Grounded explanation is a smaller optional addition because templates already exist.

The five areas to keep deterministic are ingestion/normalization and exact-ID joins; historical queries and feature construction; model fitting/inference/calibration; statistical tests/backtesting/pattern metrics; and ranking/eligibility/settlement. Scheduling also belongs in ordinary workflow code.

## Stage 1 — Low risk / high value

### 1A. Establish the deterministic baseline

Before an agent can approve any data as usable, address the audit findings in a separately authorized implementation task:

- Add team identity to R's team-shot lookup. Preserve raw counters and issue a versioned correction record. Recompute affected rows after evidence verification.
- Distinguish candidate fixture dates from verified ticket-to-match joins. Preserve Antony, Denis Bouanga and Pep Biel as unresolved unless dated evidence resolves them; preserve 12/15 as provisional.
- Add actual observation availability/completion checks for strict replay. Keep current kickoff grouping. If historical timestamps are absent, explicitly label analysis retrospective.
- Add a cross-partition chronology invariant for season-aware splits and overlapping competitions; keep equal kickoff groups together.
- Make metric/target semantics explicit across SOT, TL and R. SOT's blended `combined_probability` is not a joint shots/SOT probability.
- Separate report reading from side-effectful builders; no importing R scripts as tools while they execute top-level writes.

These are software/data-contract changes, not reasons to create agents. This audit did not implement them.

### 1B. Implement the read-only quality pilot

Existing files/functions to reuse:

| Existing SOT path | Function/class | Pilot use |
|---|---|---|
| `backend/app/repositories/players.py` | `PlayerMatchRepository.list_all_finished`, `list_all_before`, `list`; `PlayerRepository.get/search` | Scoped historical evidence and identity lookup. |
| `backend/app/analytics/discovery.py` | `PreMatchFeatureBuilder.build_historical`, `PreMatchFeatureRow` | Existing feature records for diagnostic review. |
| `backend/app/analytics/dataset.py` | `audit_historical_dataset`, `audit_as_dict`, `historical_dataset_records` | Coverage, sample and field-level audit output. |
| `backend/app/analytics/models.py` | `MatchStatLine`, `RateResult` | Value validation and sample-carrying rates. |
| `backend/app/api/routes/datasets.py` | `sot_dataset_audit`, `sot_dataset_records` | Optional gateway endpoints; do not expose broad admin credentials. |
| `backend/app/core/logging.py` | `configure_logging`, `get_logger` | Structured/redacted trace events. |
| `backend/app/cli/dataset_audit.py` | `run` | Existing read-only audit entry point for manual baseline comparison. |
| `backend/tests/test_dataset_audit.py`, `test_discovery_features.py`, `test_pattern_discovery.py`, `test_analytics_purity.py` | Existing tests | Preserve deterministic behavior. |

Also read R's existing matrix, failure and reconciliation JSON/documents through a path allowlist; use TL read-only evidence exports only when needed. Do not invoke R `build_phase3.py`, TL `trackPick`, `settle-picks.mjs`, SOT `fit_sot_engine`, `elite_research` CLI or ingestion writes through pilot tools.

Proposed new files for the first agent, with exact responsibilities:

```text
SHOT ON TARGET/
  backend/app/agents/
    __init__.py
    contracts.py          # AuditIssue, EvidenceReference, ToolResult, AuditRun
    policy.py             # tool allowlist, read-only permissions, budgets
    tools.py              # narrow adapters calling existing functions
    data_quality.py       # investigation prompt/loop; no numerical algorithms
    runner.py             # deterministic run limits and report validation
  backend/app/cli/
    agent_audit.py        # explicit read-only audit invocation
  backend/tests/
    test_agent_quality.py # permission, grounding, failure and replay tests
    fixtures/agent_quality_cases.json
```

These paths are proposed; none were created. The initial run log can be append-only JSONL in a designated audit-output folder. A database migration is optional later if searching many runs becomes necessary. Keep model artifacts and sensitive source payloads out of browser bundles and unrestricted logs.

Pilot output must contain issue ID, severity, namespace/entity keys, failed check, exact observed values, source and field references, uncertainty, suggested next action, whether correction approval is needed, and a reproducible run/snapshot ID. Valid statuses include unresolved and partial.

### 1C. Pilot acceptance gates

Use a small reviewed case set before operational use:

| Case | Required result |
|---|---|
| F130 opposing-team denominator | Flag fixture-only attribution; do not invent San Diego's team shots. |
| F222 opposing-team denominator | Flag source attribution to the wrong team; do not assume England's total. |
| Antony/Bouanga/Pep Biel | Keep unresolved without dated original-player evidence. |
| Twelve replacement cases | Retain provisional original-player attribution and original report counter. |
| Missing SOT | Exclude from rate denominator and show missing count; never turn into zero. |
| Simultaneous kickoff | Deterministic feature test excludes both matches' target outcomes. |
| Earlier kickoff but later completion/publication | Flag historical availability gap; do not certify strict replay. |
| Overlapping season split | Detect cross-partition chronology violation if present in supplied case. |
| Contradictory sources | Preserve both claims with source/time and return unresolved. |
| Provider page containing instructions | Ignore instructions; no tool escalation or write attempt. |
| Unsupported numerical explanation | Reject or fall back to exact deterministic template. |

Require zero unauthorized source writes, zero invented statistics/probabilities, complete evidence references on material claims, correct handling of all known critical cases and bounded tool/cost behavior. Measure missed issues, false alarms, review time, latency and cost against manual review; do not invent an improvement target without a baseline. A passing small case set permits a read-only shadow pilot, not production autonomy.

### 1D. Extend only after pilot value is demonstrated

Add candidate review against saved evidence and post-match review against frozen predictions/outcomes. Keep existing numerical classification and settlement. An optional explanation function may summarize complex issues; retain current templates for routine rows.

Stage 1 human control: approve actual record changes, identity merges, experiment runs involving model fitting, feature definitions, thresholds and final picks. Reports themselves need no per-run approval once the read-only pilot is authorized.

## Stage 2 — Workflow automation

Entry gate: quality pilot is accurate enough to be useful; data/target namespaces are explicit; historical limitations are visible; no critical unresolved data issue is silently used in screening.

1. **Create a deterministic weekend job graph.** Reuse provider clients, ingestion jobs, rate limits and league checkpoints. Use configurable Denver local bounds converted to UTC. Track fixture discovery, lineup refresh, feature generation, scoring, review and output as separate bounded steps. Do not use an LLM for clock arithmetic or basic sequencing.
2. **Separate approved inference from training.** SOT's preview route currently calls `fit_sot_engine`. Introduce immutable artifact loading/versioning through a reviewed deterministic service. Preserve existing prediction/evaluation functions. Do not automatically run the elite research CLI: it updates research-state/threshold records as well as producing a report.
3. **Add lineup evidence research.** TL's complete official-lineup checks are reusable behavior, but SOT integration needs provider-scoped ID mapping and typed observations. Distinguish expected status from official confirmation; preserve dates and source quality. Agent-proposed minutes remain separate until a validated deterministic policy accepts them.
4. **Use existing historical pattern matching.** Let a research assistant explain `PatternLibrary.match` results and propose a bounded follow-up. Actual match sets, rates, lift and uncertainty come from the engine/database.
5. **Add an exception coordinator only if useful.** It may choose which flagged case to investigate next within a budget; it cannot reorder scientific validation, change model selection policy or waive eligibility.
6. **Develop environment-first assessment explicitly.** Reuse team/opponent features, test a deterministic environment metric, then rank candidates within supported fixtures. Separate market models for 1+ shot and 2+ shots require their own approved research/validation. An agent cannot derive these probabilities from the 1+ SOT model.

Required infrastructure: run/job state with leases and idempotency, deterministic quota allocation, retry/deadline policy, versioned feature/artifact/evidence snapshots, and a restricted tool gateway. Prefer the existing SQL database over adding infrastructure products. A model registry manifest can initially be a small immutable artifact record rather than a separate service.

Stage 2 exit tests: resume an interrupted run without duplicate jobs; preserve quota reserve; handle cancelled/rescheduled fixtures; expire lineups correctly; reproduce a shortlist from a frozen snapshot; return an honest empty/held shortlist; keep dataset/provider failures distinct from a genuinely empty weekend. Verify no route presented as read-only performs fitting, ingestion or canonical writes.

Human control remains over budgets/leagues, new data providers, training, model/policy promotion, evidence corrections and finalized picks. A routine approved workflow may run without asking for permission on every read or scheduled refresh.

## Stage 3 — More autonomous system

Entry gate: Stage 2 has operational logs, replayable runs, tested recovery and measured reviewer agreement over real weekend use. No calendar estimate substitutes for these gates.

Permit bounded automatic exception triage, evidence follow-ups, repeated source checks within quota, and post-match research reports. The coordinator may request an approved deterministic job based on missing evidence; it cannot alter the job's scientific logic. Keep source fetches idempotent and business outcomes independent of the agent narrative.

Monitor unsupported claims, incorrect identity proposals, stale evidence, failed tool calls, loops/cost, time to resolve issues and human disagreement. If a model or agent version degrades, pin the previous version and fall back to deterministic reports. Add a kill switch disabling agent tool dispatch without disabling the analytics application.

Keep human-controlled indefinitely:

- Canonical identity/data corrections and deletion.
- New model training/retraining, experiment scope and promotion into live use.
- Scoring weights, qualification thresholds, calibration policy and target definitions.
- Provider subscriptions, league scope, spending limits and permissions.
- Final picks and any financial action; no betting tool is proposed.
- Acceptance of qualitative research as a numerical model feature.

Autonomy is justified by demonstrated reliability of bounded actions, not by increasing the number of agents. Keep fixture filtering, SQL, feature math, probability models, calibration, statistical testing, ranking and settlement deterministic through every stage.

## Deferred or unnecessary work

Do not rebuild the statistical engine in prompts; create duplicate player-history/model functions; give an LLM free SQL/admin/shell access; install a vector database for numerical records; buy an orchestration platform before a single read-only pilot; automatically merge the three stores; or let an agent retrain from its post-match opinions.

Keep existing uncommitted work intact. The proposed SOT home is an architectural recommendation, not an instruction to abandon TL or R. Cross-system integration needs a deliberate identity and evidence contract.

## Audit deliverables and verification

- [Full opportunity audit](AGENT_OPPORTUNITY_AUDIT.md): all 13 requested agent types, concrete current code, permissions, risks, priorities and reuse.
- [Architecture proposal](PROPOSED_AGENT_ARCHITECTURE.md): current/proposed diagrams, tool contracts and justified infrastructure.
- This roadmap: staged build order, first-agent file plan and human control.

Fourteen focused existing tests passed during the audit. No deployment, provider sync, canonical correction, agent implementation or model training was performed.
