param(
  [string]$PythonExe = "py",
  [string]$PythonArgs = "-3 -B",
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$PublishAt = "08:30",
  [string]$CheckAt = "08:40",
  [string]$TaskName = "WeiLuoGe-Home-Brief-Daily-08-30",
  [string]$CheckTaskName = "WeiLuoGe-Home-Brief-Check-08-40"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptPath = Join-Path $RepoRoot "scripts\home_brief_daily_scheduler.py"
if (-not (Test-Path $ScriptPath)) {
  throw "Missing script: $ScriptPath"
}

$PythonCommand = (Get-Command $PythonExe -ErrorAction Stop).Source
if (-not $PythonCommand) {
  throw "Cannot resolve Python command: $PythonExe"
}

$LogDir = Join-Path $RepoRoot "output\home-brief-logs"

$RunArgs = "$PythonArgs `"$ScriptPath`" run --repo-root `"$RepoRoot`" --git-commit --git-push --log-dir `"$LogDir`""
$RunAction = New-ScheduledTaskAction -Execute $PythonCommand -Argument $RunArgs
$RunTrigger = New-ScheduledTaskTrigger -Daily -At $PublishAt

Register-ScheduledTask -TaskName $TaskName -Action $RunAction -Trigger $RunTrigger -Force | Out-Null

$CheckArgs = "$PythonArgs `"$ScriptPath`" check --repo-root `"$RepoRoot`" --git-commit --git-push --log-dir `"$LogDir`""
$CheckAction = New-ScheduledTaskAction -Execute $PythonCommand -Argument $CheckArgs
$CheckTrigger = New-ScheduledTaskTrigger -Daily -At $CheckAt

Register-ScheduledTask -TaskName $CheckTaskName -Action $CheckAction -Trigger $CheckTrigger -Force | Out-Null

Write-Output "Installed task: $TaskName"
Write-Output "Schedule: daily at $PublishAt"
Write-Output "Command: $PythonCommand $RunArgs"
Write-Output "Installed task: $CheckTaskName"
Write-Output "Schedule: daily at $CheckAt"
Write-Output "Command: $PythonCommand $CheckArgs"
