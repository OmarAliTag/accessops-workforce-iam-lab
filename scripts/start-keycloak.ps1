[CmdletBinding()]
param(
    [string]$KeycloakHome = (Join-Path $env:USERPROFILE '.cache\accessops-runtime\keycloak-26.7.4')
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'

if (-not (Test-Path -LiteralPath $envPath)) {
    throw 'Missing .env. Run scripts\setup-python.ps1, then replace its placeholder values.'
}
if (-not (Test-Path -LiteralPath (Join-Path $KeycloakHome 'bin\kc.bat'))) {
    throw 'Keycloak is missing. Run scripts\install-keycloak.ps1 first.'
}

Get-Content -LiteralPath $envPath | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
    }
}

$required = @(
    'KEYCLOAK_BOOTSTRAP_ADMIN',
    'KEYCLOAK_BOOTSTRAP_PASSWORD',
    'OIDC_CLIENT_SECRET',
    'KEYCLOAK_AUTOMATION_CLIENT_SECRET'
)
foreach ($name in $required) {
    $value = [Environment]::GetEnvironmentVariable($name, 'Process')
    if ([string]::IsNullOrWhiteSpace($value) -or $value -match '^(replace-|Replace-)') {
        throw "Replace the $name placeholder in .env before starting Keycloak."
    }
}

$env:KC_BOOTSTRAP_ADMIN_USERNAME = $env:KEYCLOAK_BOOTSTRAP_ADMIN
$env:KC_BOOTSTRAP_ADMIN_PASSWORD = $env:KEYCLOAK_BOOTSTRAP_PASSWORD
$env:ACCESSOPS_PORTAL_CLIENT_SECRET = $env:OIDC_CLIENT_SECRET
$env:ACCESSOPS_AUTOMATION_CLIENT_SECRET = $env:KEYCLOAK_AUTOMATION_CLIENT_SECRET

$importDirectory = Join-Path $KeycloakHome 'data\import'
New-Item -ItemType Directory -Path $importDirectory -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot 'keycloak\accessops-realm.json') -Destination (Join-Path $importDirectory 'accessops-realm.json') -Force

Write-Host 'Starting Keycloak on http://127.0.0.1:8080 (development mode, local lab only).'
& (Join-Path $KeycloakHome 'bin\kc.bat') start-dev --http-host=127.0.0.1 --http-port=8080 --import-realm

