param(
  [string]$PythonExe = "py",
  [string]$PythonArgs = "-3 -B",
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$BluetoothWindowStart = "08:22",
  [string]$BluetoothWindowEnd = "08:23",
  [double]$BluetoothSimilarityThreshold = 0.80,
  [string]$FindWindowStart = "08:26",
  [string]$FindWindowEnd = "08:27",
  [double]$FindSimilarityThreshold = 0.70,
  [string]$DualShotWindowStart = "08:28",
  [string]$DualShotWindowEnd = "08:29",
  [double]$DualShotSimilarityThreshold = 0.50,
  [string]$OctopusWindowStart = "08:31",
  [string]$OctopusWindowEnd = "08:32",
  [double]$OctopusSimilarityThreshold = 0.65,
  [string]$HomeBriefAt = "08:30",
  [string]$HomeBriefCheckAt = "08:40",
  [string]$HomeBriefSecondaryCheckAt = "20:30",
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

function Apply-TaskRuntimeDefaults([string]$taskName, [bool]$StartWhenAvailable = $true) {
  $settingsArgs = @{
    AllowStartIfOnBatteries    = $true
    DontStopIfGoingOnBatteries = $true
  }
  if ($StartWhenAvailable) {
    $settingsArgs.StartWhenAvailable = $true
  }
  $settings = New-ScheduledTaskSettingsSet @settingsArgs
  Set-ScheduledTask -TaskName $taskName -Settings $settings | Out-Null
  if ($StartWhenAvailable) {
    Write-Output "Hardened task settings: $taskName (StartWhenAvailable enabled)"
  } else {
    Write-Output "Hardened task settings: $taskName"
  }
}

$bluetoothInstaller = Ensure-Script "install_protocol_blog_morning_tasks.ps1"
$findInstaller = Ensure-Script "install_find_ai_blog_task.ps1"
$dualshotInstaller = Ensure-Script "install_dualshot_blog_task.ps1"
$octopusInstaller = Ensure-Script "install_octopus_blog_task.ps1"
$homeBriefInstaller = Ensure-Script "install_home_brief_daily_task.ps1"
$preflightInstaller = Ensure-Script "install_blog_preflight_task.ps1"
$watchdogInstaller = Ensure-Script "install_blog_watchdog_task.ps1"
$morningCatchupInstaller = Ensure-Script "install_morning_catchup_task.ps1"

if ($ReplaceExisting) {
  Remove-TasksByPattern "WeiLuoGe-Live-Update-Blog-Morning-*"
  Remove-TasksByPattern "WeiLuoGe-Storage-Impact-Blog-Daily-*"
  Remove-TasksByPattern "WeiLuoGe-Translate-AI-Blog-Morning-*"
  $legacyTaskNames = @(
    "WeiLuoGe-Blog-Daily-09-30",
    "WeiLuoGe-Blog-Preflight-08-15",
    "WeiLuoGe-Live-Update-Blog-Morning-1",
    "WeiLuoGe-Live-Update-Blog-Morning-2",
    "WeiLuoGe-Live-Update-Blog-Morning-3",
    "WeiLuoGe-Storage-Impact-Blog-Daily-1",
    "WeiLuoGe-Bluetooth-Protocol-Blog-Morning-2",
    "WeiLuoGe-Translate-AI-Blog-Morning-1",
    "WeiLuoGe-Octopus-Blog-Morning-2",
    "WeiLuoGe-Blog-Watchdog-08-35",
    "WeiLuoGe-Home-Brief-Check-08-40",
    "WeiLuoGe-Home-Brief-Check-20-30",
    "WeiLuoGe-Morning-Catchup-AtLogOn"
  )
  foreach ($taskName in $legacyTaskNames) {
    Remove-TaskIfExists $taskName
  }
}

Invoke-Installer $bluetoothInstaller {
  & $bluetoothInstaller `
    -PythonExe $PythonExe `
    -PythonArgs $PythonArgs `
    -RepoRoot $RepoRoot `
    -WindowStart $BluetoothWindowStart `
    -WindowEnd $BluetoothWindowEnd `
    -PostsPerDay 1 `
    -SimilarityThreshold $BluetoothSimilarityThreshold `
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
    -SimilarityThreshold $FindSimilarityThreshold `
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
    -SimilarityThreshold $DualShotSimilarityThreshold `
    -ReplaceExisting:$ReplaceExisting
}

Invoke-Installer $octopusInstaller {
  & $octopusInstaller `
    -PythonExe $PythonExe `
    -PythonArgs $PythonArgs `
    -RepoRoot $RepoRoot `
    -WindowStart $OctopusWindowStart `
    -WindowEnd $OctopusWindowEnd `
    -PostsPerDay 1 `
    -SimilarityThreshold $OctopusSimilarityThreshold `
    -ReplaceExisting:$ReplaceExisting
}

Invoke-Installer $homeBriefInstaller {
  & $homeBriefInstaller `
    -PythonExe $PythonExe `
    -PythonArgs $PythonArgs `
    -RepoRoot $RepoRoot `
    -PublishAt $HomeBriefAt `
    -CheckAt $HomeBriefCheckAt `
    -SecondaryCheckAt $HomeBriefSecondaryCheckAt `
    -TaskName "WeiLuoGe-Home-Brief-Daily-08-30" `
    -CheckTaskName "WeiLuoGe-Home-Brief-Check-08-40" `
    -SecondaryCheckTaskName "WeiLuoGe-Home-Brief-Check-20-30"
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

Invoke-Installer $morningCatchupInstaller {
  & $morningCatchupInstaller `
    -PythonExe $PythonExe `
    -PythonArgs $PythonArgs `
    -RepoRoot $RepoRoot `
    -TaskName "WeiLuoGe-Morning-Catchup-AtLogOn"
}

$expectedTaskNames = @(
  "WeiLuoGe-Bluetooth-Protocol-Blog-Morning-1",
  "WeiLuoGe-Find-AI-Blog-Morning-1",
  "WeiLuoGe-DualShot-Camera-Blog-Morning-1",
  "WeiLuoGe-Octopus-Blog-Morning-1",
  "WeiLuoGe-Home-Brief-Daily-08-30",
  "WeiLuoGe-Home-Brief-Check-08-40",
  "WeiLuoGe-Home-Brief-Check-20-30",
  "WeiLuoGe-Blog-Preflight-08-15",
  "WeiLuoGe-Blog-Watchdog-08-35",
  "WeiLuoGe-Morning-Catchup-AtLogOn"
)

Write-Output ""
Write-Output "Verifying installed site tasks..."
foreach ($taskName in $expectedTaskNames) {
  Assert-TaskExists $taskName
  $allowLateCatchup = $true
  Apply-TaskRuntimeDefaults -taskName $taskName -StartWhenAvailable:$allowLateCatchup
}

Write-Output ""
Write-Output "Installed full daily site schedule:"
Write-Output "  Bluetooth Explorer: 1 slot between $BluetoothWindowStart and $BluetoothWindowEnd (similarity threshold $BluetoothSimilarityThreshold)"
Write-Output "  Find AI: 1 slot between $FindWindowStart and $FindWindowEnd (similarity threshold $FindSimilarityThreshold)"
Write-Output "  Dual Camera: 1 slot between $DualShotWindowStart and $DualShotWindowEnd (similarity threshold $DualShotSimilarityThreshold)"
Write-Output "  Octopus: 1 slot between $OctopusWindowStart and $OctopusWindowEnd (similarity threshold $OctopusSimilarityThreshold)"
Write-Output "  Home Brief run: daily at $HomeBriefAt"
Write-Output "  Home Brief check: daily at $HomeBriefCheckAt"
Write-Output "  Home Brief second check: daily at $HomeBriefSecondaryCheckAt"
Write-Output "  Blog preflight: daily at $PreflightAt"
Write-Output "  Blog watchdog: daily at $WatchdogAt"
Write-Output "  Morning catch-up: at logon with a short delay"
