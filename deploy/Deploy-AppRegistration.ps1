#Requires -Version 7.0

<#
.SYNOPSIS
    Creates (or tears down) the Entra ID app registration used by the env-settings PoC
    to call Power Platform admin APIs and Dataverse with OAuth2 client credentials (S2S).

.DESCRIPTION
    Uses Azure CLI for all Entra ID work so there is no hard dependency on the
    Microsoft.Graph PowerShell modules. The Power Platform "management application"
    registration step needs Microsoft.PowerApps.Administration.PowerShell; if that module
    is missing the script prints the exact manual command and keeps going.

.EXAMPLE
    pwsh -File deploy/Deploy-AppRegistration.ps1

.EXAMPLE
    pwsh -File deploy/Deploy-AppRegistration.ps1 -Teardown
#>
[CmdletBinding()]
param(
    # Entra ID display name of the app registration to create, reuse or tear down.
    [string] $DisplayName = 'pp-env-settings-poc',

    # Defaults to the tenant of the currently signed-in az account.
    [string] $TenantId,

    # Lifetime of a newly created client secret, in years (Entra allows at most 2).
    [ValidateRange(1, 2)]
    [int] $SecretYears = 1,

    # Where the PP_TENANT_ID / PP_CLIENT_ID / PP_CLIENT_SECRET file is written or read.
    [string] $EnvFilePath = (Join-Path (Split-Path -Parent $PSScriptRoot) '.env'),

    # Management-app registration is ON by default; opt out rather than opt in,
    # because without it the service principal has no tenant-wide admin access.
    [switch] $SkipManagementApp,

    # Install Microsoft.PowerApps.Administration.PowerShell without prompting.
    [switch] $InstallModuleIfMissing,

    # Mint a new client secret even when the .env already holds one for this app.
    [switch] $ForceNewSecret,

    # Delete instead of create: unregisters the management app, then removes the service
    # principal, the app registration and the matching .env. Nothing else is created.
    [switch] $Teardown,

    # Echo the client secret to the console at the end of a create run (see the warning
    # it prints - the value lands in transcripts and CI logs).
    [switch] $ShowSecret
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# PS 7.4+ turns a non-zero native exit code into a terminating error. We want to decide
# per call (teardown must tolerate "already gone"), so handle $LASTEXITCODE explicitly.
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = Split-Path -Parent $PSScriptRoot

# Well-known first-party resource app IDs.
$DataverseResourceAppId  = '00000007-0000-0000-c000-000000000000'  # "Dynamics CRM"
$BapAdminAppsUri         = 'https://api.bap.microsoft.com/providers/Microsoft.BusinessAppPlatform/adminApplications'
$BapApiVersion           = '2020-10-01'
$ManagementModule        = 'Microsoft.PowerApps.Administration.PowerShell'

# Set by Invoke-Az. Needed because some az commands (admin-consent) print nothing on
# success, so a null return value alone cannot tell success from failure.
$script:LastAzExitCode = 0

#region helpers ---------------------------------------------------------------

# Single choke point for az: captures stdout, swallows the noisy stderr banner,
# and lets the caller decide whether a non-zero exit is fatal.
function Invoke-Az {
    param(
        [Parameter(Mandatory)][string[]] $Arguments,
        [switch] $Tolerant
    )

    $stdout = & az @Arguments 2>$null
    $exit = $LASTEXITCODE
    $script:LastAzExitCode = $exit

    if ($exit -ne 0 -and -not $Tolerant) {
        throw "az $($Arguments -join ' ') failed with exit code $exit."
    }

    if ($exit -ne 0) { return $null }
    if (-not $stdout) { return $null }

    $text = ($stdout -join [Environment]::NewLine).Trim()
    if (-not $text) { return $null }

    try { return $text | ConvertFrom-Json } catch { return $text }
}

function Test-AzReady {
    if (-not (Get-Command az -CommandType Application -ErrorAction SilentlyContinue)) {
        Write-Warning 'Azure CLI (az) was not found on PATH. Install it from https://aka.ms/installazurecli.'
        exit 1
    }

    $account = Invoke-Az -Arguments @('account', 'show', '-o', 'json') -Tolerant
    if (-not $account) {
        Write-Warning 'Not signed in to Azure CLI. Run:  az login --allow-no-subscriptions'
        exit 1
    }

    return $account
}

# Resolve a delegated scope GUID at runtime instead of hardcoding it, so the script
# survives any future re-issue of the well-known permission IDs.
function Resolve-DelegatedScopeId {
    param(
        [Parameter(Mandatory)][string] $ResourceAppId,
        [Parameter(Mandatory)][string] $ScopeName
    )

    $id = Invoke-Az -Tolerant -Arguments @(
        'ad', 'sp', 'show', '--id', $ResourceAppId,
        '--query', "oauth2PermissionScopes[?value=='$ScopeName'].id | [0]",
        '-o', 'tsv'
    )

    if ($id) { return [string]$id }

    Write-Warning "Could not resolve '$ScopeName' on resource $ResourceAppId (is the service principal present in this tenant?)."
    return $null
}

function Get-ExistingApp {
    param([Parameter(Mandatory)][string] $Name)

    $apps = Invoke-Az -Tolerant -Arguments @(
        'ad', 'app', 'list', '--display-name', $Name, '-o', 'json'
    )

    if (-not $apps) { return $null }
    return @($apps)[0]
}

function Test-ManagementModule {
    param([switch] $InstallIfMissing)

    if (Get-Module -ListAvailable -Name $ManagementModule) { return $true }

    if (-not $InstallIfMissing) {
        $answer = Read-Host "Module '$ManagementModule' is not installed. Install it now for the current user? [y/N]"
        if ($answer -notmatch '^(y|yes)$') { return $false }
    }

    try {
        Write-Host "Installing $ManagementModule (CurrentUser scope)..."
        Install-Module -Name $ManagementModule -Scope CurrentUser -Force -AllowClobber
        return $true
    }
    catch {
        Write-Warning "Install-Module failed: $($_.Exception.Message)"
        return $false
    }
}

function Write-ManualManagementAppHelp {
    param([Parameter(Mandatory)][string] $AppId, [Parameter(Mandatory)][string] $Tenant)

    Write-Warning 'Register the management application manually with EITHER of the following:'
    Write-Host ''
    Write-Host '  # PowerShell (must be run by a tenant admin, interactive sign-in)'
    Write-Host "  Install-Module $ManagementModule -Scope CurrentUser"
    Write-Host "  Add-PowerAppsAccount -Endpoint prod -TenantID $Tenant"
    Write-Host "  New-PowerAppManagementApp -ApplicationId $AppId"
    Write-Host ''
    Write-Host '  # REST (bearer token from an interactive admin sign-in, NOT the service principal)'
    Write-Host "  PUT $BapAdminAppsUri/$AppId`?api-version=$BapApiVersion"
    Write-Host ''
}

#endregion helpers ------------------------------------------------------------

#region teardown --------------------------------------------------------------

function Invoke-Teardown {
    param([Parameter(Mandatory)][string] $Tenant)

    Write-Host "=== Teardown: $DisplayName ===" -ForegroundColor Yellow

    $app = Get-ExistingApp -Name $DisplayName
    if (-not $app) {
        Write-Host "SKIP  app registration '$DisplayName' - not found."
        $appId = $null
    }
    else {
        $appId = [string]$app.appId
        Write-Host "FOUND app registration '$DisplayName' (appId $appId)."
    }

    # Each step is isolated so one failure never strands the remaining cleanup.
    if ($appId -and -not $SkipManagementApp) {
        $signedIn = $false
        try {
            if (Get-Module -ListAvailable -Name $ManagementModule) {
                Import-Module $ManagementModule -ErrorAction Stop
                # Remove-PowerAppManagementApp does not sign in on its own: without this the
                # call always throws and the app stays registered tenant-wide.
                Write-Host 'Signing in to Power Platform (interactive, tenant admin required)...'
                Add-PowerAppsAccount -Endpoint prod -TenantID $Tenant
                $signedIn = $true
                Remove-PowerAppManagementApp -ApplicationId $appId
                Write-Host 'REMOVED management application registration.'
            }
            else {
                Write-Warning "SKIP  management app - module '$ManagementModule' not installed."
                Write-Warning "      Run manually: Remove-PowerAppManagementApp -ApplicationId $appId"
                Write-Warning "      Or REST: DELETE $BapAdminAppsUri/$appId`?api-version=$BapApiVersion"
            }
        }
        catch {
            if (-not $signedIn) {
                Write-Warning "Power Platform sign-in failed or was cancelled: $($_.Exception.Message)"
            }
            else {
                Write-Warning "Management app removal failed: $($_.Exception.Message)"
            }
            Write-Warning '      The app is probably STILL a tenant-wide management application. Retry with:'
            Write-Warning "      Add-PowerAppsAccount -Endpoint prod -TenantID $Tenant"
            Write-Warning "      Remove-PowerAppManagementApp -ApplicationId $appId"
        }
    }

    $appDeleted = $false
    if ($appId) {
        try {
            $sp = Invoke-Az -Tolerant -Arguments @('ad', 'sp', 'show', '--id', $appId, '-o', 'json')
            if ($sp) {
                $null = Invoke-Az -Tolerant -Arguments @('ad', 'sp', 'delete', '--id', $appId)
                Write-Host 'REMOVED service principal.'
            }
            else {
                Write-Host 'SKIP  service principal - not found.'
            }
        }
        catch {
            Write-Warning "Service principal deletion failed: $($_.Exception.Message)"
        }

        try {
            $null = Invoke-Az -Tolerant -Arguments @('ad', 'app', 'delete', '--id', $appId)
            if ($script:LastAzExitCode -eq 0) {
                $appDeleted = $true
                Write-Host 'REMOVED app registration.'
            }
            else {
                Write-Warning "App registration deletion failed (az exit $($script:LastAzExitCode))."
            }
        }
        catch {
            Write-Warning "App registration deletion failed: $($_.Exception.Message)"
        }
    }

    # Only delete the .env we recognise, so a hand-edited file for another app survives.
    try {
        if (-not (Test-Path -LiteralPath $EnvFilePath)) {
            Write-Host "SKIP  .env - '$EnvFilePath' does not exist."
        }
        else {
            $line = Get-Content -LiteralPath $EnvFilePath | Where-Object { $_ -match '^\s*PP_CLIENT_ID\s*=' } | Select-Object -First 1
            $fileAppId = if ($line) { ($line -split '=', 2)[1].Trim() } else { $null }

            if ($appId -and $fileAppId -eq $appId) {
                # The secrets in this file are still live if the app survived, and this is
                # the only local record of them.
                if (-not $appDeleted) {
                    Write-Warning "SKIP  .env - the app registration was NOT deleted, so its secrets are still valid."
                    Write-Warning "      Keeping '$EnvFilePath' as the only local record. Delete it once the app is gone."
                }
                else {
                    Remove-Item -LiteralPath $EnvFilePath -Force
                    Write-Host "REMOVED $EnvFilePath."
                }
            }
            elseif (-not $appId -and $fileAppId) {
                Write-Warning "SKIP  .env - app registration not found, cannot confirm PP_CLIENT_ID=$fileAppId belongs to it."
            }
            elseif (-not $fileAppId) {
                Write-Warning "SKIP  .env - no PP_CLIENT_ID line in '$EnvFilePath', cannot confirm it belongs to this app."
            }
            else {
                Write-Warning "SKIP  .env - PP_CLIENT_ID=$fileAppId does not match $appId."
            }
        }
    }
    catch {
        Write-Warning ".env cleanup failed: $($_.Exception.Message)"
    }

    Write-Host ''
    Write-Host "Teardown finished for tenant $Tenant." -ForegroundColor Yellow
    Write-Host 'Left behind on purpose:'
    Write-Host '  * Dataverse application users created by Add-EnvironmentAppUsers.ps1 - they are'
    Write-Host '    per environment and must be removed in the Power Platform admin center'
    Write-Host '    (Environment > Settings > Users + permissions > Application users).'
    Write-Host '  * The app registration is SOFT-deleted: Entra keeps it recoverable for 30 days.'
    Write-Host "    List it with:  az ad app list --show-deleted --display-name `"$DisplayName`""
}

#endregion teardown -----------------------------------------------------------

#region main ------------------------------------------------------------------

$account = Test-AzReady
if (-not $TenantId) { $TenantId = [string]$account.tenantId }
Write-Host "Tenant: $TenantId"

if ($Teardown) {
    Invoke-Teardown -Tenant $TenantId
    return
}

# --- 1. App registration (idempotent) ----------------------------------------
$app = Get-ExistingApp -Name $DisplayName
if ($app) {
    $appId = [string]$app.appId
    Write-Host "Reusing existing app registration '$DisplayName' (appId $appId)."
}
else {
    Write-Host "Creating single-tenant app registration '$DisplayName'..."
    $app = Invoke-Az -Arguments @(
        'ad', 'app', 'create',
        '--display-name', $DisplayName,
        '--sign-in-audience', 'AzureADMyOrg',
        '-o', 'json'
    )
    $appId = [string]$app.appId
    Write-Host "Created appId $appId."
}

# --- 2. Service principal (idempotent) ---------------------------------------
$sp = Invoke-Az -Tolerant -Arguments @('ad', 'sp', 'show', '--id', $appId, '-o', 'json')
if ($sp) {
    Write-Host 'Service principal already exists.'
}
else {
    Write-Host 'Creating service principal...'
    $null = Invoke-Az -Arguments @('ad', 'sp', 'create', '--id', $appId, '-o', 'json')
}

# --- 3. API permissions -------------------------------------------------------
#
# Dataverse ("Dynamics CRM") user_impersonation is the only permission this PoC adds.
# It is what the Power Platform ALM / GitHub Actions guidance prescribes for an S2S app.
#
# Deliberately NOT added:
#  * Power Platform API (8578e004-...) - it publishes DELEGATED scopes only. Microsoft's
#    guidance is explicitly "for service principal identities, don't use application
#    permissions"; a client-credentials token for https://api.powerplatform.com/.default
#    works off the management-app registration (step 5) or an RBAC role assignment, so
#    adding delegated scopes here would be pure noise.
#  * PowerApps Runtime Service / PowerApps-Advisor - only needed for pac CLI solution
#    checker / build-tools scenarios, not for admin + Dataverse reads.
#
# Reminder: app-only access to Dataverse DATA still requires an Application User plus a
# security role in each target environment (Power Platform admin center > Environment > S2S).
$scopeId = Resolve-DelegatedScopeId -ResourceAppId $DataverseResourceAppId -ScopeName 'user_impersonation'
if ($scopeId) {
    Write-Host 'Adding Dataverse user_impersonation (delegated)...'
    $null = Invoke-Az -Tolerant -Arguments @(
        'ad', 'app', 'permission', 'add',
        '--id', $appId,
        '--api', $DataverseResourceAppId,
        '--api-permissions', "$scopeId=Scope"
    )
}
else {
    Write-Warning "Skipped Dataverse permission - could not resolve the scope on $DataverseResourceAppId."
}

# Consent needs Privileged Role Administrator or Global Administrator; degrade gracefully.
Write-Host 'Granting admin consent...'
$null = Invoke-Az -Tolerant -Arguments @('ad', 'app', 'permission', 'admin-consent', '--id', $appId)
if ($script:LastAzExitCode -ne 0) {
    Write-Warning 'Admin consent failed (insufficient privileges?). Have a tenant admin consent here:'
    Write-Warning "  https://login.microsoftonline.com/$TenantId/adminconsent?client_id=$appId"
}
else {
    Write-Host 'Admin consent granted.'
}

# --- 4. Client secret ---------------------------------------------------------
# Every 'credential reset --append' mints another live secret, but only the newest one
# reaches .env - the older ones stay valid and untracked. So reuse the secret already on
# disk unless it belongs to a different app, is missing, or -ForceNewSecret is passed.
$reusedSecret = $false
$clientSecret = $null

if (-not $ForceNewSecret -and (Test-Path -LiteralPath $EnvFilePath)) {
    $envText    = @(Get-Content -LiteralPath $EnvFilePath)
    $idLine     = $envText | Where-Object { $_ -match '^\s*PP_CLIENT_ID\s*=' }     | Select-Object -First 1
    $secretLine = $envText | Where-Object { $_ -match '^\s*PP_CLIENT_SECRET\s*=' } | Select-Object -First 1
    $fileAppId  = if ($idLine) { ($idLine -split '=', 2)[1].Trim() } else { '' }
    $fileSecret = if ($secretLine) { ($secretLine -split '=', 2)[1].Trim() } else { '' }

    if ($fileAppId -eq $appId -and $fileSecret) {
        $clientSecret = $fileSecret
        $reusedSecret = $true
        Write-Host "Reusing the client secret already in $EnvFilePath (pass -ForceNewSecret to mint another)."
    }
}

if (-not $reusedSecret) {
    Write-Host "Creating client secret valid for $SecretYears year(s)..."
    $cred = Invoke-Az -Arguments @(
        'ad', 'app', 'credential', 'reset',
        '--id', $appId,
        '--years', "$SecretYears",
        '--append',
        '--display-name', "poc-$(Get-Date -Format 'yyyyMMdd-HHmm')",
        '-o', 'json'
    )
    $clientSecret = [string]$cred.password
    if (-not $clientSecret) { throw 'Azure CLI did not return a client secret.' }
}

# --- 5. Power Platform management application ---------------------------------
$managementAppRegistered = $false
if ($SkipManagementApp) {
    Write-Host 'Skipping management application registration (-SkipManagementApp).'
}
else {
    # A service principal cannot register itself - this needs an interactive tenant admin.
    if (Test-ManagementModule -InstallIfMissing:$InstallModuleIfMissing) {
        try {
            Import-Module $ManagementModule -ErrorAction Stop
            Write-Host 'Signing in to Power Platform (interactive, tenant admin required)...'
            Add-PowerAppsAccount -Endpoint prod -TenantID $TenantId
            New-PowerAppManagementApp -ApplicationId $appId | Out-Null
            $managementAppRegistered = $true
            Write-Host 'Registered as a Power Platform management application.'
        }
        catch {
            Write-Warning "Management app registration failed: $($_.Exception.Message)"
            Write-ManualManagementAppHelp -AppId $appId -Tenant $TenantId
        }
    }
    else {
        Write-Warning "Module '$ManagementModule' unavailable."
        Write-ManualManagementAppHelp -AppId $appId -Tenant $TenantId
    }
}

# --- 6. .env ------------------------------------------------------------------
$envLines = @(
    "PP_TENANT_ID=$TenantId"
    "PP_CLIENT_ID=$appId"
    "PP_CLIENT_SECRET=$clientSecret"
)
# UTF8NoBOM: a BOM breaks naive KEY=value parsers (python-dotenv et al).
Set-Content -LiteralPath $EnvFilePath -Value $envLines -Encoding utf8NoBOM
Write-Host "Wrote $EnvFilePath - it contains the live client secret (not echoed here)."

# The file inherits the directory DACL, which typically lets every local user read it.
try {
    $acl = Get-Acl -LiteralPath $EnvFilePath
    $acl.SetAccessRuleProtection($true, $false)   # stop inheriting, drop the inherited ACEs
    foreach ($identity in @([System.Security.Principal.WindowsIdentity]::GetCurrent().Name, 'NT AUTHORITY\SYSTEM')) {
        $acl.AddAccessRule(
            [System.Security.AccessControl.FileSystemAccessRule]::new($identity, 'FullControl', 'Allow'))
    }
    Set-Acl -LiteralPath $EnvFilePath -AclObject $acl
    Write-Host '  Permissions restricted to you and SYSTEM.'
}
catch {
    Write-Warning "Could not restrict permissions on '$EnvFilePath': $($_.Exception.Message)"
    Write-Warning '  The file holds a live client secret - check who can read it.'
}

# --- 7. .gitignore ------------------------------------------------------------
# Reports are written to out/, which is ignored: they carry tenant configuration data
# (environment names, URLs, DLP and security settings) and must stay out of git.
$gitignorePath = Join-Path $RepoRoot '.gitignore'
$wanted = @('.env', '.env.*', 'out/', 'report.html', 'data.json', '__pycache__/', '*.pyc')
$existing = if (Test-Path -LiteralPath $gitignorePath) { @(Get-Content -LiteralPath $gitignorePath) } else { @() }
$missing = $wanted | Where-Object { $_ -notin $existing }

if ($missing) {
    # Without a trailing newline the first entry would be glued onto the last line.
    $raw = if (Test-Path -LiteralPath $gitignorePath) { Get-Content -LiteralPath $gitignorePath -Raw } else { '' }
    if ($raw -and $raw -notmatch '\r?\n$') { Add-Content -LiteralPath $gitignorePath -Value '' }

    Add-Content -LiteralPath $gitignorePath -Value $missing
    Write-Host ".gitignore updated with: $($missing -join ', ')"
}
else {
    Write-Host '.gitignore already up to date.'
}

# --- 8. Summary ---------------------------------------------------------------
Write-Host ''
Write-Host '=== Created ===' -ForegroundColor Green
Write-Host "  Display name : $DisplayName"
Write-Host "  Tenant ID    : $TenantId"
Write-Host "  Client ID    : $appId"
Write-Host "  Secret       : $(if ($reusedSecret) { "reused from $EnvFilePath" } else { "new, written to $EnvFilePath (expires in $SecretYears year(s))" })"
Write-Host "  Permissions  : Dataverse user_impersonation (delegated)"
Write-Host "  Mgmt app     : $(if ($managementAppRegistered) { 'registered' } elseif ($SkipManagementApp) { 'skipped' } else { 'NOT registered - see warnings above' })"

if ($ShowSecret) {
    Write-Warning 'Echoing the client secret (-ShowSecret): it is now in your console history, any PowerShell transcript and any CI log.'
    Write-Warning "  PP_CLIENT_SECRET=$clientSecret"
}

Write-Host ''
Write-Host 'Remaining manual step: add this app as an Application User with a security role'
Write-Host 'in each Dataverse environment (Power Platform admin center > Environments > S2S).'
Write-Host ''
Write-Host 'Teardown:' -ForegroundColor Cyan
Write-Host "  pwsh -File `"$PSCommandPath`" -DisplayName `"$DisplayName`" -Teardown"

#endregion main ---------------------------------------------------------------
