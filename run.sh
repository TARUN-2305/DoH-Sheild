#!/bin/bash
# run.sh
# ---------------------------------------------------------------------
# Starter script for the DoH-Shield local proxy and rich terminal dashboard.
# CS362IA: Network Programming and Security | Semester VI | RVCE
# ---------------------------------------------------------------------

echo "=================================================="
echo "🛡️  D O H - S H I E L D   S Y S T E M   S T A R T  🛡️"
echo "=================================================="

# Ensure we are in the script's directory
cd "$(dirname "$0")"

# Activate Python virtual environment
if [ -f "./venv/bin/activate" ]; then
    echo "[*] Activating virtual environment..."
    source ./venv/bin/activate
else
    echo "[!] Virtual environment venv not found! Please create it first."
    exit 1
fi

# Clean up stale stats from previous runs
rm -f stats.json stats.json.tmp

# Run verification tests on core components before starting the proxy
echo "[*] Running component verification checks..."
python verify_shield.py
if [ $? -ne 0 ]; then
    echo "[!] Component verification check failed! Please review verify_shield.py."
    exit 1
fi
echo "[+] Verification successful! Core components are healthy."

# Spin up local mock DoH resolver on port 8081
echo "[*] Spawning local mock DoH resolver on port 8081..."
python mock_doh_resolver.py >/dev/null 2>&1 &
RESOLVER_PID=$!

# Spin up mitmproxy in the background
echo "[*] Spawning mitmproxy DoH Interception Addon on port 8080..."
mitmdump -s doh_shield.py --listen-port 8080 --ssl-insecure >/dev/null 2>&1 &
MITM_PID=$!

# Spin up interactive web server on port 8082
echo "[*] Spawning interactive web portal on port 8082..."
python web_server.py >/dev/null 2>&1 &
WEB_PID=$!

# Ensure background processes are cleaned up when the script exits
cleanup() {
    echo -e "\n[*] Terminating background processes (mitmproxy PID: $MITM_PID, Resolver PID: $RESOLVER_PID, Web Server PID: $WEB_PID)..."
    kill $MITM_PID $RESOLVER_PID $WEB_PID 2>/dev/null
    wait $MITM_PID $RESOLVER_PID $WEB_PID 2>/dev/null
    rm -f stats.json stats.json.tmp
    echo "🛡️ DoH-Shield stopped successfully. Goodbye!"
}
trap cleanup INT TERM EXIT

# Wait a moment for services to bind to ports
sleep 2.5

# Double check if mitmproxy started successfully
if ! kill -0 $MITM_PID 2>/dev/null; then
    echo "[!] mitmproxy failed to start! Port 8080 might already be in use."
    exit 1
fi

# Double check if resolver started successfully
if ! kill -0 $RESOLVER_PID 2>/dev/null; then
    echo "[!] Local mock resolver failed to start! Port 8081 might already be in use."
    exit 1
fi

# Double check if web server started successfully
if ! kill -0 $WEB_PID 2>/dev/null; then
    echo "[!] Web portal server failed to start! Port 8082 might already be in use."
    exit 1
fi

# Print dashboard address
echo "=================================================="
echo "🛡️  DoH-Shield is ACTIVE and PROTECTING your traffic!"
echo "🌐 Web Control Portal: http://127.0.0.1:8082"
echo "=================================================="
sleep 1.0

# Start our beautiful rich dashboard in the foreground
echo "[*] Launching real-time terminal dashboard..."
python dashboard.py
