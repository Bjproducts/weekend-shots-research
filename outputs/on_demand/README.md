# On-demand data assistant (local prototype)

Start from the project directory:

```powershell
python work/on_demand.py
```

Open http://127.0.0.1:8766. Stop with Ctrl+C. Nothing is installed as a background service or scheduled task. It listens only on loopback and requires same-origin JSON POSTs for actions; it does not serve the filesystem.

## What works

- Choose a historical 2026 MLS Saturday (America/Denver).
- Check the existing completed-fixture archive, cached player-shot records and saved A/B replay without a network call.
- Fetch missing player-shot data only for target fixtures and their recent venue-history matches through ASA's documented public endpoint. At most four UTC dates per click, with zero minimum-shot filters. One date can include other fixtures; this endpoint is date-scoped, not a fabricated game-ID filter.
- Preserve raw responses, source URLs, retrieval times and SHA-256 hashes in a small cache. Duplicate records with differing values are flagged, not silently approved. A pagination boundary, changed schema or network failure stops collection.
- Save a precise Flashscore browser-collection request including each target home team's earlier-match IDs ordered backwards. Collect only until every eligible starter has five verified prior starts or insufficient history is documented.
- Keep previously studied saved picks separate from new unvalidated records.

## Not yet automated

The browser request is **not dispatched to an embedded AI agent**. Copy the generated request into this Codex chat to have its browser tools perform the collection. Do not describe the request button as launching an agent.

### Background-worker preflight — September 28, 2026

The installed Codex CLI (0.144.5) is authenticated with ChatGPT, and a read-only, ephemeral `codex exec` capability test ran successfully. However, the worker reported that `cua_repl` was not exposed in its process. Its browser inventory could not be called. Configured/enabled MCP entries alone therefore do not establish a working browser connection. No pages were visited and no sports data was collected in this test.

The blocker is browser access in the standalone worker, not missing model authentication. No credentials were copied, global configuration changed, or sandbox bypass enabled. Official non-interactive execution documentation supports scripted runs and structured results, but does not establish that this desktop chat's browser connection is usable from a standalone worker: https://learn.chatgpt.com/docs/non-interactive-mode

### Separate connection verified — September 28, 2026

The desktop-browser blocker was resolved for a separate worker by installing a project-local, version-pinned Microsoft Playwright MCP connector under `work/browser_worker/`. A real Codex worker opened an isolated headless Edge session, visited the public Charlotte–DC lineup page, extracted all eleven home starters and closed the browser. All eleven match the earlier manually collected lineup. Evidence: `outputs/on_demand/browser_probe/20260928T130759Z/` (raw tool events, structured result, timestamps and verification). The earlier unsuccessful attempt is retained separately.

No global Codex configuration, personal browser session or stored credentials were copied or changed. The worker uses existing ChatGPT authentication and consumes Codex allowance. Only five browser tools are exposed and approved in this invocation; shell access remains read-only. Setup follows official MCP documentation. See `work/browser_worker/README.md` for the repeatable test and limits.

### Dashboard connection completed — September 28, 2026

The local dashboard now launches one bounded lineup job in the isolated research browser, polls its status, displays the saved result and can cancel the owned worker process tree. Only one job can run at a time. Job IDs are validated and every run has a separate folder under `outputs/on_demand/jobs/` containing status, structured result, raw browser events and logs.

The first end-to-end dashboard job, `20260928T200841Z-8f9b8e74`, completed successfully: Charlotte v DC United and eleven home starters were observed. Server-side validation requires the requested URL, eleven unique non-empty names, completed browser navigation, visible Starting Lineups evidence containing all names, and a completed browser close. A separate immediate cancellation test, `20260928T201108Z-3626e756`, finished as cancelled.

The A/B formula and existing datasets remain unchanged. This feature still supports only previously verified fixture URLs and one lineup per job; it does not yet discover every weekend fixture URL, collect previous-five starter histories, import records into the model or create a fresh backtest. Displayed kickoff timezone is unverified, and the page's final score must never become a pre-match feature.

New source data remains insufficient until fixture/player ID mapping, starters, minute conventions, shot conflicts, team totals and coverage are validated. No import endpoint or mixed-source A/B engine is enabled yet. Partial feasibility examples are not a model-ready store. Existing A/B replay is reused, not retrained or recomputed from newly fetched data.

Scope is historical MLS 2026 using the September 27 completed-fixture catalogue. Future schedules, automatic catalogue refresh, team-name lookup, live lineups and season-wide downloads are intentionally not implemented. ASA team IDs are shown explicitly rather than guessed names. Empty coverage is not a confirmed no-game weekend.

Checks: `python work/check_on_demand.py`; browser checks: `node work/check_on_demand.cjs` while the service runs.
