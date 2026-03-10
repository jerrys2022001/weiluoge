param(
  [string]$PythonExe = "python",
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$LogRoot = "D:\Operation Log",
  [int]$MinPosts = 5,
  [int]$MaxPosts = 10,
  [string]$DayStart = "08:00",
  [string]$DayEnd = "23:30",
  [ValidateSet("classic", "velocai-mix")]
  [string]$ContentMode = "classic",
  [ValidateSet("playwright-first", "api-first", "playwright", "api")]
  [string]$PostMode = "playwright-first",
  [string]$UpdateTopicsFile = "",
  [int]$WorkerEveryMinutes = 60,
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

$MergedTaskName = "$TaskPrefix-Plan"
$LegacyWorkerTaskName = "$TaskPrefix-Worker"

$CommonArgs = "--log-root `"$LogRoot`" --min-posts $MinPosts --max-posts $MaxPosts --day-start $DayStart --day-end $DayEnd --content-mode $ContentMode --post-mode $PostMode"
if ($UpdateTopicsFile) {
  $CommonArgs += " --update-topics-file `"$UpdateTopicsFile`""
}
$RunArgs = "`"$ScriptPath`" run $CommonArgs"

$RunAction = New-ScheduledTaskAction -Execute $PythonCommand -Argument $RunArgs

$RunTrigger = New-ScheduledTaskTrigger `
  -Once `
  -At (Get-Date).Date.AddMinutes(1) `
  -RepetitionInterval (New-TimeSpan -Minutes $WorkerEveryMinutes) `
  -RepetitionDuration (New-TimeSpan -Days 3650)

if (Get-ScheduledTask -TaskName $LegacyWorkerTaskName -ErrorAction SilentlyContinue) {
  Unregister-ScheduledTask -TaskName $LegacyWorkerTaskName -Confirm:$false | Out-Null
}

Register-ScheduledTask -TaskName $MergedTaskName -Action $RunAction -Trigger $RunTrigger -Force | Out-Null

Write-Output "Installed task:"
Write-Output " - $MergedTaskName"
Write-Output ""
Write-Output "Task command:"
Write-Output " - $PythonCommand $RunArgs"
Write-Output ""
Write-Output "Logs and plans are stored under: $LogRoot\TwitterStoryBot"
