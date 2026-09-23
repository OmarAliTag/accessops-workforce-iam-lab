[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $python)) {
    throw 'Missing .venv. Run scripts\setup-python.ps1 first.'
}
if (-not (Test-Path -LiteralPath $envPath)) {
    throw 'Missing .env. Run scripts\setup-python.ps1 first.'
}

Get-Content -LiteralPath $envPath | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
    }
}

Write-Host 'Starting AccessOps Portal on http://127.0.0.1:5000.'
Push-Location $projectRoot
try {
    & $python -m portal.app
}
finally {
    Pop-Location
}

