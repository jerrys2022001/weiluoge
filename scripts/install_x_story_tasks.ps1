param(
  [string]$PythonExe = "python",
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$LogRoot = "D:\Operation Log",
  [int]$MinPosts = 6,
  [int]$MaxPosts = 12,
  [string]$DayStart = "08:00",
  [string]$DayEnd = "23:30",
  [ValidateSet("classic", "velocai-mix")]
  [string]$ContentMode = "classic",
  [ValidateSet("playwright-first", "api-first", "playwright", "api")]
  [string]$PostMode = "playwright-first",
  [string]$UpdateTopicsFile = "",
  [string[]]$WindowSpec = @(),
  [string]$PlaywrightChromePath = "",
  [string]$PlaywrightUserDataDir = "",
  [string]$PlaywrightProfileDirectory = "",
  [string]$PlaywrightProxyServer = "",
  [int]$PlaywrightLoginWaitSeconds = 0,
  [int]$WorkerEveryMinutes = 60,
  [string]$TaskPrefix = "WeiLuoGe-XStory"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Parse-HHmm {
  param([string]$Value)
  return [datetime]::ParseExact($Value, 'HH:mm', [System.Globalization.CultureInfo]::InvariantCulture)
}

function Get-WindowStartTimes {
  param(
    [string[]]$Specs,
    [string]$FallbackDayStart
  )

  $starts = @()
  if ($Specs -and $Specs.Count -gt 0) {
    foreach ($spec in $Specs) {
      if (-not $spec) { continue }
      $parts = $spec -split '\|'
      if ($parts.Count -ne 5) {
        throw "Invalid WindowSpec '$spec'. Expected format: name|HH:MM|HH:MM|min_posts|max_posts"
      }
      $starts += $parts[1].Trim()
    }
  } else {
    $starts += $FallbackDayStart
  }
  return $starts
}

function Get-WindowSpecs {
  param(
    [string[]]$Specs,
    [string]$FallbackDayStart,
    [string]$FallbackDayEnd,
    [int]$FallbackMinPosts,
    [int]$FallbackMaxPosts
  )

  $windows = @()
  if ($Specs -and $Specs.Count -gt 0) {
    foreach ($spec in $Specs) {
      if (-not $spec) { continue }
      $parts = $spec -split '\|'
      if ($parts.Count -ne 5) {
        throw "Invalid WindowSpec '$spec'. Expected format: name|HH:MM|HH:MM|min_posts|max_posts"
      }
      $windows += [pscustomobject]@{
        Name = $parts[0].Trim()
        DayStart = $parts[1].Trim()
        DayEnd = $parts[2].Trim()
        MinPosts = [int]$parts[3].Trim()
        MaxPosts = [int]$parts[4].Trim()
      }
    }
  } else {
    $windows += [pscustomobject]@{
      Name = "primary"
      DayStart = $FallbackDayStart
      DayEnd = $FallbackDayEnd
      MinPosts = $FallbackMinPosts
      MaxPosts = $FallbackMaxPosts
    }
  }

  return $windows
}

function Convert-TimeSpanToTaskDuration {
  param([timespan]$TimeSpan)

  $parts = @("PT")
  if ($TimeSpan.Hours -gt 0) {
    $parts += "$($TimeSpan.Hours)H"
  }
  if ($TimeSpan.Minutes -gt 0) {
    $parts += "$($TimeSpan.Minutes)M"
  }
  if ($TimeSpan.Seconds -gt 0 -or $parts.Count -eq 1) {
    $parts += "$($TimeSpan.Seconds)S"
  }
  return ($parts -join "")
}

function New-CalendarTriggerXml {
  param(
    [string]$DayStart,
    [string]$DayEnd,
    [int]$RepeatMinutes
  )

  $start = Parse-HHmm -Value $DayStart
  $end = Parse-HHmm -Value $DayEnd
  $duration = [datetime]::Today.Add($end.TimeOfDay) - [datetime]::Today.Add($start.TimeOfDay)
  if ($duration.TotalMinutes -le 0) {
    throw "Window end must be later than start: $DayStart -> $DayEnd"
  }
  $startBoundary = (Get-Date -Hour $start.Hour -Minute $start.Minute -Second 0).ToString("yyyy-MM-ddTHH:mm:ss")
  $durationText = Convert-TimeSpanToTaskDuration -TimeSpan $duration

  return @"
    <CalendarTrigger>
      <StartBoundary>$startBoundary</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
      <Repetition>
        <Interval>PT${RepeatMinutes}M</Interval>
        <Duration>$durationText</Duration>
        <StopAtDurationEnd>true</StopAtDurationEnd>
      </Repetition>
    </CalendarTrigger>
"@
}

function Get-NextTriggerStart {
  param(
    [string[]]$WindowStarts,
    [int]$LeadMinutes = 5
  )

  $now = Get-Date
  $candidates = @()
  foreach ($windowStart in $WindowStarts) {
    $parsed = Parse-HHmm -Value $windowStart
    $todayStart = Get-Date -Hour $parsed.Hour -Minute $parsed.Minute -Second 0
    $preStart = $todayStart.AddMinutes(-1 * $LeadMinutes)
    if ($preStart -gt $now) {
      $candidates += $preStart
    } else {
      $candidates += $preStart.AddDays(1)
    }
  }

  if (-not $candidates -or $candidates.Count -eq 0) {
    return (Get-Date).AddMinutes(1)
  }

  return ($candidates | Sort-Object | Select-Object -First 1)
}

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

$Windows = Get-WindowSpecs -Specs $WindowSpec -FallbackDayStart $DayStart -FallbackDayEnd $DayEnd -FallbackMinPosts $MinPosts -FallbackMaxPosts $MaxPosts
$WindowStarts = Get-WindowStartTimes -Specs $WindowSpec -FallbackDayStart $DayStart
$TriggerStart = Get-NextTriggerStart -WindowStarts $WindowStarts -LeadMinutes 5

$CommonArgs = "--log-root `"$LogRoot`" --min-posts $MinPosts --max-posts $MaxPosts --day-start $DayStart --day-end $DayEnd --content-mode $ContentMode --post-mode $PostMode"
if ($UpdateTopicsFile) {
  $CommonArgs += " --update-topics-file `"$UpdateTopicsFile`""
}
foreach ($Spec in $WindowSpec) {
  if ($Spec) {
    $CommonArgs += " --window-spec `"$Spec`""
  }
}
if ($PlaywrightChromePath) {
  $CommonArgs += " --playwright-chrome-path `"$PlaywrightChromePath`""
}
if ($PlaywrightUserDataDir) {
  $CommonArgs += " --playwright-user-data-dir `"$PlaywrightUserDataDir`""
}
if ($PlaywrightProfileDirectory) {
  $CommonArgs += " --playwright-profile-directory `"$PlaywrightProfileDirectory`""
}
if ($PlaywrightProxyServer) {
  $CommonArgs += " --playwright-proxy-server `"$PlaywrightProxyServer`""
}
if ($PlaywrightLoginWaitSeconds -gt 0) {
  $CommonArgs += " --playwright-login-wait-seconds $PlaywrightLoginWaitSeconds"
}
$RunArgs = "`"$ScriptPath`" run $CommonArgs"

if (Get-ScheduledTask -TaskName $LegacyWorkerTaskName -ErrorAction SilentlyContinue) {
  Unregister-ScheduledTask -TaskName $LegacyWorkerTaskName -Confirm:$false | Out-Null
}

$PrincipalSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$TriggerXml = ($Windows | ForEach-Object {
  New-CalendarTriggerXml -DayStart $_.DayStart -DayEnd $_.DayEnd -RepeatMinutes $WorkerEveryMinutes
}) -join "`n"

$EscapedCommand = [System.Security.SecurityElement]::Escape($PythonCommand)
$EscapedArgs = [System.Security.SecurityElement]::Escape($RunArgs)

$TaskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <URI>\$MergedTaskName</URI>
  </RegistrationInfo>
  <Principals>
    <Principal id="Author">
      <UserId>$PrincipalSid</UserId>
      <LogonType>InteractiveToken</LogonType>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <WakeToRun>true</WakeToRun>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <IdleSettings>
      <Duration>PT10M</Duration>
      <WaitTimeout>PT1H</WaitTimeout>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
  </Settings>
  <Triggers>
$TriggerXml
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>$EscapedCommand</Command>
      <Arguments>$EscapedArgs</Arguments>
    </Exec>
  </Actions>
</Task>
"@

$TempXml = Join-Path ([System.IO.Path]::GetTempPath()) "$MergedTaskName.xml"
$TaskXml | Out-File -FilePath $TempXml -Encoding Unicode -Force
& schtasks.exe /Create /TN $MergedTaskName /XML $TempXml /F | Out-Null
Remove-Item $TempXml -Force -ErrorAction SilentlyContinue

Write-Output "Installed task:"
Write-Output " - $MergedTaskName"
Write-Output ""
Write-Output "Task command:"
Write-Output " - $PythonCommand $RunArgs"
Write-Output ""
Write-Output "First trigger start:"
Write-Output " - $TriggerStart"
Write-Output ""
Write-Output "Logs and plans are stored under: $LogRoot\TwitterStoryBot"
