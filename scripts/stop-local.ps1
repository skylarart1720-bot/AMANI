$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$manifest = Join-Path $root '.runtime\services.json'
if (-not (Test-Path -LiteralPath $manifest)) { Write-Host 'No managed services recorded.'; exit 0 }
$services = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
foreach ($service in $services) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($service.pid)"
    if ($process -and $process.CommandLine -and $process.CommandLine.Contains($root)) {
        & taskkill.exe /PID $service.pid /T /F | Out-Null
    } elseif ($process) {
        Write-Warning "Could not establish ownership of process $($service.pid); left it running."
    }
}
Write-Host 'Stopped identified AMANI LINE processes.'
