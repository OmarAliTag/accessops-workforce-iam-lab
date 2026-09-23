[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path $env:USERPROFILE '.cache\accessops-runtime')
)

$ErrorActionPreference = 'Stop'
$version = '26.7.4'
$expectedSha256 = 'a286e98b4296d4e75ee88d8527c7cd463b307caa022f088c9f22cffccc741fa1'
$archive = Join-Path $InstallRoot "keycloak-$version.zip"
$keycloakHome = Join-Path $InstallRoot "keycloak-$version"
$download = "https://github.com/keycloak/keycloak/releases/download/$version/keycloak-$version.zip"

New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
if (-not (Test-Path -LiteralPath $archive)) {
    Invoke-WebRequest -Uri $download -OutFile $archive
}

$actualSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant()
if ($actualSha256 -ne $expectedSha256) {
    throw "Keycloak archive checksum mismatch. Expected $expectedSha256, received $actualSha256."
}

if (-not (Test-Path -LiteralPath $keycloakHome)) {
    Expand-Archive -LiteralPath $archive -DestinationPath $InstallRoot
}

& (Join-Path $keycloakHome 'bin\kc.bat') --version
Write-Host "KEYCLOAK_HOME=$keycloakHome"

