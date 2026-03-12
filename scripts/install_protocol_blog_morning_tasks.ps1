param(
  [string]$PythonExe = "py",
  [string]$PythonArgs = "-3 -B",
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$WindowStart = "08:46",
  [string]$WindowEnd = "08:50",
  [int]$PostsPerDay = 3,
  [string]$TaskNamePrefix = "WeiLuoGe-Bluetooth-Protocol-Blog-Morning",
  [bool]$ReplaceExisting = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Parse-HHMM([string]$value) {
  if ($value -notmatch '^(?<h>\d{1,2}):(?<m>\d{2})$') {
    throw "Invalid time format (expected HH:MM): $value"
  }
  $h = [int]$Matches['h']
  $m = [int]$Matches['m']
  if ($h -lt 0 -or $h -gt 23 -or $m -lt 0 -or $m -gt 59) {
    throw "Invalid time value: $value"
  }
  return ($h * 60 + $m)
}

function Format-HHMM([int]$minutes) {
  $h = [int][math]::Floor($minutes / 60)
  $m = [int]($minutes - ($h * 60))
  return ("{0:D2}:{1:D2}" -f $h, $m)
}

$ScriptPath = Join-Path $RepoRoot "scripts\\blog_protocol_daily_scheduler.py"
if (-not (Test-Path $ScriptPath)) {
  throw "Missing script: $ScriptPath"
}

$PythonCommand = (Get-Command $PythonExe -ErrorAction Stop).Source
if (-not $PythonCommand) {
  throw "Cannot resolve Python command: $PythonExe"
}

if ($PostsPerDay -lt 1) {
  throw "PostsPerDay must be >= 1"
}

$startMin = Parse-HHMM $WindowStart
$endMin = Parse-HHMM $WindowEnd
if ($endMin -le $startMin) {
  throw "WindowEnd must be after WindowStart: $WindowStart -> $WindowEnd"
}
$duration = $endMin - $startMin
if ($PostsPerDay -eq 1) {
  $publishMinutes = @($startMin)
}
else {
  if ($duration -lt ($PostsPerDay - 1)) {
    throw "Window too small for PostsPerDay. durationMinutes=$duration posts=$PostsPerDay"
  }
  $publishMinutes = for ($i = 0; $i -lt $PostsPerDay; $i++) {
    [int][math]::Round($startMin + (($duration * $i) / ($PostsPerDay - 1)))
  }
}

if ($ReplaceExisting) {
  $prefixPattern = "$TaskNamePrefix-*"
  $existing = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -like $prefixPattern }
  foreach ($task in $existing) {
    Unregister-ScheduledTask -TaskName $task.TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
  }
}

for ($i = 0; $i -lt $publishMinutes.Count; $i++) {
  $publishAt = Format-HHMM $publishMinutes[$i]
  $taskName = "$TaskNamePrefix-$($i + 1)"

  $Args = "$PythonArgs `"$ScriptPath`" run --repo-root `"$RepoRoot`" --angle-offset $i --git-commit --git-push"
  $Action = New-ScheduledTaskAction -Execute $PythonCommand -Argument $Args
  $Trigger = New-ScheduledTaskTrigger -Daily -At $publishAt

  Register-ScheduledTask -TaskName $taskName -Action $Action -Trigger $Trigger -Force | Out-Null

  Write-Output "Installed task: $taskName"
  Write-Output "Schedule: daily at $publishAt (angle-offset=$i)"
  Write-Output "Command: $PythonCommand $Args"
}
