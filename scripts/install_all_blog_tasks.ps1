param(
  [string]$PythonExe = "py",
  [string]$PythonArgs = "-3 -B",
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$CleanupWindowStart = "08:20",
  [string]$CleanupWindowEnd = "08:21",
  [string]$BluetoothWindowStart = "08:22",
  [string]$BluetoothWindowEnd = "08:24",
  [string]$FindWindowStart = "08:26",
  [string]$FindWindowEnd = "08:27",
  [string]$TranslateWindowStart = "08:28",
  [string]$TranslateWindowEnd = "08:30",
  [string]$WatchdogAt = "08:35",
  [bool]$ReplaceExisting = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Ensure-Script([string]$name) {
  $path = Join-Path $RepoRoot ("scripts\" + $name)
  if (-not (Test-Path $path)) {
    throw "Missing script: $path"
  }
  return $path
}

function Remove-TaskIfExists([string]$taskName) {
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
}

function Remove-TasksByPattern([string]$pattern) {
  $existing = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -like $pattern }
  foreach ($task in $existing) {
    Unregister-ScheduledTask -TaskName $task.TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
  }
}

function Invoke-Installer([string]$scriptPath, [scriptblock]$installer) {
  Write-Output ""
  Write-Output "Running installer: $scriptPath"
  & $installer
  if (-not $?) {
    throw "Installer failed: $scriptPath"
  }
}

$cleanupInstaller = Ensure-Script "install_storage_impact_blog_task.ps1"
$bluetoothInstaller = Ensure-Script "install_protocol_blog_morning_tasks.ps1"
$findInstaller = Ensure-Script "install_find_ai_blog_task.ps1"
$translateInstaller = Ensure-Script "install_translate_ai_blog_tasks.ps1"
$watchdogInstaller = Ensure-Script "install_blog_watchdog_task.ps1"

if ($ReplaceExisting) {
  Remove-TasksByPattern "WeiLuoGe-Live-Update-Blog-Morning-*"
  $legacyTaskNames = @(
    "WeiLuoGe-Blog-Daily-09-30",
    "WeiLuoGe-Live-Update-Blog-Morning-1",
    "WeiLuoGe-Live-Update-Blog-Morning-2",
    "WeiLuoGe-Live-Update-Blog-Morning-3",
    "WeiLuoGe-Blog-Watchdog-08-35"
  )
  foreach ($taskName in $legacyTaskNames) {
    Remove-TaskIfExists $taskName
  }
}

Invoke-Installer $cleanupInstaller {
  & $cleanupInstaller `
    -PythonExe $PythonExe `
    -PythonArgs $PythonArgs `
    -RepoRoot $RepoRoot `
    -WindowStart $CleanupWindowStart `
    -WindowEnd $CleanupWindowEnd `
    -PostsPerDay 1 `
    -ReplaceExisting:$ReplaceExisting
}

Invoke-Installer $bluetoothInstaller {
  & $bluetoothInstaller `
    -PythonExe $PythonExe `
    -PythonArgs $PythonArgs `
    -RepoRoot $RepoRoot `
    -WindowStart $BluetoothWindowStart `
    -WindowEnd $BluetoothWindowEnd `
    -PostsPerDay 2 `
    -ReplaceExisting:$ReplaceExisting
}

Invoke-Installer $findInstaller {
  & $findInstaller `
    -PythonExe $PythonExe `
    -PythonArgs $PythonArgs `
    -RepoRoot $RepoRoot `
    -WindowStart $FindWindowStart `
    -WindowEnd $FindWindowEnd `
    -PostsPerDay 1 `
    -ReplaceExisting:$ReplaceExisting
}

Invoke-Installer $translateInstaller {
  & $translateInstaller `
    -PythonExe $PythonExe `
    -PythonArgs $PythonArgs `
    -RepoRoot $RepoRoot `
    -WindowStart $TranslateWindowStart `
    -WindowEnd $TranslateWindowEnd `
    -PostsPerDay 2 `
    -ReplaceExisting:$ReplaceExisting
}

Invoke-Installer $watchdogInstaller {
  & $watchdogInstaller `
    -PythonExe $PythonExe `
    -PythonArgs $PythonArgs `
    -RepoRoot $RepoRoot `
    -PublishAt $WatchdogAt `
    -TaskName "WeiLuoGe-Blog-Watchdog-08-35"
}

Write-Output ""
Write-Output "Installed full daily blog schedule:"
Write-Output "  Cleanup PRO: 1 slot between $CleanupWindowStart and $CleanupWindowEnd"
Write-Output "  Bluetooth: 2 slots between $BluetoothWindowStart and $BluetoothWindowEnd"
Write-Output "  Find AI: 1 slot between $FindWindowStart and $FindWindowEnd"
Write-Output "  Translate: 2 slots between $TranslateWindowStart and $TranslateWindowEnd"
Write-Output "  Watchdog: daily at $WatchdogAt"
