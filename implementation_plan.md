# Implementation Plan — Merging and Combining DoH-Shield Branches

This plan details how to merge the remote `origin/main` changes (the friend's Matplotlib animations, conceptual diagrams, and basic web dashboard) into our current local `interface-1` branch, and unify their charts and execution scripts.

---

## Proposed Changes

### 1. Merge Remote main
- Fetch `origin/main` (already completed).
- Execute `git merge origin/main` to combine code history.
- Git will merge changes automatically. We will check for any conflicts (e.g. in `run.sh`).

### 2. Unify Web Interface Dashboards

We will extract the **Attacker Confidence** bar chart logic from the friend's `web_dashboard.html` and integrate it directly into our premium glassmorphic control portal.

#### [MODIFY] [index.html](file:///c:/Users/91636/.gemini/antigravity-ide/scratch/DoH-Sheild/web_frontend/index.html)
- Add a new canvas element `<canvas id="confidenceChart"></canvas>` next to the timeline chart in the **Simulation Lab** section.
- Add a similar Attacker Confidence chart `<canvas id="liveConfidenceChart"></canvas>` in the **Live Proxy Dashboard** section.
- Adjust grid layouts to show both charts side-by-side or neatly stacked.

#### [MODIFY] [style.css](file:///c:/Users/91636/.gemini/antigravity-ide/scratch/DoH-Sheild/web_frontend/style.css)
- Add layout support for dual-chart rendering (flexbox/grid adjustments).
- Style the charts containers.

#### [MODIFY] [app.js](file:///c:/Users/91636/.gemini/antigravity-ide/scratch/DoH-Sheild/web_frontend/app.js)
- Initialize `confidenceChart` (Simulation tab) and `liveConfidenceChart` (Dashboard tab) using Chart.js.
- **Simulation**: Update `confidenceChart` data dynamically using the predicted classifications for each scenario preset (e.g., target class has 90%+ confidence for undefended flows, but flat ~20% confidence for morphed flows).
- **Live Stats**: Polling `/api/stats` will monitor history log timestamps. When a new session is captured, it will extract the target domain name, dynamically identify the correct class index, and animate `liveConfidenceChart` (reflecting actual attack classification confidence).

### 3. Maintain Compatibility & Parity

#### [NEW] Copy `web_dashboard.html` to `web_frontend/`
- We will copy `web_dashboard.html` to `web_frontend/web_dashboard.html` to ensure any direct routes to `/web_dashboard.html` continue working through our robust Flask web server.

#### [MODIFY] [run.sh](file:///c:/Users/91636/.gemini/antigravity-ide/scratch/DoH-Sheild/run.sh)
- Update `run.sh` (Linux launcher) to start `web_server.py` on port `8082` instead of the insecure `python -m http.server 8000` (which exposes source files).
- Print the premium web portal address: `🌐 Web Control Portal: http://127.0.0.1:8082`
- Ensure all background processes (mitmproxy, mock resolver, and web server) are cleaned up cleanly on Linux exit.

---

## Verification Plan

### Automated Verification
- We will verify that the git merge completes with exit code 0.
- We will check that the Flask web server starts up and serves the updated HTML layout.

### Manual Verification
- We will open the browser at `http://127.0.0.1:8082` and check:
  - **Simulation Lab**: Adjust controls and verify that both the bubble timeline and the Attacker Confidence bar charts update dynamically.
  - **Live Dashboard**: Send a test query and verify that the live dashboard updates and draws the Attacker Confidence charts using the domain queried.
- Run `python animate_morphing.py --show` to verify that the Matplotlib visualization frame animation runs successfully on the local desktop.
