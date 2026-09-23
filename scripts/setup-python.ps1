[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$python = if (Test-Path -LiteralPath $bundledPython) { $bundledPython } else { (Get-Command python).Source }
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $venvPython)) {
    & $python -m venv (Join-Path $projectRoot '.venv')
}

& $venvPython -m pip install --disable-pip-version-check -r (Join-Path $projectRoot 'requirements-dev.txt')

$envFile = Join-Path $projectRoot '.env'
if (-not (Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath (Join-Path $projectRoot '.env.example') -Destination $envFile
}
& $venvPython (Join-Path $projectRoot 'scripts\bootstrap_env.py')

Write-Host "Python environment ready: $venvPython"
