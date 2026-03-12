param(
  [string]$PythonExe = "py",
  [string]$PythonArgs = "-3 -B",
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$PublishAt = "08:40",
  [string]$TaskName = "WeiLuoGe-Storage-Impact-Blog-Daily-08-40"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptPath = Join-Path $RepoRoot "scripts\\blog_cleanup_focus_scheduler.py"
if (-not (Test-Path $ScriptPath)) {
  throw "Missing script: $ScriptPath"
}

$PythonCommand = (Get-Command $PythonExe -ErrorAction Stop).Source
if (-not $PythonCommand) {
  throw "Cannot resolve Python command: $PythonExe"
}

# Remove older default task names so the machine only keeps one active storage-impact schedule.
$legacyTaskNames = @(
  "WeiLuoGe-Storage-Impact-Blog-Daily-09-15",
  "WeiLuoGe-Storage-Impact-Blog-Daily-09-00"
)
foreach ($legacyTaskName in $legacyTaskNames) {
  if ($TaskName -ne $legacyTaskName) {
    Unregister-ScheduledTask -TaskName $legacyTaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
  }
}

$Args = "$PythonArgs `"$ScriptPath`" run --repo-root `"$RepoRoot`" --git-commit --git-push"
$Action = New-ScheduledTaskAction -Execute $PythonCommand -Argument $Args
$Trigger = New-ScheduledTaskTrigger -Daily -At $PublishAt

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Force | Out-Null

Write-Output "Installed task: $TaskName"
Write-Output "Schedule: daily at $PublishAt"
Write-Output "Command: $PythonCommand $Args"
