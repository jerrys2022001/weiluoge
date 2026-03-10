[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Show-Usage {
    @"
Browser Research wrapper

Usage:
  browser_research.cmd search "query" [--engine bing|google|duckduckgo|baidu] [--session NAME] [--headed|--headless] [--no-snapshot] [--wait-ms 1500]
  browser_research.cmd open <url> [--session NAME] [--headed|--headless] [--no-snapshot] [--wait-ms 1500]
  browser_research.cmd <playwright-cli args...>

Behavior:
  - `search` builds a search URL, opens it in Playwright, and snapshots by default.
  - `open` opens a URL in Playwright and snapshots by default.
  - Any other arguments are passed through directly to `playwright-cli`.
  - If `search` or `open` need multiple Playwright calls and no session is supplied,
    this wrapper auto-generates one and prints it for reuse.
  - On Windows, the wrapper uses skill-local npm and Playwright cache folders to
    avoid permission issues with the default user profile cache.

Examples:
  browser_research.cmd search "Bluetooth Mesh provisioning"
  browser_research.cmd search "iPhone cleanup app" --engine baidu --session cleanup
  browser_research.cmd open https://playwright.dev --session demo --wait-ms 1200
  browser_research.cmd --session demo snapshot
  browser_research.cmd --session demo click e12
"@ | Write-Host
}

function Initialize-ToolEnv {
    $skillRoot = Split-Path -Path $PSScriptRoot -Parent
    $npmCache = Join-Path $skillRoot '.npm-cache'
    $playwrightBrowsers = Join-Path $skillRoot '.playwright-browsers'

    if ([string]::IsNullOrWhiteSpace($env:npm_config_cache) -and [string]::IsNullOrWhiteSpace($env:NPM_CONFIG_CACHE)) {
        New-Item -ItemType Directory -Force $npmCache | Out-Null
        $env:npm_config_cache = $npmCache
        $env:NPM_CONFIG_CACHE = $npmCache
    }

    if ([string]::IsNullOrWhiteSpace($env:PLAYWRIGHT_BROWSERS_PATH)) {
        New-Item -ItemType Directory -Force $playwrightBrowsers | Out-Null
        $env:PLAYWRIGHT_BROWSERS_PATH = $playwrightBrowsers
    }
}

function Get-NpxPath {
    foreach ($candidate in @('npx.cmd', 'npx')) {
        $npxCommand = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($npxCommand) {
            return $npxCommand.Source
        }
    }

    throw "npx is required but was not found on PATH. Install Node.js/npm first, then retry."
}

function Invoke-PlaywrightCli {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    Initialize-ToolEnv
    $npxPath = Get-NpxPath
    & $npxPath '--yes' '--package' '@playwright/cli' 'playwright-cli' @Arguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

function New-SessionName {
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $suffix = [Guid]::NewGuid().ToString('N').Substring(0, 8)
    return "browser-research-$timestamp-$suffix"
}

function Normalize-Url {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url
    )

    if ($Url -match '^[a-zA-Z][a-zA-Z0-9+.-]*://') {
        return $Url
    }

    return "https://$Url"
}

function Get-SearchUrl {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Query,
        [Parameter(Mandatory = $true)]
        [string]$Engine
    )

    $encodedQuery = [Uri]::EscapeDataString($Query)
    switch ($Engine.ToLowerInvariant()) {
        'bing'       { return "https://www.bing.com/search?q=$encodedQuery" }
        'google'     { return "https://www.google.com/search?q=$encodedQuery" }
        'duckduckgo' { return "https://duckduckgo.com/?q=$encodedQuery" }
        'baidu'      { return "https://www.baidu.com/s?wd=$encodedQuery" }
        default      { throw "Unsupported search engine: $Engine. Use one of: bing, google, duckduckgo, baidu." }
    }
}

function Parse-OpenOrSearchArgs {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [Parameter(Mandatory = $true)]
        [string]$Mode
    )

    $target = $null
    $session = if ([string]::IsNullOrWhiteSpace($env:PLAYWRIGHT_CLI_SESSION)) { $null } else { $env:PLAYWRIGHT_CLI_SESSION }
    $engine = 'bing'
    $useHeaded = $true
    $autoSnapshot = $true
    $waitMs = 0

    for ($index = 0; $index -lt $Arguments.Length; $index++) {
        $argument = $Arguments[$index]

        if ($argument -like '--session=*') {
            $session = $argument.Substring('--session='.Length)
            continue
        }

        if ($argument -like '--engine=*') {
            $engine = $argument.Substring('--engine='.Length)
            continue
        }

        if ($argument -like '--wait-ms=*') {
            $waitMs = [int]$argument.Substring('--wait-ms='.Length)
            continue
        }

        switch ($argument) {
            '--session' {
                if ($index + 1 -ge $Arguments.Length) { throw 'Missing value after --session.' }
                $index++
                $session = $Arguments[$index]
                continue
            }
            '--engine' {
                if ($index + 1 -ge $Arguments.Length) { throw 'Missing value after --engine.' }
                $index++
                $engine = $Arguments[$index]
                continue
            }
            '--wait-ms' {
                if ($index + 1 -ge $Arguments.Length) { throw 'Missing value after --wait-ms.' }
                $index++
                $waitMs = [int]$Arguments[$index]
                continue
            }
            '--headed' {
                $useHeaded = $true
                continue
            }
            '--headless' {
                $useHeaded = $false
                continue
            }
            '--no-snapshot' {
                $autoSnapshot = $false
                continue
            }
            default {
                if ($null -eq $target) {
                    $target = $argument
                    continue
                }

                throw "Unexpected extra argument for '$Mode': $argument"
            }
        }
    }

    if ([string]::IsNullOrWhiteSpace($target)) {
        throw "Missing target for '$Mode'."
    }

    return [pscustomobject]@{
        Target       = $target
        Session      = $session
        Engine       = $engine
        UseHeaded    = $useHeaded
        AutoSnapshot = $autoSnapshot
        WaitMs       = $waitMs
    }
}

function Invoke-OpenWorkflow {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter()]
        [string]$Session,
        [Parameter(Mandatory = $true)]
        [bool]$UseHeaded,
        [Parameter(Mandatory = $true)]
        [bool]$AutoSnapshot,
        [Parameter(Mandatory = $true)]
        [int]$WaitMs
    )

    $effectiveSession = if ([string]::IsNullOrWhiteSpace($Session)) { New-SessionName } else { $Session }
    $sessionArgs = @('--session', $effectiveSession)
    $openArgs = @($sessionArgs + @('open', $Url))
    if ($UseHeaded) {
        $openArgs += '--headed'
    }

    Invoke-PlaywrightCli -Arguments $openArgs

    if ($WaitMs -gt 0) {
        Invoke-PlaywrightCli -Arguments ($sessionArgs + @('run-code', "await page.waitForTimeout($WaitMs)"))
    }

    if ($AutoSnapshot) {
        Invoke-PlaywrightCli -Arguments ($sessionArgs + @('snapshot'))
    }

    Write-Host "Session: $effectiveSession"
    Write-Host "URL: $Url"
    if ($AutoSnapshot) {
        Write-Host 'Snapshot: captured'
    }
    else {
        Write-Host 'Snapshot: skipped'
    }
}

if (-not $CliArgs -or $CliArgs.Length -eq 0) {
    Show-Usage
    exit 0
}

$command = $CliArgs[0]
if ($command -in @('help', '--help', '-h', '/?')) {
    Show-Usage
    exit 0
}

$remainingArgs = @()
if ($CliArgs.Length -gt 1) {
    $remainingArgs = $CliArgs[1..($CliArgs.Length - 1)]
}

switch ($command.ToLowerInvariant()) {
    'search' {
        $options = Parse-OpenOrSearchArgs -Arguments $remainingArgs -Mode 'search'
        $url = Get-SearchUrl -Query $options.Target -Engine $options.Engine
        Invoke-OpenWorkflow -Url $url -Session $options.Session -UseHeaded $options.UseHeaded -AutoSnapshot $options.AutoSnapshot -WaitMs $options.WaitMs
        break
    }
    'open' {
        $options = Parse-OpenOrSearchArgs -Arguments $remainingArgs -Mode 'open'
        $url = Normalize-Url -Url $options.Target
        Invoke-OpenWorkflow -Url $url -Session $options.Session -UseHeaded $options.UseHeaded -AutoSnapshot $options.AutoSnapshot -WaitMs $options.WaitMs
        break
    }
    default {
        Invoke-PlaywrightCli -Arguments $CliArgs
        break
    }
}
