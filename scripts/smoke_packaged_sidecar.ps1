# Smoke-test the *packaged* Windows Python sidecar, not the source interpreter.
# Uses only disposable synthetic data and a short-lived random bearer token.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SidecarPath,
    [Parameter(Mandatory = $true)][string]$ReportPath
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$binary = (Resolve-Path -LiteralPath $SidecarPath).Path
if (-not $binary.EndsWith('.exe', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Expected the packaged Windows sidecar .exe'
}
$work = Join-Path $env:RUNNER_TEMP ('yijing-sidecar-smoke-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work -Force | Out-Null
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$listener.Start()
$port = $listener.LocalEndpoint.Port
$listener.Stop()
$token = [Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLowerInvariant()
$env:YIJING_SERVER_PORT = [string]$port
$env:YIJING_API_TOKEN = $token
$env:YIJING_DB_PATH = Join-Path $work 'history.sqlite3'
$env:YIJING_LOG_PATH = Join-Path $work 'backend.log'
$env:YIJING_BACKUP_DIR = Join-Path $work 'backups'
$env:YIJING_DESKTOP_DEV = '0'
$base = "http://127.0.0.1:$port"
$process = $null
try {
    $process = Start-Process -FilePath $binary -WorkingDirectory $work -PassThru -WindowStyle Hidden
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if ($process.HasExited) { throw "Packaged sidecar exited before startup (exit=$($process.ExitCode))" }
        try {
            $probe = Invoke-WebRequest -Uri "$base/api/desktop/health" -Headers @{ Authorization = "Bearer $token" } -TimeoutSec 2 -SkipHttpErrorCheck
            if ([int]$probe.StatusCode -eq 200) {
                $health = $probe.Content | ConvertFrom-Json
                if ($health.status -ne 'ok' -or $health.mode -ne 'desktop') { throw 'Unexpected desktop health body' }
                $ready = $true
                break
            }
        } catch [System.Net.Http.HttpRequestException] {
            # The packaged interpreter may still be unpacking or starting.
        } catch [System.Net.WebException] {
            # Loopback is not ready yet.
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw 'Packaged sidecar desktop API failed to start within 30 seconds' }

    $anonymous = Invoke-WebRequest -Uri "$base/api/desktop/health" -TimeoutSec 5 -SkipHttpErrorCheck
    if ([int]$anonymous.StatusCode -ne 401) { throw "Missing-token request returned $($anonymous.StatusCode), expected 401" }

    $bad = Invoke-WebRequest -Uri "$base/api/hexagrams" -Headers @{ Authorization = 'Bearer invalid-token' } -TimeoutSec 5 -SkipHttpErrorCheck
    if ([int]$bad.StatusCode -ne 401) { throw "Wrong-token request returned $($bad.StatusCode), expected 401" }

    $headers = @{ Authorization = "Bearer $token" }
    $hexagrams = Invoke-RestMethod -Uri "$base/api/hexagrams" -Headers $headers -TimeoutSec 8
    if (@($hexagrams).Count -ne 64) { throw "Expected 64 classical hexagrams, got $(@($hexagrams).Count)" }
    $history = Invoke-RestMethod -Uri "$base/api/history" -Headers $headers -TimeoutSec 8
    if ($history.total -ne 0 -or @($history.items).Count -ne 0) {
        throw 'Disposable desktop profile unexpectedly contains private history'
    }

    $report = [ordered]@{
        status = 'PASS'
        test = 'packaged-windows-sidecar-startup'
        checks = @('desktop-health-authenticated', 'missing-token-401', 'bad-token-401', '64-hexagram-catalog', 'empty-isolated-history')
        synthetic_temp_profile = $true
        user_data_accessed = $false
        desktop_gui_installer_upgrade_tested = $false
    }
    $parent = Split-Path -Parent $ReportPath
    if ($parent) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    ($report | ConvertTo-Json -Depth 4) | Set-Content -LiteralPath $ReportPath -Encoding utf8
    Write-Output 'Packaged Windows sidecar smoke PASS: authenticated health, 401s, catalog and empty history'
} finally {
    if ($process) {
        try { if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue } }
        finally { $process.Dispose() }
    }
    Remove-Item Env:YIJING_SERVER_PORT,Env:YIJING_API_TOKEN,Env:YIJING_DB_PATH,Env:YIJING_LOG_PATH,Env:YIJING_BACKUP_DIR,Env:YIJING_DESKTOP_DEV -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}
