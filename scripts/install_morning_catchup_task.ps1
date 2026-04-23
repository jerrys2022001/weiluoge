param(
  [string]$PythonExe = "py",
  [string]$PythonArgs = "-3 -B",
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$TaskName = "WeiLuoGe-Morning-Catchup-AtLogOn",
  [string]$LogonDelay = "PT5M",
  [string]$BlogReadyAfter = "08:35",
  [string]$HomeReadyAfter = "08:40"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptPath = Join-Path $RepoRoot "scripts\morning_publish_catchup.py"
if (-not (Test-Path $ScriptPath)) {
  throw "Missing script: $ScriptPath"
}

$PythonCommand = (Get-Command $PythonExe -ErrorAction Stop).Source
if (-not $PythonCommand) {
  throw "Cannot resolve Python command: $PythonExe"
}

$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$Args = "$PythonArgs `"$ScriptPath`" --repo-root `"$RepoRoot`" --blog-ready-after $BlogReadyAfter --home-ready-after $HomeReadyAfter"
$Action = New-ScheduledTaskAction -Execute $PythonCommand -Argument $Args -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn
if ($LogonDelay) {
  $Trigger.Delay = $LogonDelay
}

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null

Write-Output "Installed task: $TaskName"
Write-Output "Schedule: at logon (delay $LogonDelay)"
Write-Output "Command: $PythonCommand $Args"
