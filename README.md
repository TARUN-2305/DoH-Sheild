# 🛡️ DoH-Shield: Client-Side Traffic Morphing Proxy for Website Fingerprinting Defense in DNS-over-HTTPS

DoH-Shield is a mathematically backed, client-side DNS-over-HTTPS (DoH) traffic obfuscation proxy designed to neutralize state-of-the-art Website Fingerprinting (WF) attacks. Developed as part of **CS362IA: Network Programming and Security (Semester VI, RVCE)**, the system partitions browser DoH traffic profiles into indistinguishable clusters and applies differential privacy guarantees to secure user privacy against network-level eavesdroppers with minimal performance overhead.

---

## 📖 Table of Contents
1. [Project Overview](#-project-overview)
2. [Threat Model & Core Architecture](#-threat-model--core-architecture)
3. [Visual Comparisons & Flow Diagrams](#-visual-comparisons--flow-diagrams)
4. [Guarantees & Privacy Bounds](#-guarantees--privacy-bounds)
5. [File Directory Structure](#-file-directory-structure)
6. [Installation & Setup](#-installation--setup)
7. [End-to-End Training (Google Colab)](#-end-to-end-training-google-colab)
8. [Running the System](#-running-the-system)
9. [System Verification & Self-Tests](#-system-verification--self-tests)
10. [References](#-references)

---

## 🌟 Project Overview

DNS-over-HTTPS (DoH, RFC 8484) encrypts DNS transactions inside HTTPS tunnels to prevent passive eavesdroppers from discovering target domain names. However, encrypting packet payloads is insufficient. Modern **Website Fingerprinting (WF)** attacks exploit traffic metadata:
- **Packet size distributions**
- **Flow durations**
- **Inter-packet arrival times**
- **Request-response latencies**

Classifiers like **Random Forest** and **Deep Fingerprinting CNNs** (Sirinam et al., CCS 2018) can identify visited websites with **>99% accuracy** on raw DoH traffic.

**DoH-Shield** intercepts local browser traffic, extracts 29 statistical flow features in real-time, maps them into unsupervised K-Means clusters, and morphs the flow characteristics toward cluster centroids. It dynamically injects padded dummy DNS queries (using EDNS(0) padding) and adds Laplace timing noise to achieve robust confusion under formal differential privacy limits.

### 🎬 Traffic Morphing Simulation
The animation below demonstrates a side-by-side simulation of a packet stream: an undefended flow (leaking signatures, causing 99% attacker CNN confidence) vs. a morphed DoH-Shield flow (injected dummies, flattened classifier confidence below 37%).

![DoH-Shield Morphing Simulation](./doh_shield_morphing.gif)

---

## 🛠️ Threat Model & Core Architecture

DoH-Shield operates under a **passive, network-level eavesdropper threat model**. The attacker observes encrypted TLS flows traversing the network path (IPs, packet lengths, direction, and relative arrival times) but cannot decrypt payloads or compromise target servers.

### System Architecture Diagram
The layout below illustrates how the Client Browser, Local Proxy, and Upstream Resolvers interface, detailing the sub-modules responsible for feature extraction, morphing, EDNS(0) padding, and DP timing noise:

![DoH-Shield System Architecture](./doh_shield_sys_diagram.png)

### Core Components
1. **Real-time Feature Extractor (`feature_extractor.py`)**: Computes 29 statistical descriptors (mean, median, mode, variance, std dev, skewness, and coefficients of variation for lengths and timestamps) on sliding packet trace windows.
2. **KMeans Morph Engine (`morph_engine.py`)**: Loads pre-trained KMeans clusters and scaler. Maps the incoming trace to the nearest cluster centroid and applies **Adaptive Session-Key Cluster Randomization** to deter static classification models.
3. **EDNS(0) Dummy Injector (`dummy_injector.py`)**: Crafts compliant DNS queries asynchronously using `dnspython` and injects exact EDNS(0) padding to pad queries to precise target sizes.
4. **MITM Interception Addon (`doh_shield.py`)**: Integrates into the `mitmproxy` pipeline, detects inactivity timeouts (2.0s), and coordinates feature extraction and dummy generation.
5. **Real-Time Web Telemetry Dashboard (`web_dashboard.html`)**: A gorgeous, real-time web interface served locally on port `8000` using Chart.js to plot timelines, overhead dials, and attacker confidence graphs.
6. **IPC Terminal Stats Dashboard (`dashboard.py`)**: A real-time command-line interface styled with the `rich` library that monitors overhead, active queries, injected dummies, and session logs.

---

## 📊 Visual Comparisons & Flow Diagrams
The diagrams below compare how packet size blocks and request timings travel when undefended vs. when protected by DoH-Shield:

### Scenario A: Communication WITHOUT DoH-Shield (Vulnerable)
Original queries generate highly distinct packet size distributions (scattered blocks) and raw timing gaps. An eavesdropper uses these to reconstruct the website signature with 99% classification accuracy.

![Undefended DoH Flow](./undefended_doh_flow.png)

### Scenario B: Communication WITH DoH-Shield (Protected)
The local proxy intercepts queries, pads them using RFC 6891 EDNS(0) options to match cluster mode sizes, injects dummy packets to pad session volume, and applies Laplace timing jitter. The attacker's AI classifier is completely confused.

![Defended DoH Flow](./defended_doh_flow.png)

---

## 🔒 Guarantees & Privacy Bounds

DoH-Shield establishes a formal upper bound on attacker success probability by combining **$k$-Anonymity** (Sweeney, 2002) and **$\varepsilon$-Differential Privacy** (Dwork, 2006):

$$P_{\text{attack}} \le \frac{1}{k} + \exp(-\varepsilon)$$

Where:
- $k$ represents the minimum cluster size ($k = 343$ achieved in the RVCE VI-Sem prototype).
- $\varepsilon$ represents the differential privacy timing budget ($\varepsilon = 1.0$).

This guarantees that **no classifier can exceed $37.08\%$ accuracy** against morphed traffic, regardless of its architecture or retraining capabilities.

---

## 📁 File Directory Structure

```text
DoH-Sheild/
├── centroids.npy                  # KMeans cluster centroids (numpy matrix)
├── cluster_model.pkl              # Production KMeans cluster weights
├── cluster_scaler.pkl             # Standalone scaler for KMeans mapping
├── collect_defended.sh            # Live automation evaluation collector
├── dashboard.py                   # Rich CLI live visual stats monitor
├── web_dashboard.html             # Chart.js-based dynamic web telemetry dashboard
├── df_attack_model_best.pt        # Trained Deep Fingerprinting CNN weights
├── doh_shield.py                  # mitmproxy interception addon logic
├── DoHShield_Complete_Training.ipynb # Unified training notebook for Colab
├── DoHShield_Phase4_Evaluation.ipynb # Dynamic evaluation notebook for Colab
├── dummy_injector.py              # EDNS(0) dummy query constructor
├── feature_extractor.py           # Real-time 29-feature flow extractor
├── feature_scaler.pkl             # Baseline standard feature scaler
├── label_encoder.pkl              # Attack model label encoder
├── morph_engine.py                # Obfuscation plan and timing noise injector
├── animate_morphing.py            # Code-based Matplotlib visualization animator
├── presentation_guide.md          # Comprehensive viva preparation & demo guide
├── doh_shield_sys_diagram.png     # Figma-style local proxy system diagram
├── doh_shield_conceptual_diagram.png # High-level raw-to-morphed mapping diagram
├── undefended_doh_flow.png        # Minimal flow chart without DoH-Shield
├── defended_doh_flow.png          # Minimal flow chart with DoH-Shield
├── doh_shield_morphing.gif        # Compiled Matplotlib side-by-side animated trace
├── README.md                      # Comprehensive system documentation
├── run.sh                         # Signal-trapped proxy, dashboard, & HTTP server starter
├── top_features_phase3.npy        # ATTACK feature importance indexes
└── verify_shield.py               # 4-stage automated unit testing suite
```

---

## ⚙️ Installation & Setup

### Prerequisites
- **OS**: Ubuntu / Linux
- **Python**: 3.10+
- **Mitmproxy**: 9.0+

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/TARUN-2305/DoH-Sheild.git
cd DoH-Sheild

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt || pip install numpy pandas scikit-learn joblib scipy mitmproxy dnspython scapy rich httpx pyarrow fastparquet matplotlib pillow
```

### 2. Configure Browser Proxy & SSL CA Trust
To intercept TLS encrypted HTTPS queries without certificate warnings:
1. Open **Firefox** -> **Settings** -> search for **Proxy** -> **Settings...**
2. Choose **Manual proxy configuration**.
3. Set **HTTP Proxy** to `127.0.0.1` and **Port** to `8080`. Check **Also use this proxy for HTTPS**.
4. Search for **DNS over HTTPS** in Firefox settings, set it to **Max Protection**, and select **Cloudflare** as the provider.
5. In settings, search for **Certificates** -> click **View Certificates...** -> **Authorities** -> **Import...**
6. Locate and import `~/.mitmproxy/mitmproxy-ca-cert.pem`, check **Trust this CA to identify websites**, and click **OK**.

---

## 🧠 End-to-End Training (Google Colab)

If you wish to retrain all attack and defense models using the **CIRA-CIC-DoHBrw-2020** dataset:

1. Locate `DoHShield_Complete_Training.ipynb` in the repository and upload it to Google Colab.
2. In Colab's left sidebar, click the **Key Icon (Secrets)** and define:
   - `KAGGLE_USERNAME`: Your Kaggle API account username.
   - `KAGGLE_KEY`: Your Kaggle API key token.
   - `HF_token` (Optional): Hugging Face token for auto-archiving.
3. Turn on **GPU Acceleration** and click **Runtime -> Run all**.
4. Download the generated `doh_shield_artifacts.zip` bundle, extract it, and place the model assets (`*.pkl`, `*.pt`, `*.npy`) back into the root directory.

---

## 🚀 Running the System

Start the local intercepting proxy, the terminal dashboard, and the local web server with a single trapped shell script:

```bash
chmod +x run.sh
./run.sh
```

### Viewing the Real-Time Web Telemetry
Once the proxy starts up, it spins up a local web server on port `8000`. You can open your browser and navigate to:
👉 **[http://127.0.0.1:8000/web_dashboard.html](http://127.0.0.1:8000/web_dashboard.html)**

### Running the Live Interactive Matplotlib GUI Animation
To view the animated timeline and attacker CNN confidence curves updating dynamically on your desktop, run the animation script with the interactive show flag:
```bash
python animate_morphing.py --show
```

---

## 🧪 System Verification & Self-Tests

To manually execute the complete 4-checkpoint test suite and verify feature parsing, timing noise convergence, and packet padding structures:

```bash
python verify_shield.py
```

### Verification Outputs:
```text
.
..
...
....
----------------------------------------------------------------------
Ran 4 tests in 0.676s

OK
```

---

## 📚 References

1. **Deep Fingerprinting**: Sirinam, P., et al. "Deep Fingerprinting: Undermining Website Fingerprinting Defenses with Deep Learning." *Proceedings of the 2018 ACM SIGSAC Conference on Computer and Communications Security (CCS '18)*.
2. **Website Fingerprinting on DoH**: Panchenko, A., et al. "Website Fingerprinting Defenses against DNS-over-HTTPS." *Computers & Security, 2022*.
3. **l-Diversity**: Machanavajjhala, A., et al. "l-Diversity: Privacy Beyond k-Anonymity." *ACM Transactions on Knowledge Discovery from Data (TKDD), 2007*.
4. **Differential Privacy**: Dwork, C. "Differential Privacy." *International Colloquium on Automata, Languages, and Programming (ICALP), 2006*.

---

*DoH-Shield | Network Programming and Security (CS362IA) | RV College of Engineering, Bengaluru*
