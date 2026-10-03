param([switch]$Dev)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if ($Dev) { & $python (Join-Path $PSScriptRoot 'run_local.py') --dev }
else { & $python (Join-Path $PSScriptRoot 'run_local.py') }
exit $LASTEXITCODE
