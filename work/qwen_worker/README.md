# Bounded Qwen worker

This folder lets the installed `qwen` CLI handle routine repository work while keeping each model session small and auditable.

## Roles

Qwen should normally handle repository inventory, collector implementation, normalization code, test scaffolding, log triage, dashboard boilerplate, and reproducible aggregate analysis.

Codex retains strategy changes, source approval, methodology decisions, leakage review, immutable-artifact review, and final conclusions reported to the user.

## Run a task

Create a short task Markdown file that lists the exact files Qwen should inspect and the expected output. Then run:

```powershell
powershell -ExecutionPolicy Bypass -File work/qwen_worker/run_qwen_worker.ps1 `
  -TaskFile work/qwen_worker/tasks/example.md `
  -Mode inspect
```

Modes:

- `inspect`: read-only planning/audit mode.
- `edit`: permits file edits but not broad autonomous operations.
- `operate`: permits safe command execution for tests, collectors, and existing workflows.

Every run is capped by prompt size, session turns, tool calls, wall time, and subagent depth. A fresh session is used by default so stale chat context is not accumulated.

The configured Qwen CLI currently uses the model selected in `~/.qwen/settings.json`. At the time this worker was added, the selected model was an OpenRouter endpoint, not a fully local model runtime.

