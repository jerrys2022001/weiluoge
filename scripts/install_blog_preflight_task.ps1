param(
  [string]$PythonExe = "py",
  [string]$PythonArgs = "-3 -B",
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$CheckAt = "08:15",
  [string]$TaskName = "WeiLuoGe-Blog-Preflight-08-15"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptPath = Join-Path $RepoRoot "scripts\blog_scheduler_preflight.py"
if (-not (Test-Path $ScriptPath)) {
  throw "Missing script: $ScriptPath"
}

$PythonCommand = (Get-Command $PythonExe -ErrorAction Stop).Source
if (-not $PythonCommand) {
  throw "Cannot resolve Python command: $PythonExe"
}

$Args = "$PythonArgs `"$ScriptPath`" --repo-root `"$RepoRoot`""
$Action = New-ScheduledTaskAction -Execute $PythonCommand -Argument $Args -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At $CheckAt
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null

Write-Output "Installed task: $TaskName"
Write-Output "Schedule: daily at $CheckAt"
Write-Output "Command: $PythonCommand $Args"
