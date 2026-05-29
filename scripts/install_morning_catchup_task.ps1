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

$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Principal = New-ScheduledTaskPrincipal -UserId $CurrentUser -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$Args = "$PythonArgs `"$ScriptPath`" --repo-root `"$RepoRoot`" --blog-ready-after $BlogReadyAfter --home-ready-after $HomeReadyAfter"
$Action = New-ScheduledTaskAction -Execute $PythonCommand -Argument $Args -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $CurrentUser
if ($LogonDelay) {
  $Trigger.Delay = $LogonDelay
}

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force -ErrorAction Stop | Out-Null

Write-Output "Installed task: $TaskName"
Write-Output "Schedule: at logon for $CurrentUser (delay $LogonDelay)"
Write-Output "Command: $PythonCommand $Args"
