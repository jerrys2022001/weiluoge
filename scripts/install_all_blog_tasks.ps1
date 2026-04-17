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
  [string]$DualShotWindowStart = "08:28",
  [string]$DualShotWindowEnd = "08:29",
  [string]$TranslateWindowStart = "08:29",
  [string]$TranslateWindowEnd = "08:30",
  [string]$HomeBriefAt = "08:30",
  [string]$HomeBriefCheckAt = "08:40",
  [string]$PreflightAt = "08:15",
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

function Assert-TaskExists([string]$taskName) {
  $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
  if ($null -eq $task) {
    throw "Expected scheduled task was not installed: $taskName"
  }
  Write-Output "Verified task: $taskName"
}

function Apply-TaskRuntimeDefaults([string]$taskName) {
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
  Set-ScheduledTask -TaskName $taskName -Settings $settings | Out-Null
  Write-Output "Hardened task settings: $taskName"
}

$cleanupInstaller = Ensure-Script "install_storage_impact_blog_task.ps1"
$bluetoothInstaller = Ensure-Script "install_protocol_blog_morning_tasks.ps1"
$findInstaller = Ensure-Script "install_find_ai_blog_task.ps1"
$dualshotInstaller = Ensure-Script "install_dualshot_blog_task.ps1"
$translateInstaller = Ensure-Script "install_translate_ai_blog_tasks.ps1"
$homeBriefInstaller = Ensure-Script "install_home_brief_daily_task.ps1"
$preflightInstaller = Ensure-Script "install_blog_preflight_task.ps1"
$watchdogInstaller = Ensure-Script "install_blog_watchdog_task.ps1"

if ($ReplaceExisting) {
  Remove-TasksByPattern "WeiLuoGe-Live-Update-Blog-Morning-*"
  $legacyTaskNames = @(
    "WeiLuoGe-Blog-Daily-09-30",
    "WeiLuoGe-Blog-Preflight-08-15",
    "WeiLuoGe-Live-Update-Blog-Morning-1",
    "WeiLuoGe-Live-Update-Blog-Morning-2",
    "WeiLuoGe-Live-Update-Blog-Morning-3",
    "WeiLuoGe-Blog-Watchdog-08-35",
    "WeiLuoGe-Home-Brief-Check-08-40"
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

Invoke-Installer $dualshotInstaller {
  & $dualshotInstaller `
    -PythonExe $PythonExe `
    -PythonArgs $PythonArgs `
    -RepoRoot $RepoRoot `
    -WindowStart $DualShotWindowStart `
    -WindowEnd $DualShotWindowEnd `
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
    -PostsPerDay 1 `
    -ReplaceExisting:$ReplaceExisting
}

Invoke-Installer $homeBriefInstaller {
  & $homeBriefInstaller `
    -PythonExe $PythonExe `
    -PythonArgs $PythonArgs `
    -RepoRoot $RepoRoot `
    -PublishAt $HomeBriefAt `
    -CheckAt $HomeBriefCheckAt `
    -TaskName "WeiLuoGe-Home-Brief-Daily-08-30" `
    -CheckTaskName "WeiLuoGe-Home-Brief-Check-08-40"
}

Invoke-Installer $preflightInstaller {
  & $preflightInstaller `
    -PythonExe $PythonExe `
    -PythonArgs $PythonArgs `
    -RepoRoot $RepoRoot `
    -CheckAt $PreflightAt `
    -TaskName "WeiLuoGe-Blog-Preflight-08-15"
}

Invoke-Installer $watchdogInstaller {
  & $watchdogInstaller `
    -PythonExe $PythonExe `
    -PythonArgs $PythonArgs `
    -RepoRoot $RepoRoot `
    -PublishAt $WatchdogAt `
    -TaskName "WeiLuoGe-Blog-Watchdog-08-35"
}

$expectedTaskNames = @(
  "WeiLuoGe-Storage-Impact-Blog-Daily-1",
  "WeiLuoGe-Bluetooth-Protocol-Blog-Morning-1",
  "WeiLuoGe-Bluetooth-Protocol-Blog-Morning-2",
  "WeiLuoGe-Find-AI-Blog-Morning-1",
  "WeiLuoGe-DualShot-Camera-Blog-Morning-1",
  "WeiLuoGe-Translate-AI-Blog-Morning-1",
  "WeiLuoGe-Home-Brief-Daily-08-30",
  "WeiLuoGe-Home-Brief-Check-08-40",
  "WeiLuoGe-Blog-Preflight-08-15",
  "WeiLuoGe-Blog-Watchdog-08-35"
)

Write-Output ""
Write-Output "Verifying installed site tasks..."
foreach ($taskName in $expectedTaskNames) {
  Assert-TaskExists $taskName
  Apply-TaskRuntimeDefaults $taskName
}

Write-Output ""
Write-Output "Installed full daily site schedule:"
Write-Output "  Cleanup PRO: 1 slot between $CleanupWindowStart and $CleanupWindowEnd"
Write-Output "  Bluetooth Explorer: 2 slots between $BluetoothWindowStart and $BluetoothWindowEnd"
Write-Output "  Find AI: 1 slot between $FindWindowStart and $FindWindowEnd"
Write-Output "  DualShot Camera: 1 slot between $DualShotWindowStart and $DualShotWindowEnd"
Write-Output "  Translate AI: 1 slot between $TranslateWindowStart and $TranslateWindowEnd"
Write-Output "  Home Brief run: daily at $HomeBriefAt"
Write-Output "  Home Brief check: daily at $HomeBriefCheckAt"
Write-Output "  Blog preflight: daily at $PreflightAt"
Write-Output "  Blog watchdog: daily at $WatchdogAt"
