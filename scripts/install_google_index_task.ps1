param(
  [string]$PythonExe = "py",
  [string]$PythonArgs = "-3 -B",
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$RunAt = "10:30",
  [string]$TaskName = "WeiLuoGe-Google-Index-Daily-10-30",
  [string]$LogRoot = "D:\Operation Log",
  [string]$SitemapUrl = "https://velocai.net/sitemap.xml",
  [string]$SiteUrl = "https://velocai.net/",
  [int]$MaxUrlsPerRun = 20,
  [string]$ProfileDirectory = "Default",
  [string]$SourceUserDataDir = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptPath = Join-Path $RepoRoot "scripts\google_index_daily_scheduler.py"
if (-not (Test-Path $ScriptPath)) {
  throw "Missing script: $ScriptPath"
}

$PythonCommand = (Get-Command $PythonExe -ErrorAction Stop).Source
if (-not $PythonCommand) {
  throw "Cannot resolve Python command: $PythonExe"
}

$Args = "$PythonArgs `"$ScriptPath`" run --log-root `"$LogRoot`" --sitemap-url `"$SitemapUrl`" --site-url `"$SiteUrl`" --max-urls-per-run $MaxUrlsPerRun --profile-directory `"$ProfileDirectory`""
if (-not [string]::IsNullOrWhiteSpace($SourceUserDataDir)) {
  $Args += " --source-user-data-dir `"$SourceUserDataDir`""
}
$Action = New-ScheduledTaskAction -Execute $PythonCommand -Argument $Args
$Trigger = New-ScheduledTaskTrigger -Daily -At $RunAt

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Force | Out-Null

Write-Output "Installed task: $TaskName"
Write-Output "Schedule: daily at $RunAt"
Write-Output "Command: $PythonCommand $Args"
