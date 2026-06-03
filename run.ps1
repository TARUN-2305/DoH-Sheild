# run.ps1
# ---------------------------------------------------------------------
# Starter script for the DoH-Shield local proxy and rich terminal dashboard on Windows.
# CS362IA: Network Programming and Security | Semester VI | RVCE
# ---------------------------------------------------------------------

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Green
Write-Host "🛡️  D O H - S H I E L D   S Y S T E M   S T A R T  🛡️" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

# Clean up stale stats from previous runs
Remove-Item -Path stats.json, stats.json.tmp, mitm_out.log, mitm_err.log, resolver_out.log, resolver_err.log, web_server_out.log, web_server_err.log -ErrorAction SilentlyContinue

# Run verification tests on core components before starting the proxy
Write-Host "[*] Running component verification checks..." -ForegroundColor Cyan
& ".\venv\Scripts\python.exe" verify_shield.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Component verification check failed! Please review feature_extractor.py or morph_engine.py." -ForegroundColor Red
    exit 1
}
Write-Host "[+] Verification successful! Core components are healthy." -ForegroundColor Green

# Spin up local mock DoH resolver on port 8081
Write-Host "[*] Spawning local mock DoH resolver on port 8081..." -ForegroundColor Cyan
$resolverProcess = Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "mock_doh_resolver.py" -NoNewWindow -RedirectStandardOutput "resolver_out.log" -RedirectStandardError "resolver_err.log" -PassThru

# Spin up mitmproxy in the background
Write-Host "[*] Spawning mitmproxy DoH Interception Addon on port 8080..." -ForegroundColor Cyan
$mitmProcess = Start-Process -FilePath ".\venv\Scripts\mitmdump.exe" -ArgumentList "-s doh_shield.py --listen-port 8080 --ssl-insecure" -NoNewWindow -RedirectStandardOutput "mitm_out.log" -RedirectStandardError "mitm_err.log" -PassThru

# Spin up local web server on port 8082
Write-Host "[*] Spawning interactive web portal on port 8082..." -ForegroundColor Cyan
$webProcess = Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "web_server.py" -NoNewWindow -RedirectStandardOutput "web_server_out.log" -RedirectStandardError "web_server_err.log" -PassThru

# Wait a moment for processes to bind
Start-Sleep -Seconds 2.5

# Double check if processes started successfully
if ($mitmProcess.HasExited) {
    Write-Host "[!] mitmproxy failed to start! Port 8080 might already be in use or mitmdump crashed." -ForegroundColor Red
    if (Test-Path "mitm_err.log") {
        Write-Host "LOGS:" -ForegroundColor Yellow
        Get-Content "mitm_err.log" -Tail 10
    }
    # Clean up resolver and web server if mitm failed
    Stop-Process -Id $resolverProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $webProcess.Id -Force -ErrorAction SilentlyContinue
    exit 1
}
if ($resolverProcess.HasExited) {
    Write-Host "[!] Local mock resolver failed to start! Port 8081 might already be in use." -ForegroundColor Red
    if (Test-Path "resolver_err.log") {
        Write-Host "LOGS:" -ForegroundColor Yellow
        Get-Content "resolver_err.log" -Tail 10
    }
    # Clean up mitm and web server if resolver failed
    Stop-Process -Id $mitmProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $webProcess.Id -Force -ErrorAction SilentlyContinue
    exit 1
}
if ($webProcess.HasExited) {
    Write-Host "[!] Web portal server failed to start! Port 8082 might already be in use." -ForegroundColor Red
    if (Test-Path "web_server_err.log") {
        Write-Host "LOGS:" -ForegroundColor Yellow
        Get-Content "web_server_err.log" -Tail 10
    }
    # Clean up mitm and resolver if web server failed
    Stop-Process -Id $mitmProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $resolverProcess.Id -Force -ErrorAction SilentlyContinue
    exit 1
}

try {
    # Print the web portal address in the terminal for user convenience
    Write-Host ""
    Write-Host "[+] 🌐 DoH-Shield Web Control Portal is live at: http://127.0.0.1:8082" -ForegroundColor Green
    Write-Host ""

    # Start the terminal dashboard in the foreground
    Write-Host "[*] Launching real-time terminal dashboard..." -ForegroundColor Cyan
    & ".\venv\Scripts\python.exe" dashboard.py
}
finally {
    Write-Host "`n[*] Terminating local processes..." -ForegroundColor Cyan
    Stop-Process -Id $mitmProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $resolverProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $webProcess.Id -Force -ErrorAction SilentlyContinue
    Remove-Item -Path stats.json, stats.json.tmp -ErrorAction SilentlyContinue
    Write-Host "🛡️ DoH-Shield stopped successfully. Goodbye!" -ForegroundColor Green
}
