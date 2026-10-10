param(
    [string]$Weekend,
    [string]$TaskName = "WeekendShotsProfitCollector"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvPath = Join-Path $ProjectRoot ".env"
$HasProcessKey = -not [string]::IsNullOrWhiteSpace($env:THE_ODDS_API_KEY)
$HasFileKey = $false
if (Test-Path -LiteralPath $EnvPath) {
    $HasFileKey = [bool](Select-String -LiteralPath $EnvPath -Pattern '^THE_ODDS_API_KEY=.+$' -Quiet)
}
if (-not ($HasProcessKey -or $HasFileKey)) {
    throw "THE_ODDS_API_KEY is not configured. Copy .env.example to .env and add the key before registering the task."
}

$Python = $null
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $ExistingTask -and (Test-Path -LiteralPath $ExistingTask.Actions.Execute)) {
    $Python = $ExistingTask.Actions.Execute
}
foreach ($Name in @("python", "py")) {
    if (-not [string]::IsNullOrWhiteSpace($Python)) { break }
    $Command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $Command) { continue }
    $ProbeArgs = if ($Name -eq "py") { @("-3", "-c", "import sys; print(sys.executable)") } else { @("-c", "import sys; print(sys.executable)") }
    $Resolved = (& $Command.Source @ProbeArgs 2>$null)
    if ($LASTEXITCODE -eq 0 -and $null -ne $Resolved) {
        $Candidate = ([string]$Resolved).Trim()
        if (Test-Path -LiteralPath $Candidate) { $Python = $Candidate }
    }
}
if ([string]::IsNullOrWhiteSpace($Python)) {
    $Python = Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA "Python\pythoncore-*\python.exe"), (Join-Path $env:LOCALAPPDATA "Programs\Python\Python*\python.exe") -File -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Could not resolve the real Python executable for the scheduled task."
}
$Runner = Join-Path $PSScriptRoot "run_profit_collector.py"
$Arguments = if ([string]::IsNullOrWhiteSpace($Weekend)) {
    ('"{0}" --watch' -f $Runner)
} else {
    ('"{0}" --weekend {1} --watch' -f $Runner, $Weekend)
}
$Action = New-ScheduledTaskAction -Execute $Python -Argument $Arguments -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At "00:00"
$Trigger.Repetition = (New-ScheduledTaskTrigger -Once -At "00:00" -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 1)).Repetition
$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 4)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Paper-only frozen-v3 and volume-v4 football odds collector. Exits when no candidate is within two hours." -Force | Out-Null
$Scope = if ([string]::IsNullOrWhiteSpace($Weekend)) { "the nearest active frozen v3 weekend" } else { "weekend $Weekend" }
Write-Output "Registered $TaskName for $Scope. It checks every 10 minutes and never places wagers."
