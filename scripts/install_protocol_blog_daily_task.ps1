param(
  [string]$PythonExe = "py",
  [string]$PythonArgs = "-3 -B",
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$PublishAt = "10:00",
  [string]$TaskName = "WeiLuoGe-Bluetooth-Protocol-Blog-Daily-10-00"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptPath = Join-Path $RepoRoot "scripts\blog_protocol_daily_scheduler.py"
if (-not (Test-Path $ScriptPath)) {
  throw "Missing script: $ScriptPath"
}

$PythonCommand = (Get-Command $PythonExe -ErrorAction Stop).Source
if (-not $PythonCommand) {
  throw "Cannot resolve Python command: $PythonExe"
}

$Args = "$PythonArgs `"$ScriptPath`" run --repo-root `"$RepoRoot`" --git-commit --git-push"
$Action = New-ScheduledTaskAction -Execute $PythonCommand -Argument $Args
$Trigger = New-ScheduledTaskTrigger -Daily -At $PublishAt

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Force | Out-Null

Write-Output "Installed task: $TaskName"
Write-Output "Schedule: daily at $PublishAt"
Write-Output "Command: $PythonCommand $Args"
