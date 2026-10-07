[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TaskFile,

    [ValidateSet('inspect', 'edit', 'operate')]
    [string]$Mode = 'inspect',

    [string]$Model = 'openrouter/free',

    [ValidateRange(2, 40)]
    [int]$MaxSessionTurns = 12,

    [ValidateRange(0, 200)]
    [int]$MaxToolCalls = 40,

    [string]$MaxWallTime = '8m',

    [ValidateRange(4000, 80000)]
    [int]$MaxPromptCharacters = 48000,

    [string]$OutputFile
)

$ErrorActionPreference = 'Stop'

$workerRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $workerRoot '..\..')).Path
$policyPath = Join-Path $workerRoot 'WORKER_POLICY.md'
$resolvedTask = (Resolve-Path -LiteralPath $TaskFile).Path

$policy = Get-Content -Raw -LiteralPath $policyPath
$task = Get-Content -Raw -LiteralPath $resolvedTask
$prompt = @"
$policy

## Assigned task

$task
"@

if ($prompt.Length -gt $MaxPromptCharacters) {
    throw "Task packet is $($prompt.Length) characters; limit is $MaxPromptCharacters. Replace raw data with paths, schemas, or summaries."
}

$approvalMode = switch ($Mode) {
    'inspect' { 'plan' }
    'edit' { 'auto-edit' }
    'operate' { 'auto' }
}

$qwenArgs = @(
    '--auth-type', 'openai',
    '--model', $Model,
    '--approval-mode', $approvalMode,
    '--output-format', 'text',
    '--max-session-turns', $MaxSessionTurns,
    '--max-tool-calls', $MaxToolCalls,
    '--max-subagent-depth', '1',
    '--max-wall-time', $MaxWallTime,
    $prompt
)

Push-Location $projectRoot
try {
    # Windows PowerShell converts native stderr lines into ErrorRecord objects.
    # Keep those lines in the worker log and use the native exit code as the
    # authoritative success/failure signal.
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    if ($OutputFile) {
        $resolvedOutput = if ([System.IO.Path]::IsPathRooted($OutputFile)) {
            $OutputFile
        } else {
            Join-Path $projectRoot $OutputFile
        }
        & qwen @qwenArgs 2>&1 | Tee-Object -FilePath $resolvedOutput
    } else {
        & qwen @qwenArgs
    }

    $qwenExitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference
    if ($qwenExitCode -ne 0) {
        throw "Qwen exited with code $qwenExitCode."
    }
} finally {
    $ErrorActionPreference = 'Stop'
    Pop-Location
}
