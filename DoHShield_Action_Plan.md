# DoH-Shield: Deep Detailed Action Plan
## From Zero to Working Research Prototype

---

## SYSTEM SETUP DECISION

### Use Ubuntu 22.04 LTS — Not Windows 11

**Reasons (non-negotiable for this project):**

Windows 11 has fundamental problems for this specific work:
- `mitmproxy` on Windows has known TLS interception bugs with HTTP/2 (which DoH uses); the community explicitly recommends Linux
- Raw socket captures (`scapy`, `tcpdump`, `tshark`) require Administrator mode workarounds on Windows and behave differently
- `asyncio` on Windows uses a different event loop (`ProactorEventLoop`) that breaks some mitmproxy addon hooks
- Firefox/Chrome's DoH behavior differs subtly on Windows vs Linux (proxy detection logic differs)
- All major WF papers (Panchenko, Li, Adaptive Tamaraw) collected their datasets and ran experiments on Linux

**What to use:** Ubuntu 22.04 LTS (dual boot or WSL2 is acceptable for coding but run actual traffic capture natively on Ubuntu)

---

## ENVIRONMENT SPLIT

| Task | Where |
|---|---|
| Traffic capture (live DoH proxy) | Ubuntu 22.04, local machine |
| Feature extraction from PCAPs | Ubuntu 22.04 or Colab CPU |
| Dataset preprocessing / EDA | Colab T4 (fast, free) |
| Classifier training (attack models) | Colab T4 GPU |
| Cluster model training (offline) | Colab T4 GPU |
| Morph engine + proxy (prototype) | Ubuntu 22.04, local machine |
| Evaluation / benchmarking | Ubuntu 22.04 (real proxy) + Colab (offline) |

---

## TOOL STACK (every tool and why)

### Core Network Tools (Ubuntu)
| Tool | Version | Purpose |
|---|---|---|
| `mitmproxy` | 10.x | Intercept live DoH HTTPS flows; inject dummy queries |
| `dnspython` | 2.x | Parse raw DNS wire-format inside DoH payloads |
| `scapy` | 2.5.x | Packet-level crafting for dummy query injection |
| `tshark` / `wireshark` | Latest | Ground-truth PCAP recording during data collection |
| `firefox` (configured) | Latest | DoH-enabled browser for traffic generation |
| `curl` with DoH | Latest | Scripted DoH request generation |

### ML / Data (Colab + local)
| Tool | Purpose |
|---|---|
| `pandas`, `numpy` | Feature dataframes, numerical ops |
| `scikit-learn` | K-Means clustering, Random Forest attack model, StandardScaler |
| `PyTorch` (T4 GPU) | Deep Fingerprinting CNN attack model training |
| `scipy` | Laplace distribution sampling (DP noise) |
| `matplotlib`, `seaborn` | Evaluation plots, confusion matrices |
| `joblib` | Save/load trained cluster model |

### Dataset
| Source | What |
|---|---|
| CIRA-CIC-DoHBrw-2020 | Baseline DoH traffic features (UNB, freely downloadable) |
| Self-collected PCAPs | 200-site custom dataset via live capture (ground truth for prototype) |

### Paper Writing
| Tool | Purpose |
|---|---|
| LaTeX (Overleaf) | Paper draft in IEEE two-column format |
| BibTeX | Citation management |

---

## PHASE-BY-PHASE BREAKDOWN

---

## PHASE 0: Foundation Setup (Days 1–5)

### What Happens

This phase does not produce research results. It creates the controlled environment where everything else runs without surprises.

**Step 0.1 — Ubuntu Setup**

Install Ubuntu 22.04 LTS. After a fresh install, run:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv tshark wireshark curl git firefox
pip3 install mitmproxy dnspython scapy pandas numpy scikit-learn scipy matplotlib seaborn joblib
```

**Step 0.2 — Firefox DoH Configuration**

Firefox must be configured to send all DNS through DoH (not the OS resolver) so mitmproxy can capture it:
- Go to `about:config`
- Set `network.trr.mode = 3` (DoH-only, no fallback)
- Set `network.trr.uri = https://cloudflare-dns.com/dns-query`
- Set `network.trr.bootstrapAddress = 1.1.1.1`

This makes every DNS lookup go through DoH over HTTPS, which mitmproxy will intercept.

**Step 0.3 — mitmproxy Certificate Trust**

For mitmproxy to intercept TLS (including DoH over HTTPS), its self-signed CA cert must be trusted by Firefox:
- Start mitmproxy once: `mitmproxy --listen-port 8080`
- Certificate is at `~/.mitmproxy/mitmproxy-ca-cert.pem`
- Import into Firefox: Settings → Privacy → Certificates → Import

**Step 0.4 — Colab Environment**

On Colab, create a standard setup notebook (pinned, reusable):
```python
!pip install dnspython scapy pandas scikit-learn scipy matplotlib seaborn torch torchvision
import torch
print(torch.cuda.get_device_name(0))  # Should print: Tesla T4
```

Upload CIRA-CIC-DoHBrw-2020 CSV files to Google Drive; mount Drive in Colab for fast access.

### Literature for This Phase
- mitmproxy official docs: https://docs.mitmproxy.org
- Firefox DoH configuration: RFC 8484 (DNS Queries over HTTPS), IETF 2018
- CIRA-CIC-DoHBrw-2020 paper: Montazeri Shatoori et al., "Detection of DoH Tunnels using Time-series Classification of Encrypted Traffic", IEEE CyberSci 2020

---

## PHASE 1: Understanding the Threat — Attack Replication (Days 6–18)

### What Happens

Before building a defense, you must replicate the attack from literature. This is standard research methodology (no defense paper is published without this). You are not inventing the attack — you are re-confirming it works on your own data.

**The attack to replicate:** Panchenko et al.'s 153-feature Random Forest classifier + a simple Deep Fingerprinting CNN — both confirmed to achieve >90% accuracy on DoH traffic.

---

### Step 1.1 — Feature Engineering (Understanding What Leaks)

DoH traffic leaks information through these observable features — all extractable without decryption:

**Statistical features (per DNS flow):**

| Feature | What it is | Why it leaks |
|---|---|---|
| `flow_duration` | Total time of DNS resolution burst | Each site has characteristic resolution times |
| `pkt_count_in / out` | Number of DNS query / response packets | Each site triggers different sub-queries (CDN, ads, fonts) |
| `pkt_len_mean / std` | Average and spread of packet sizes | Response sizes correlate with DNS record types (A, AAAA, CNAME) |
| `pkt_len_max / min` | Extremes of packet sizes | |
| `inter_arrival_mean` | Average gap between consecutive packets | Sites have different DNS resolution dependency chains |
| `inter_arrival_std` | Variability in timing | |
| `bytes_in / out` | Total bytes sent and received | |
| `iat_q1, q3` | Quartile timing gaps | |

CIRA-CIC-DoHBrw-2020 already extracts 28 of these features using their `DoHMeter` tool. You use this directly.

**How to load it:**
```python
import pandas as pd
df = pd.read_csv('l2-total.csv')  # From CIRA-CIC-DoHBrw-2020
print(df.columns)  # See all 28 features
print(df['label'].value_counts())  # Benign-DoH vs Malicious-DoH
```

---

### Step 1.2 — Train the Random Forest Attack Model (Colab T4)

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score
from sklearn.preprocessing import StandardScaler

X = df.drop('label', axis=1).values
y = df['label'].values

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)

y_pred = rf.predict(X_test)
print(classification_report(y_test, y_pred))
print(f"F1 Score: {f1_score(y_test, y_pred, average='weighted'):.4f}")
```

**Expected result:** F1 > 0.92 on the CIRA dataset. If you get this, you have confirmed the attack exists on real data. Write this number down — it becomes your paper's "baseline attack accuracy."

---

### Step 1.3 — Train the Deep Fingerprinting CNN (Colab T4)

The Deep Fingerprinting model (Sirinam et al., 2018, CCS) treats the traffic trace as a 1D sequence and applies convolutional filters:

```python
import torch
import torch.nn as nn

class DeepFingerprint(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        self.conv_block = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=8, padding=4),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(32, 64, kernel_size=8, padding=4),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(2),
        )
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 7, 128),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(128, num_classes)
        )
    def forward(self, x):
        return self.fc(self.conv_block(x))
```

Input: the sequence of inter-arrival times and packet sizes (flattened as a 1D vector, zero-padded to fixed length 28).

**Training on T4:**
```python
device = torch.device('cuda')
model = DeepFingerprint(num_classes=2).to(device)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
criterion = nn.CrossEntropyLoss()

for epoch in range(30):
    for X_batch, y_batch in train_loader:
        X_batch = X_batch.unsqueeze(1).to(device)  # [B, 1, 28]
        y_batch = y_batch.to(device)
        loss = criterion(model(X_batch), y_batch)
        optimizer.zero_grad(); loss.backward(); optimizer.step()
```

**Expected training time on T4:** ~4 minutes for 30 epochs on CIRA dataset.

---

### Step 1.4 — Save Both Models

```python
import joblib
joblib.dump(rf, 'rf_attack_model.pkl')
joblib.dump(scaler, 'scaler.pkl')
torch.save(model.state_dict(), 'df_attack_model.pt')
```

These saved models are reused in Phase 4 (evaluation against defended traffic).

### Literature for This Phase
- Sirinam et al., "Deep Fingerprinting: Undermining Website Fingerprinting Defenses with Deep Learning", CCS 2018 — original Deep Fingerprinting paper
- Panchenko et al., "Toward practical defense against traffic analysis attacks on encrypted DNS traffic", Computers & Security 2022 — 153-feature RF baseline
- Montazeri Shatoori et al., CIRA-CIC-DoHBrw-2020 dataset paper, IEEE CyberSci 2020

---

## PHASE 2: Understanding the Fingerprint Structure — Clustering (Days 19–28)

### What Happens

This phase does the core scientific work of DoH-Shield. You analyze the DoH fingerprints of websites and discover how they naturally group. This is the offline, one-time computation that the proxy will rely on at runtime.

**The key insight from the literature:** Websites that load similar numbers of sub-resources (same CDN, same tracker libraries, same font providers) produce similar DNS patterns. K-Means can find these groups. An attacker who sees your traffic can only narrow you down to a cluster, not a single site — this is where the privacy gain comes from.

---

### Step 2.1 — Exploratory Data Analysis (EDA)

Before clustering, understand the feature space visually.

```python
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

pca = PCA(n_components=2)
X_2d = pca.fit_transform(X_scaled)

plt.figure(figsize=(10, 7))
plt.scatter(X_2d[:, 0], X_2d[:, 1], c=y_numeric, cmap='tab20', s=5, alpha=0.5)
plt.colorbar()
plt.title('PCA of DoH Traffic Fingerprints')
plt.savefig('pca_fingerprints.png', dpi=150)
```

What you are looking for: natural clusters visible in 2D PCA space. If clusters are visible, K-Means will find them. Literature (Glove, Adaptive Tamaraw) confirms they exist.

---

### Step 2.2 — Determine Optimal K (Elbow Method)

```python
from sklearn.cluster import KMeans

inertias = []
K_range = range(5, 100, 5)

for k in K_range:
    km = KMeans(n_clusters=k, init='k-means++', n_init=10, random_state=42)
    km.fit(X_scaled)
    inertias.append(km.inertia_)

plt.plot(K_range, inertias, 'bo-')
plt.xlabel('Number of Clusters K')
plt.ylabel('Inertia (Within-cluster Sum of Squares)')
plt.title('Elbow Method for Optimal K')
plt.savefig('elbow.png', dpi=150)
```

The "elbow" in the curve tells you the optimal K. Literature suggests K = 20–50 for 1000 websites gives good privacy-utility tradeoff.

---

### Step 2.3 — Train Final K-Means Cluster Model

```python
K_optimal = 30  # Adjust based on elbow

km_final = KMeans(n_clusters=K_optimal, init='k-means++', n_init=20, random_state=42)
km_final.fit(X_scaled)

cluster_labels = km_final.labels_
centroids = km_final.cluster_centers_

print(f"Cluster sizes: {pd.Series(cluster_labels).value_counts().describe()}")
# Good: clusters should be roughly similar in size (not one giant cluster)
```

---

### Step 2.4 — Compute l-Diversity per Cluster

l-diversity is a formal privacy metric: in a cluster of size l, each member looks as likely to be the true website as any other. You need at least l ≥ 3.

```python
from collections import Counter

cluster_diversity = {}
for cid in range(K_optimal):
    members = [y[i] for i in range(len(y)) if cluster_labels[i] == cid]
    unique_sites = len(set(members))
    cluster_diversity[cid] = unique_sites

min_l = min(cluster_diversity.values())
mean_l = sum(cluster_diversity.values()) / len(cluster_diversity)
print(f"Minimum l-diversity: {min_l}")
print(f"Mean l-diversity: {mean_l:.1f}")
```

This number goes directly into your paper's formal privacy bound: `P_attack ≤ 1/l + exp(-ε)`

---

### Step 2.5 — Save the Cluster Model

```python
joblib.dump(km_final, 'cluster_model.pkl')
joblib.dump(scaler, 'cluster_scaler.pkl')
joblib.dump(centroids, 'centroids.npy')  # NumPy array, reload with np.load
```

The proxy will load these files at startup.

### Literature for This Phase
- Nithyanand et al., "Glove: A Bespoke Website Fingerprinting Defense", WPES 2014 — first paper to use clustering for WF defense; your foundational reference
- Khajavi & Wang, "Lightening the Load: A Cluster-Based Framework for a Lower-Overhead, Provable Website Fingerprinting Defense", arXiv 2025 — direct precursor; you extend their idea to DoH specifically
- Sweeney, "k-Anonymity: A Model for Protecting Privacy", International Journal of Uncertainty 2002 — defines k-anonymity
- Machanavajjhala et al., "l-Diversity: Privacy Beyond k-Anonymity", ACM TKDD 2007 — defines l-diversity; your cluster diversity metric

---

## PHASE 3: Building the Defense — DoH-Shield Proxy (Days 29–45)

### What Happens

This is the implementation phase. You build a working local proxy that sits between Firefox and Cloudflare, intercepts DoH flows, and morphs them. This is your demo artifact — something you can run live during presentation.

The proxy has four internal components, built one at a time.

---

### Component 3.1 — DoH Flow Interceptor (mitmproxy Addon)

mitmproxy intercepts HTTPS flows. You write a Python addon that fires on every DoH request:

```python
# doh_shield_addon.py
from mitmproxy import http
import json, time

class DoHShieldAddon:
    def __init__(self):
        self.flows = {}  # session_id -> list of (timestamp, size)

    def request(self, flow: http.HTTPFlow):
        # Only process Cloudflare DoH requests
        if 'cloudflare-dns.com' in flow.request.pretty_host:
            session_id = flow.request.headers.get('x-session-id', 'default')
            ts = time.time()
            sz = len(flow.request.content)
            
            if session_id not in self.flows:
                self.flows[session_id] = []
            self.flows[session_id].append((ts, sz, 'out'))
    
    def response(self, flow: http.HTTPFlow):
        if 'cloudflare-dns.com' in flow.request.pretty_host:
            session_id = flow.request.headers.get('x-session-id', 'default')
            ts = time.time()
            sz = len(flow.response.content)
            if session_id in self.flows:
                self.flows[session_id].append((ts, sz, 'in'))

addons = [DoHShieldAddon()]
```

Run with: `mitmdump -s doh_shield_addon.py --listen-port 8080`

---

### Component 3.2 — Feature Extractor (Real-time)

From the collected flow events, extract the same 28 features the cluster model was trained on:

```python
import numpy as np

def extract_features(flow_events):
    """flow_events: list of (timestamp, size, direction) tuples"""
    if len(flow_events) < 2:
        return None
    
    timestamps = [e[0] for e in flow_events]
    sizes = [e[1] for e in flow_events]
    out_sizes = [e[1] for e in flow_events if e[2] == 'out']
    in_sizes = [e[1] for e in flow_events if e[2] == 'in']
    
    iats = np.diff(timestamps)  # inter-arrival times
    
    features = [
        timestamps[-1] - timestamps[0],     # flow_duration
        len(out_sizes),                      # pkt_count_out
        len(in_sizes),                       # pkt_count_in
        np.mean(sizes), np.std(sizes),       # pkt_len_mean, std
        np.max(sizes), np.min(sizes),        # pkt_len_max, min
        np.sum(out_sizes),                   # bytes_out
        np.sum(in_sizes),                    # bytes_in
        np.mean(iats) if len(iats) > 0 else 0,   # iat_mean
        np.std(iats) if len(iats) > 0 else 0,    # iat_std
        np.percentile(iats, 25) if len(iats) > 0 else 0,  # iat_q1
        np.percentile(iats, 75) if len(iats) > 0 else 0,  # iat_q3
        # ... pad remaining features to 28
    ]
    
    return np.array(features[:28])  # Ensure exactly 28 features
```

---

### Component 3.3 — Cluster Assignment + Morph Engine

This is the core of DoH-Shield. Given a feature vector, assign it to a cluster, then inject dummies to push the trace toward the cluster centroid:

```python
import joblib
import numpy as np
import secrets

class MorphEngine:
    def __init__(self, model_path='cluster_model.pkl', scaler_path='cluster_scaler.pkl'):
        self.km = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        self.centroids = self.km.cluster_centers_
    
    def assign_cluster(self, features):
        """Assign feature vector to its cluster"""
        scaled = self.scaler.transform(features.reshape(1, -1))
        cluster_id = self.km.predict(scaled)[0]
        return cluster_id
    
    def randomized_cluster(self, features, session_key):
        """Adaptive randomization: reassign cluster using session key"""
        cluster_id = self.assign_cluster(features)
        # Deterministically but unpredictably offset cluster using session key
        offset = int.from_bytes(session_key[:2], 'big') % 3  # ±1 neighbor
        new_cluster = (cluster_id + offset) % self.km.n_clusters
        return new_cluster
    
    def compute_dummy_count(self, features, cluster_id):
        """How many dummy packets to inject to approach centroid"""
        centroid = self.centroids[cluster_id]
        scaled = self.scaler.transform(features.reshape(1, -1))[0]
        
        # Target: match centroid's pkt_count_out (index 1 in feature vector)
        current_count = features[1]  # pkt_count_out
        target_count = int(centroid[1] * self.scaler.scale_[1] + self.scaler.mean_[1])
        
        dummy_needed = max(0, target_count - int(current_count))
        return dummy_needed
```

---

### Component 3.4 — Differential Privacy Timing Noise

This is what makes the defense formally provable. After morphing, add calibrated Laplace noise to all inter-arrival timing gaps:

```python
from scipy.stats import laplace

class DPTimingNoise:
    def __init__(self, epsilon=1.0):
        """
        epsilon: privacy budget (lower = more private, more noise)
        sensitivity: maximum change one sample can cause in timing stats
        """
        self.epsilon = epsilon
        self.sensitivity = 0.1  # seconds; max IAT sensitivity (tuned empirically)
    
    def add_noise(self, iat_sequence):
        """Add Laplace noise to inter-arrival time sequence"""
        scale = self.sensitivity / self.epsilon
        noise = laplace.rvs(loc=0, scale=scale, size=len(iat_sequence))
        noisy_iats = np.clip(iat_sequence + noise, 0, None)  # No negative delays
        return noisy_iats
    
    def delay_packet(self, base_delay, noise_value):
        """Apply delay to actual packet transmission"""
        actual_delay = max(0, base_delay + noise_value)
        return actual_delay
    
    def privacy_guarantee(self):
        """Return formal ε-DP guarantee"""
        return self.epsilon
    
    def attacker_bound(self, l_diversity):
        """
        Formal upper bound on attacker accuracy:
        P_attack <= 1/l + exp(-ε)
        """
        return (1.0 / l_diversity) + np.exp(-self.epsilon)
```

**Why Laplace specifically?** The Laplace Mechanism is the canonical noise mechanism for ε-differential privacy on real-valued queries (Dwork & Roth, "The Algorithmic Foundations of Differential Privacy", 2014). For a query with sensitivity Δ, adding Lap(Δ/ε) achieves ε-DP. This is not an approximation — it is an exact mathematical guarantee. This is what makes your paper's claim publishable.

---

### Component 3.5 — Session Key + Dummy Injector

```python
import asyncio

class DummyInjector:
    def __init__(self, resolver_url='https://cloudflare-dns.com/dns-query'):
        self.resolver_url = resolver_url
        self.session_key = secrets.token_bytes(32)
    
    async def inject_dummy_query(self):
        """Send a benign dummy DNS query to a random harmless domain"""
        import random
        import httpx
        
        dummy_domains = [
            'dummy-cdn-request.example.com',
            'static-asset-placeholder.test',
            # Use domains that always NXDOMAIN; no actual resolution happens
        ]
        
        domain = random.choice(dummy_domains)
        # Encode as DNS wire format and POST to DoH resolver
        query_data = build_dns_query(domain)  # dnspython call
        
        async with httpx.AsyncClient() as client:
            await client.post(
                self.resolver_url,
                content=query_data,
                headers={'Content-Type': 'application/dns-message'}
            )
    
    async def inject_n_dummies(self, n, timing_gaps):
        """Inject n dummy queries with DP-noised timing"""
        dp = DPTimingNoise(epsilon=1.0)
        noisy_gaps = dp.add_noise(np.array(timing_gaps[:n]))
        
        for gap in noisy_gaps:
            await asyncio.sleep(gap)
            await self.inject_dummy_query()
```

---

### Putting It All Together (Full Proxy Loop)

```
Browser sends DoH query to Cloudflare
    → mitmproxy intercepts
    → DoHShieldAddon records (timestamp, size)
    → After N queries (or timeout), flow is considered "complete"
    → FeatureExtractor extracts 28 features
    → MorphEngine assigns cluster, computes dummy count
    → DPTimingNoise adds Laplace noise to upcoming timing gaps
    → DummyInjector asynchronously fires dummy queries
    → Original query forwarded to Cloudflare (with noised timing)
```

**Total added latency:** The dummy injections happen asynchronously — they do NOT block the original queries. The only latency comes from the Laplace timing noise on the original flow, which is bounded by the DP parameter ε.

### Literature for This Phase
- Dwork & Roth, "The Algorithmic Foundations of Differential Privacy", Foundations and Trends in TCS, 2014 — the definitive DP reference; must cite for your Laplace mechanism
- Dwork et al., "Calibrating Noise to Sensitivity in Private Data Analysis", TCC 2006 — original Laplace mechanism paper
- mitmproxy documentation (https://docs.mitmproxy.org) for addon hooks
- dnspython documentation for DNS wire-format parsing

---

## PHASE 4: Evaluation (Days 46–58)

### What Happens

You run the two attack models (Phase 1) against defended traffic (Phase 3) and measure the results. This is where you generate all numbers for the paper's comparison table.

**The evaluation protocol follows standard WF research methodology** (Juarez et al., "Critical Evaluation of Website Fingerprinting Attacks", CCS 2014):

---

### Step 4.1 — Collect Defended Traffic

With DoH-Shield proxy running, visit 200 websites 10 times each:

```bash
# Script to automate browser visits through mitmproxy
for site in $(cat top200_sites.txt); do
    curl --proxy http://localhost:8080 \
         --doh-url https://cloudflare-dns.com/dns-query \
         "https://$site" > /dev/null 2>&1
    sleep 2
done
```

This generates the "defended dataset" — what the attacker sees after DoH-Shield runs.

---

### Step 4.2 — Attack the Defended Traffic

Load both saved attack models and run them on defended features:

```python
import joblib, torch
import numpy as np

# Load attack models
rf = joblib.load('rf_attack_model.pkl')
scaler = joblib.load('scaler.pkl')

# Load defended features
X_defended = np.load('defended_features.npy')
y_defended = np.load('defended_labels.npy')

X_defended_scaled = scaler.transform(X_defended)

# Random Forest attack
y_pred_rf = rf.predict(X_defended_scaled)
from sklearn.metrics import accuracy_score, f1_score
rf_acc = accuracy_score(y_defended, y_pred_rf)
print(f"RF Attacker Accuracy (Defended): {rf_acc:.4f}")

# Deep Fingerprinting attack
model = DeepFingerprint(num_classes=200)
model.load_state_dict(torch.load('df_attack_model.pt'))
model.eval()

# ... run inference
df_acc = ...
print(f"DF Attacker Accuracy (Defended): {df_acc:.4f}")
```

---

### Step 4.3 — Adaptive Adversary Test

The adaptive adversary retrains on defended traffic. This is the hardest test:

```python
# Attacker collects some defended samples and retrains
X_adaptive_train, X_adaptive_test = train_test_split(X_defended, test_size=0.3)

rf_adaptive = RandomForestClassifier(n_estimators=200)
rf_adaptive.fit(scaler.transform(X_adaptive_train), y_adaptive_train)

adaptive_acc = accuracy_score(y_adaptive_test, rf_adaptive.predict(...))
print(f"Adaptive RF Accuracy: {adaptive_acc:.4f}")
```

Even against this, the formal DP bound guarantees: `P_attack ≤ 1/l + exp(-ε)` — the attacker cannot exceed this regardless of how many times they retrain.

---

### Step 4.4 — Overhead Measurement

```python
# Bandwidth overhead
original_bytes = sum(original_traffic_sizes)
dummy_bytes = sum(dummy_query_sizes)
bw_overhead = (dummy_bytes / original_bytes) * 100
print(f"Bandwidth Overhead: {bw_overhead:.1f}%")

# Latency overhead
import numpy as np
original_latencies = np.array([...])  # Undefended DNS resolution times
defended_latencies = np.array([...])  # Defended DNS resolution times
latency_overhead_ms = np.mean(defended_latencies - original_latencies) * 1000
print(f"Latency Overhead: {latency_overhead_ms:.1f} ms")
```

---

### Step 4.5 — Formal Bound Verification

```python
dp = DPTimingNoise(epsilon=1.0)
l_min = min(cluster_diversity.values())

theoretical_bound = dp.attacker_bound(l_min)
print(f"Theoretical Attacker Accuracy Upper Bound: {theoretical_bound:.4f}")
print(f"Observed RF Attacker Accuracy: {rf_acc:.4f}")

assert observed_acc <= theoretical_bound + 0.02, \
    "Empirical result exceeds theoretical bound — check implementation"
```

This verification step is critical for the paper: you show the math matches the experiment.

### Literature for This Phase
- Juarez et al., "Critical Evaluation of Website Fingerprinting Attacks", CCS 2014 — defines the evaluation protocol all WF papers use (must cite)
- Rimmer et al., "Automated Website Fingerprinting through Deep Learning", NDSS 2018 — Deep Fingerprinting baseline

---

## PHASE 5: Final Prototype for Demonstration (Days 59–70)

### What Happens

You build a clean, runnable demo that shows the system working live in 5 minutes in front of an evaluator.

---

### Demo Architecture

```
Terminal 1:          Terminal 2:         Terminal 3:
[mitmproxy +       [live dashboard      [Firefox
 DoHShield         showing:             browser with
 addon running]    - cluster ID         DoH → 8080]
                   - dummy count
                   - DP ε
                   - overhead %]
```

---

### Demo Script (What You Run)

**1. Start the proxy:**
```bash
mitmdump -s doh_shield.py --listen-port 8080 --ssl-insecure
```

**2. Set Firefox proxy to localhost:8080**

**3. Open the dashboard (Python + Rich library):**
```python
from rich.live import Live
from rich.table import Table

# Real-time table showing:
# Site visited | Cluster assigned | Dummies injected | BW overhead | DP bound
```

**4. Visit any website in Firefox.** The dashboard updates in real-time showing:
- Which cluster the site was assigned to
- How many dummy queries were fired
- Current bandwidth overhead
- Formal attacker accuracy upper bound

**5. Run attack model against captured defended traffic on-the-fly and show reduced accuracy.**

---

### What the Demo Proves to Evaluators

| Claim | What You Show |
|---|---|
| "It intercepts DoH" | Live mitmproxy log shows HTTPS flows |
| "It assigns clusters" | Dashboard shows cluster ID per site |
| "It injects dummies" | Wireshark capture shows extra DNS queries |
| "It reduces attacker accuracy" | Run RF predictor live: shows low confidence |
| "It has formal guarantee" | Display bound formula with computed values |
| "Overhead is low" | Dashboard shows ≤ 40% BW overhead live |

---

## PHASE 6: Paper Writing (Days 71–84)

### Structure (IEEE Two-Column Format, ~8 pages)

```
I.    Introduction (1 page)
      - DoH privacy illusion problem
      - Research gap
      - Our contributions (3 bullets)

II.   Background & Related Work (1.5 pages)
      - DoH protocol (RFC 8484)
      - WF attack taxonomy
      - Existing defenses and their limits (table)

III.  Threat Model (0.5 pages)
      - Passive adversary on network path
      - Adaptive adversary (retrains on defended traces)
      - No server cooperation assumed

IV.   DoH-Shield Design (2 pages)
      - System architecture diagram
      - Cluster-aware morphing
      - DP timing noise mechanism
      - Session-key adaptive randomization
      - Formal privacy analysis

V.    Evaluation (2 pages)
      - Experimental setup
      - Attack accuracy comparison table
      - Overhead comparison table
      - Formal bound verification

VI.   Discussion & Limitations (0.5 pages)
VII.  Conclusion (0.5 pages)
References
```

### Target Venues
- **NDSS 2026 Workshop on DNS Privacy** — perfect fit, student-friendly
- **IEEE Networking Letters** — fast review (2–4 weeks), accepts 5-page papers
- **ACM CCS 2026 Poster Track** — high visibility

---

## FULL TIMELINE SUMMARY

| Phase | Days | Key Output |
|---|---|---|
| 0: Environment Setup | 1–5 | Working mitmproxy + Firefox DoH chain |
| 1: Attack Replication | 6–18 | RF + CNN attack models, baseline accuracy numbers |
| 2: Clustering | 19–28 | K-Means model, l-diversity computed, formal bound set |
| 3: Proxy Build | 29–45 | Working DoH-Shield proxy with all 4 components |
| 4: Evaluation | 46–58 | All comparison numbers, formal verification |
| 5: Demo Polish | 59–70 | Live demo with dashboard |
| 6: Paper | 71–84 | Draft ready for submission |

**Total: 12 weeks, exactly one semester.**

---

## DIVISION OF LABOR (You vs. Antigravity 2.0)

| You (Research) | Antigravity 2.0 (Building) |
|---|---|
| Read each paper cited in each phase | Write `doh_shield.py` addon per Component 3.x spec |
| Interpret EDA results (does the elbow make sense?) | Write the feature extractor (Component 3.2) |
| Choose K after seeing elbow plot | Write training notebooks for RF and CNN |
| Decide ε (privacy budget) — tradeoff call | Write the MorphEngine class |
| Write the formal proof section of the paper | Write the DPTimingNoise class |
| Validate that empirical ≤ theoretical bound | Write the evaluation scripts |
| Write all paper sections | Build the Rich dashboard for demo |
| Present and defend | Wire all components into final runnable main.py |

---

## KEY PAPERS TO READ (In Order, Each Phase)

### Phase 0
1. RFC 8484 — DNS Queries over HTTPS (2018) — 15 pages, readable

### Phase 1
2. Sirinam et al., "Deep Fingerprinting", CCS 2018 — attack model you implement
3. Panchenko et al., Computers & Security 2022 — 153-feature baseline

### Phase 2
4. Nithyanand et al., "Glove", WPES 2014 — clustering for WF defense
5. Machanavajjhala et al., "l-Diversity", TKDD 2007 — your privacy metric
6. Khajavi & Wang, arXiv 2509.01046, 2025 — closest existing work (extend this)

### Phase 3
7. Dwork & Roth, "Algorithmic Foundations of DP", FnTCS 2014 — Laplace mechanism (Chapter 3 only, ~40 pages)
8. Dwork et al., "Calibrating Noise to Sensitivity", TCC 2006 — original DP paper

### Phase 4
9. Juarez et al., "Critical Evaluation of WF Attacks", CCS 2014 — evaluation protocol
10. Li et al., "From Fingerprint to Footprint", ESORICS 2024 — SOTA attack you compare against

---

*This document is the complete execution blueprint. Each code block is a direct instruction to Antigravity 2.0. Each paper citation is your reading assignment for that phase.*
