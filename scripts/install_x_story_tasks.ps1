param(
  [string]$PythonExe = "python",
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$LogRoot = "D:\Operation Log",
  [int]$MinPosts = 10,
  [int]$MaxPosts = 20,
  [string]$DayStart = "08:00",
  [string]$DayEnd = "23:30",
  [string]$PlanTime = "00:05",
  [int]$WorkerEveryMinutes = 5,
  [string]$TaskPrefix = "WeiLuoGe-XStory"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($MinPosts -lt 1) {
  throw "MinPosts must be >= 1."
}

if ($MaxPosts -lt $MinPosts) {
  throw "MaxPosts must be >= MinPosts."
}

if ($WorkerEveryMinutes -lt 1) {
  throw "WorkerEveryMinutes must be >= 1."
}

$ScriptPath = Join-Path $RepoRoot "scripts\x_story_scheduler.py"
if (-not (Test-Path $ScriptPath)) {
  throw "Missing script: $ScriptPath"
}

$PythonCommand = (Get-Command $PythonExe -ErrorAction Stop).Source
if (-not $PythonCommand) {
  throw "Cannot resolve Python command: $PythonExe"
}

New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null

$PlanTaskName = "$TaskPrefix-Plan"
$WorkerTaskName = "$TaskPrefix-Worker"

$CommonArgs = "--log-root `"$LogRoot`" --min-posts $MinPosts --max-posts $MaxPosts --day-start $DayStart --day-end $DayEnd"
$PlanArgs = "`"$ScriptPath`" plan $CommonArgs"
$WorkerArgs = "`"$ScriptPath`" run $CommonArgs"

$PlanAction = New-ScheduledTaskAction -Execute $PythonCommand -Argument $PlanArgs
$WorkerAction = New-ScheduledTaskAction -Execute $PythonCommand -Argument $WorkerArgs

$PlanTrigger = New-ScheduledTaskTrigger -Daily -At $PlanTime

$WorkerTrigger = New-ScheduledTaskTrigger `
  -Once `
  -At (Get-Date).Date.AddMinutes(1) `
  -RepetitionInterval (New-TimeSpan -Minutes $WorkerEveryMinutes) `
  -RepetitionDuration (New-TimeSpan -Days 3650)

Register-ScheduledTask -TaskName $PlanTaskName -Action $PlanAction -Trigger $PlanTrigger -Force | Out-Null
Register-ScheduledTask -TaskName $WorkerTaskName -Action $WorkerAction -Trigger $WorkerTrigger -Force | Out-Null

Write-Output "Installed tasks:"
Write-Output " - $PlanTaskName"
Write-Output " - $WorkerTaskName"
Write-Output ""
Write-Output "Task commands:"
Write-Output " - $PythonCommand $PlanArgs"
Write-Output " - $PythonCommand $WorkerArgs"
Write-Output ""
Write-Output "Logs and plans are stored under: $LogRoot\TwitterStoryBot"
