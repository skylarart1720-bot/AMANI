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
# A failed/restarted launcher can leave earlier services outside the latest
# manifest. Only stop framework processes whose command line proves ownership.
$orphans = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and $_.CommandLine.Contains($root) -and (
        $_.CommandLine.Contains('node_modules/next/dist/bin/next') -or
        $_.CommandLine.Contains('node_modules\next\dist\bin\next') -or
        $_.CommandLine.Contains('-m uvicorn src.main:app')
    )
}
foreach ($process in $orphans) {
    & taskkill.exe /PID $process.ProcessId /T /F | Out-Null
}
Write-Host 'Stopped identified AMANI LINE processes.'
