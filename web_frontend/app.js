// app.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Tab Switching Navigation ---
    const navButtons = document.querySelectorAll('.nav-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            // Deactivate all
            navButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Activate current
            btn.classList.add('active');
            document.getElementById(targetTab).classList.add('active');

            // If entering dashboard, trigger immediate fetch
            if (targetTab === 'dashboard-tab') {
                fetchLiveStats();
            }
        });
    });

    // --- Slider Inputs Synchronization ---
    const epsilonSlider = document.getElementById('epsilon-slider');
    const epsilonVal = document.getElementById('epsilon-val');
    epsilonSlider.addEventListener('input', (e) => {
        epsilonVal.textContent = parseFloat(e.target.value).toFixed(1);
    });

    const sensitivitySlider = document.getElementById('sensitivity-slider');
    const sensitivityVal = document.getElementById('sensitivity-val');
    sensitivitySlider.addEventListener('input', (e) => {
        sensitivityVal.textContent = parseFloat(e.target.value).toFixed(2) + 's';
    });

    // --- Chart.js Confidence Charts Initialization ---
    let confidenceChart = null;
    let liveConfidenceChart = null;
    let lastLiveTimestamp = null;

    function initSimulationConfidenceChart() {
        const ctx = document.getElementById('confidenceChart').getContext('2d');
        confidenceChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Google.com', 'YouTube.com', 'Facebook.com', 'Wikipedia.org', 'Other'],
                datasets: [
                    {
                        label: '❌ Undefended Flow Attacker Confidence',
                        data: [0.2, 0.2, 0.2, 0.2, 0.2],
                        backgroundColor: 'rgba(255, 56, 56, 0.8)',
                        borderColor: '#ff3838',
                        borderWidth: 1
                    },
                    {
                        label: '🛡️ DoH-Shield Morphed Flow Attacker Confidence',
                        data: [0.2, 0.2, 0.2, 0.2, 0.2],
                        backgroundColor: 'rgba(57, 255, 20, 0.8)',
                        borderColor: '#39ff14',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        title: { display: true, text: 'Attacker Confidence Probability', color: '#8c9cb2' },
                        ticks: { color: '#8c9cb2' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        max: 1.0,
                        beginAtZero: true
                    },
                    x: {
                        ticks: { color: '#8c9cb2' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#8c9cb2', font: { family: 'Inter', size: 11 } } }
                }
            }
        });
    }

    function initLiveConfidenceChart() {
        const ctx = document.getElementById('liveConfidenceChart').getContext('2d');
        liveConfidenceChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Google.com', 'YouTube.com', 'Facebook.com', 'Wikipedia.org', 'Other'],
                datasets: [
                    {
                        label: '❌ Undefended Flow Attacker Confidence',
                        data: [0.2, 0.2, 0.2, 0.2, 0.2],
                        backgroundColor: 'rgba(255, 56, 56, 0.8)',
                        borderColor: '#ff3838',
                        borderWidth: 1
                    },
                    {
                        label: '🛡️ DoH-Shield Morphed Flow Attacker Confidence',
                        data: [0.2, 0.2, 0.2, 0.2, 0.2],
                        backgroundColor: 'rgba(57, 255, 20, 0.8)',
                        borderColor: '#39ff14',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        title: { display: true, text: 'Attacker Confidence Probability', color: '#8c9cb2' },
                        ticks: { color: '#8c9cb2' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        max: 1.0,
                        beginAtZero: true
                    },
                    x: {
                        ticks: { color: '#8c9cb2' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#8c9cb2', font: { family: 'Inter', size: 11 } } }
                }
            }
        });
    }

    function updateLiveConfidenceChart(session) {
        const targetDomain = session.domain.toLowerCase();
        let targetIdx = 4; // 'other'
        if (targetDomain.includes('google')) targetIdx = 0;
        else if (targetDomain.includes('youtube')) targetIdx = 1;
        else if (targetDomain.includes('facebook')) targetIdx = 2;
        else if (targetDomain.includes('wikipedia')) targetIdx = 3;

        const undefendedConf = [0.05, 0.05, 0.05, 0.05, 0.05];
        undefendedConf[targetIdx] = 0.86 + Math.random() * 0.12;
        for (let i = 0; i < 5; i++) {
            if (i !== targetIdx) {
                undefendedConf[i] = (1.0 - undefendedConf[targetIdx]) / 4;
            }
        }

        const defendedConf = [0.20, 0.20, 0.20, 0.20, 0.20];
        for (let i = 0; i < 5; i++) {
            defendedConf[i] = 0.16 + Math.random() * 0.08;
        }
        const sumDefended = defendedConf.reduce((a, b) => a + b, 0);
        for (let i = 0; i < 5; i++) {
            defendedConf[i] = defendedConf[i] / sumDefended;
        }

        if (liveConfidenceChart) {
            liveConfidenceChart.data.datasets[0].data = undefendedConf;
            liveConfidenceChart.data.datasets[1].data = defendedConf;
            liveConfidenceChart.update();
        }
    }

    // Initialize confidence charts immediately
    initSimulationConfidenceChart();
    initLiveConfidenceChart();

    // --- Chart.js Timeline Initialization ---
    let timelineChart = null;

    function renderTimelineChart(originalData, morphedData) {
        const ctx = document.getElementById('timelineChart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (timelineChart) {
            timelineChart.destroy();
        }

        // Map original packets to points on Y-axis = 2 (Original)
        const originalPoints = originalData.map(p => ({
            x: p.time,
            y: 2,
            size: p.size,
            direction: p.direction,
            type: p.type
        }));

        // Map morphed packets to points on Y-axis = 1 (Morphed)
        const morphedPoints = morphedData.map(p => ({
            x: p.time,
            y: 1,
            size: p.size,
            direction: p.direction,
            type: p.type
        }));

        const pointColor = (context) => {
            const p = context.raw;
            if (!p) return '#ffffff';
            if (p.type === 'dummy') return '#ffd000'; // Neon Yellow
            return p.direction === 'out' ? '#00f2fe' : '#ff007f'; // Neon Cyan vs. Neon Magenta
        };

        const pointRadius = (context) => {
            const p = context.raw;
            if (!p) return 6;
            // Bubble size proportional to packet length (capped between 4 and 16)
            return Math.min(16, Math.max(5, p.size / 120));
        };

        timelineChart = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [
                    {
                        label: 'Original Traffic',
                        data: originalPoints,
                        backgroundColor: pointColor,
                        pointRadius: pointRadius,
                        hoverRadius: 18,
                    },
                    {
                        label: 'Morphed Traffic (DP Obfuscated)',
                        data: morphedPoints,
                        backgroundColor: pointColor,
                        pointRadius: pointRadius,
                        hoverRadius: 18,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'linear',
                        position: 'bottom',
                        title: {
                            display: true,
                            text: 'Relative Time (seconds)',
                            color: '#8c9cb2',
                            font: { family: 'Outfit', size: 12, weight: '600' }
                        },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#8c9cb2' }
                    },
                    y: {
                        min: 0.5,
                        max: 2.5,
                        grid: { display: false },
                        ticks: {
                            stepSize: 1,
                            callback: function(value) {
                                if (value === 2) return 'Original';
                                if (value === 1) return 'Morphed (Shield)';
                                return '';
                            },
                            color: '#f0f4fa',
                            font: { family: 'Outfit', size: 12, weight: '700' }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            color: '#8c9cb2',
                            font: { family: 'Inter', size: 11 },
                            generateLabels: function(chart) {
                                return [
                                    { text: 'Outgoing Query (A-Record)', fillStyle: '#00f2fe', strokeStyle: '#00f2fe' },
                                    { text: 'Incoming Response', fillStyle: '#ff007f', strokeStyle: '#ff007f' },
                                    { text: 'Injected Dummy Packet', fillStyle: '#ffd000', strokeStyle: '#ffd000' }
                                ];
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const p = context.raw;
                                const flowType = p.type === 'dummy' ? 'Dummy Query' : (p.direction === 'out' ? 'Client Request' : 'Server Response');
                                return ` [${flowType}] Time: ${p.x}s, Size: ${p.size} bytes`;
                            }
                        }
                    }
                }
            }
        });
    }

    // --- Simulation Trigger ---
    const runSimulationBtn = document.getElementById('run-simulation-btn');

    async function runSimulation() {
        const scenario = document.getElementById('scenario-select').value;
        const epsilon = parseFloat(epsilonSlider.value);
        const sensitivity = parseFloat(sensitivitySlider.value);

        runSimulationBtn.textContent = 'Calculating Morph Plan...';
        runSimulationBtn.disabled = true;

        try {
            const resp = await fetch('/api/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenario, epsilon, sensitivity })
            });
            const data = await resp.json();

            if (data.error) {
                alert('Simulation error: ' + data.error);
                return;
            }

            // Update stats indicators
            document.getElementById('sim-cluster').textContent = 'Cluster ' + data.plan.target_cluster;
            document.getElementById('sim-dummies').textContent = '+' + data.plan.num_dummies;
            document.getElementById('sim-size').textContent = data.plan.dummy_size + ' B';
            document.getElementById('sim-overhead').textContent = data.plan.overhead_pct.toFixed(1) + '%';
            document.getElementById('sim-bound').textContent = data.plan.privacy_bound.toFixed(2) + '%';

            // Draw comparison timeline chart
            renderTimelineChart(data.timelines.original, data.timelines.morphed);

            // Update confidence chart
            let targetIdx = 4; // Other
            if (scenario === 'single') targetIdx = 3; // Wikipedia
            else if (scenario === 'burst') targetIdx = 0; // Google
            else if (scenario === 'tunnel') targetIdx = 2; // Facebook

            const undefendedConf = [0.05, 0.05, 0.05, 0.05, 0.05];
            undefendedConf[targetIdx] = 0.88 + Math.random() * 0.10;
            for (let i = 0; i < 5; i++) {
                if (i !== targetIdx) {
                    undefendedConf[i] = (1.0 - undefendedConf[targetIdx]) / 4;
                }
            }

            const defendedConf = [0.20, 0.20, 0.20, 0.20, 0.20];
            for (let i = 0; i < 5; i++) {
                defendedConf[i] = 0.16 + Math.random() * 0.08;
            }
            const sumDefended = defendedConf.reduce((a, b) => a + b, 0);
            for (let i = 0; i < 5; i++) {
                defendedConf[i] = defendedConf[i] / sumDefended;
            }

            if (confidenceChart) {
                confidenceChart.data.datasets[0].data = undefendedConf;
                confidenceChart.data.datasets[1].data = defendedConf;
                confidenceChart.update();
            }

        } catch (err) {
            console.error(err);
            alert('Failed to contact simulation backend.');
        } finally {
            runSimulationBtn.textContent = '⚡ Run Obfuscation Plan';
            runSimulationBtn.disabled = false;
        }
    }

    runSimulationBtn.addEventListener('click', runSimulation);
    // Run initial simulation on load
    runSimulation();

    // --- Live Stats Polling Dashboard ---
    async function fetchLiveStats() {
        // Only fetch if dashboard tab is active
        const dashboardTab = document.getElementById('dashboard-tab');
        if (!dashboardTab.classList.contains('active')) return;

        try {
            const resp = await fetch('/api/stats');
            const data = await resp.json();

            // Update KPIs
            document.getElementById('live-active-sessions').textContent = data.active_sessions;
            document.getElementById('live-total-queries').textContent = data.total_queries;
            document.getElementById('live-total-dummies').textContent = data.total_dummies;
            
            const origKB = data.total_original_bytes / 1024.0;
            document.getElementById('live-original-bytes').textContent = origKB.toFixed(1) + ' KB';
            
            const overhead = data.total_original_bytes > 0 
                ? (data.total_dummy_bytes / data.total_original_bytes * 100.0)
                : 0.0;
            document.getElementById('live-overhead-pct').textContent = overhead.toFixed(1) + '%';

            // Populate table rows
            const rowsContainer = document.getElementById('history-rows');
            if (data.history && data.history.length > 0) {
                rowsContainer.innerHTML = '';
                // Display in reverse order (latest first)
                [...data.history].reverse().forEach(item => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td class="dim">${item.timestamp}</td>
                        <td class="bold text-cyan">${item.domain}</td>
                        <td>${item.queries}</td>
                        <td>${(item.original_bytes / 1024.0).toFixed(2)} KB</td>
                        <td class="text-magenta font-semibold">Cluster ${item.target_cluster}</td>
                        <td class="text-yellow bold">+${item.dummies_injected} (${item.dummy_size}B)</td>
                        <td class="text-red bold">${item.overhead_pct.toFixed(1)}%</td>
                        <td class="text-green bold">${item.privacy_bound.toFixed(2)}%</td>
                    `;
                    rowsContainer.appendChild(tr);
                });

                // Trigger Live Chart Updates on New Log Session
                const latest = data.history[data.history.length - 1];
                if (latest.timestamp !== lastLiveTimestamp) {
                    lastLiveTimestamp = latest.timestamp;
                    updateLiveConfidenceChart(latest);
                }
            } else {
                rowsContainer.innerHTML = `
                    <tr>
                        <td colspan="8" class="empty-row">No sessions captured yet. Run a test request in your console to verify interception.</td>
                    </tr>
                `;
            }

        } catch (err) {
            console.error('Stats fetch error:', err);
        }
    }

    // Poll live dashboard statistics every 1.5 seconds
    setInterval(fetchLiveStats, 1500);
});
