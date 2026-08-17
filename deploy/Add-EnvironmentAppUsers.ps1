#Requires -Version 7.0

<#
.SYNOPSIS
    Adds the PoC service principal as a Dataverse Application User in each environment,
    which is what unlocks the Dataverse rows of the settings matrix.

.DESCRIPTION
    Neither the management-app registration nor a Power Platform RBAC role grants access to
    Dataverse DATA - that needs a per-environment application user. This loops
    `pac admin assign-user` over the environments discovered by main.py.

    Produce the environment list first (no Dataverse access needed for that pass):
        python main.py --skip-dataverse --json out/data.json

.EXAMPLE
    pwsh -File deploy/Add-EnvironmentAppUsers.ps1 -FromReportJson out/data.json -DryRun

.EXAMPLE
    pwsh -File deploy/Add-EnvironmentAppUsers.ps1 -EnvironmentId 'Default-aaaa','bbbb'
#>
[CmdletBinding()]
param(
    # JSON produced by 'python main.py --json out/data.json'; every environment in it is processed.
    [string] $FromReportJson,

    # Explicit environment ids or Dataverse URLs, instead of (or on top of) -FromReportJson.
    [string[]] $EnvironmentId,

    # The .env written by Deploy-AppRegistration.ps1; only PP_CLIENT_ID is read from it.
    [string] $EnvFilePath = (Join-Path (Split-Path -Parent $PSScriptRoot) '.env'),

    # System Administrator is the fast PoC path. For anything beyond a PoC, create a
    # read-only custom role and pass it here instead.
    [string] $Role = 'System Administrator',

    # Print the pac commands that would run, without changing anything.
    [switch] $DryRun
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$PSNativeCommandUseErrorActionPreference = $false

if (-not (Get-Command pac -CommandType Application -ErrorAction SilentlyContinue)) {
    Write-Warning 'Power Platform CLI (pac) not found. Install with:  dotnet tool install --global Microsoft.PowerApps.CLI.Tool'
    exit 1
}

# Client id comes from the .env written by Deploy-AppRegistration.ps1.
if (-not (Test-Path -LiteralPath $EnvFilePath)) {
    Write-Warning "No .env at '$EnvFilePath'. Run Deploy-AppRegistration.ps1 first."
    exit 1
}
$line = Get-Content -LiteralPath $EnvFilePath | Where-Object { $_ -match '^\s*PP_CLIENT_ID\s*=' } | Select-Object -First 1
$appId = if ($line) { ($line -split '=', 2)[1].Trim() } else { $null }
if (-not $appId) { Write-Warning "PP_CLIENT_ID not found in '$EnvFilePath'."; exit 1 }

# Only the Dataverse URL is usable here: an environment without a database has no URL,
# and passing its id to pac would just produce a failure.
$targets = @()
if ($FromReportJson) {
    $data = Get-Content -LiteralPath $FromReportJson -Raw | ConvertFrom-Json
    if (-not ($data.PSObject.Properties.Name -contains 'environments')) {
        Write-Warning "'$FromReportJson' has no 'environments' property - is it the JSON from 'python main.py --json'?"
        exit 1
    }
    $targets = $data.environments | ForEach-Object {
        [pscustomobject]@{ Name = $_.name; Target = $_.url }
    }
}
if ($EnvironmentId) {
    $targets += $EnvironmentId | ForEach-Object { [pscustomobject]@{ Name = $_; Target = $_ } }
}
if (-not $targets) { Write-Warning 'Nothing to do: pass -FromReportJson or -EnvironmentId.'; exit 1 }

if (-not $PSBoundParameters.ContainsKey('Role')) {
    Write-Warning "Using the default role '$Role' - far more privilege than this read-only tool needs. Pass -Role with a least-privilege custom role where you can."
}

Write-Host "App: $appId   Role: $Role   Environments: $($targets.Count)"
Write-Host ''

$ok = 0
$failed = 0
foreach ($t in $targets) {
    if (-not $t.Target) {
        Write-Warning "SKIP  $($t.Name) - no Dataverse URL (environment has no database)."
        continue
    }

    $pacArgs = @('admin', 'assign-user', '--environment', $t.Target, '--user', $appId, '--role', $Role, '--application-user')
    if ($DryRun) {
        Write-Host "DRYRUN pac $($pacArgs -join ' ')"
        continue
    }

    & pac @pacArgs 2>&1 | Out-String -Stream | Where-Object { $_ -match '\S' } | ForEach-Object { Write-Verbose $_ }
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK    $($t.Name)"
        $ok++
    }
    else {
        Write-Warning "FAIL  $($t.Name) (exit $LASTEXITCODE) - re-run with -Verbose for the pac output."
        $failed++
    }
}

if (-not $DryRun) {
    Write-Host ''
    Write-Host "Done: $ok succeeded, $failed failed."
    Write-Host 'Teardown note: deleting the app registration orphans these application users.'
    Write-Host 'Remove them per environment in the Power Platform admin center if you want a clean tenant.'
}
