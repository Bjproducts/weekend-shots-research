# Isolated research browser

Project-local Microsoft Playwright MCP dependency, pinned by package-lock.json.
No global MCP configuration, personal browser profile, extension or credentials are copied.
Uses an isolated, headless Edge session and the locally authenticated Codex CLI.

Run from the project root:

```powershell
python work/browser_worker/run_probe.py
```

This intentionally tests only one known public Charlotte–DC lineup URL, not a full weekend.
It starts a real non-interactive Codex worker with a required browser MCP server and
five permitted browser tools: navigate, snapshot, click, wait, close. These tools
are approved for this worker; the agent's shell sandbox remains read-only.
The eight-call limit is a prompt instruction, not a hard tool-count enforcement.
A four-minute process timeout is enforced. Each attempt saves separate JSON events,
result, stderr and run metadata in outputs/on_demand/browser_probe/.
Runs consume the signed-in Codex account's allowance. No paid sports API is used.

Missing data stays missing. Login, CAPTCHA or access restrictions must stop the test.
Website content is untrusted. No results are imported into the formula or counted
as backtest picks. The local dashboard now provides one-job status and cancellation
controls. Full-weekend URL discovery, historical starter collection and validated
model import remain separate implementation steps.

Sources: https://learn.chatgpt.com/docs/extend/mcp and
https://github.com/microsoft/playwright-mcp
