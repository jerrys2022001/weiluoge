param(
  [string]$PythonExe = "python",
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$LogRoot = "D:\Operation Log",
  [int]$MinPosts = 10,
  [int]$MaxPosts = 16,
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

& $PythonExe --version | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Cannot run Python command: $PythonExe"
}

New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null

$PlanTaskName = "$TaskPrefix-Plan"
$WorkerTaskName = "$TaskPrefix-Worker"

$PlanCommand = "`"$PythonExe`" `"$ScriptPath`" plan --log-root `"$LogRoot`" --min-posts $MinPosts --max-posts $MaxPosts --day-start $DayStart --day-end $DayEnd"
$WorkerCommand = "`"$PythonExe`" `"$ScriptPath`" run --log-root `"$LogRoot`" --min-posts $MinPosts --max-posts $MaxPosts --day-start $DayStart --day-end $DayEnd"

& schtasks /Create /F /TN $PlanTaskName /SC DAILY /ST $PlanTime /TR $PlanCommand | Out-Null
& schtasks /Create /F /TN $WorkerTaskName /SC MINUTE /MO $WorkerEveryMinutes /TR $WorkerCommand | Out-Null

if ($LASTEXITCODE -ne 0) {
  throw "Failed to create one or more scheduled tasks."
}

Write-Output "Installed tasks:"
Write-Output " - $PlanTaskName"
Write-Output " - $WorkerTaskName"
Write-Output ""
Write-Output "Task commands:"
Write-Output " - $PlanCommand"
Write-Output " - $WorkerCommand"
Write-Output ""
Write-Output "Logs and plans are stored under: $LogRoot\TwitterStoryBot"
