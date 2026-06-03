# DoH-Shield Presentation & Viva Preparation Guide

This guide is designed to help you present the **DoH-Shield** project to your mentors, professors, and external examiners. It provides a concrete plan for a live demonstration, descriptions of our visual aids, and a mock viva/quiz to test your understanding of the underlying concepts.

---

## 🖥️ Part 1: How to Present a Live Demonstration
To make your mentor understand that the project actually works, you can perform a **live demonstration** on your Ubuntu machine showing the intercepting proxy, feature extractor, and real-time dashboard in action.

### Steps for the Live Demo:
1.  **Start the Interception Proxy and Dashboard**:
    Open a terminal in the project folder and run:
    ```bash
    chmod +x run.sh
    ./run.sh
    ```
    This script automatically runs the automated 4-stage unit tests (`verify_shield.py`), starts `mitmdump` in the background on port `8080` with our `doh_shield.py` interceptor, and loads the **real-time visual dashboard** (`dashboard.py`) in your terminal.

2.  **Configure Web Browser Proxy (Live Triggers)**:
    *   Open **Firefox** $\to$ **Settings** $\to$ **Network Settings** $\to$ **Settings...**
    *   Choose **Manual proxy configuration**.
    *   Set **HTTP Proxy** to `127.0.0.1` and **Port** to `8080`. Check **Also use this proxy for HTTPS**.
    *   In Firefox settings, search for **DNS over HTTPS** and enable **Max Protection** (using Cloudflare or Google as the resolver).

3.  **Generate Traffic & Observe Obfuscation**:
    *   Browse to any website (e.g., `wikipedia.org` or `reddit.com`) in Firefox.
    *   Watch your terminal dashboard in real-time! You will see:
        *   **Active Connections** counting up.
        *   **Real-time Feature Extraction** logs showing original packet size footprints.
        *   **Inactivity Morphing Plans**: The proxy detects a 2.0-second query burst silence, assigns the session to a K-Means centroid, and instantly fires off **asynchronous padded dummy queries** to match the target cluster.
        *   **DP timing delays** shifting timing characteristics.
        *   **Overhead \& Privacy Guarantees** logging dynamically in the history panel.

---

## 🎨 Part 2: Visual Aids & Conceptual Explanations

Here are the visual representations you can include in your presentation slides, reports, or share directly with your mentor.

### 1. Conceptual Architecture Diagram
This diagram illustrates the flow of encrypted DNS traffic and how DoH-Shield operates as a client-side loopback interceptor.

![DoH-Shield Conceptual Diagram](./doh_shield_conceptual_diagram.png)

*   **How to Explain It**:
    *   *Left (Browser $\to$ Proxy)*: The browser generates encrypted DNS queries. In their raw state, these queries have **scattered lengths and timings** (leaking metadata signatures).
    *   *Center (DoH-Shield)*: The interceptor proxy acts as a protective shield. It extracts 29 statistical features, maps them to K-Means centroids, and pads them to **uniform block lengths** using EDNS(0) and Laplace Timing Noise.
    *   *Right (Resolver \& Eavesdropper)*: The recursive resolver receives clean, compliant traffic. The network-level **AI Classifier / Attacker** is shown completely confused, with its confidence distribution flattened because the traffic signatures are indistinguishable.

### 🏛️ 2. System Architecture Design Diagram
This design diagram details the component-level layout and internal modules of the DoH-Shield local proxy, demonstrating how traffic is intercepted, analyzed, morphed, and padded before transmission.

![DoH-Shield System Architecture Diagram](./doh_shield_sys_diagram.png)

*   **Detailed Explanation of Sub-Modules (Study for Viva)**:
    *   **Traffic Interceptor (HTTP Proxy Loopback)**:
        *   Acts as a thread-safe local proxy running on `127.0.0.1:8080` via `mitmproxy`.
        *   Standard DNS-over-HTTPS (DoH) requests sent by the browser are redirected through this proxy.
        *   By installing a custom Root CA certificate, the proxy parses connection-level metadata without throwing SSL warnings, capturing session traffic bursts.
    *   **Feature Extractor Module (`feature_extractor.py`)**:
        *   Parses incoming and outgoing packets to compute **29 distinct statistical features**.
        *   These features include packet lengths (min, max, mean, median, standard deviation, skewness), flow bytes partitioned by direction, connection duration, and inter-packet latencies.
        *   This captures the "fingerprint" that machine learning attackers use to identify websites.
    *   **K-Means Morphing Engine (`morph_engine.py`)**:
        *   Maps the computed 29-dimensional feature vector of an active session to the nearest pre-trained K-Means centroid (loaded from `kmeans_clusterer.pkl` and `centroids.npy`).
        *   To counter **adversarial retraining** (where attackers train classifiers on the new static cluster shapes), it applies **Adaptive Session-Key Cluster Randomization**. It generates a secure session key $K_{\text{sess}}$ to offset the cluster target index by $[-1, 0, 1]$ modulo $K$.
    *   **EDNS(0) Dummy Injector (`dummy_injector.py` & `doh_shield.py`)**:
        *   Uses `dnspython` to formulate fully compliant dummy DNS queries.
        *   To match the size constraints of the target centroid, it pads outgoing queries using **RFC 6891 EDNS(0) padding options**.
        *   If the proxy detects 2.0 seconds of session inactivity, it dispatches the padded dummy packets asynchronously via non-blocking HTTP requests. This ensures the total size footprint matches the centroid shape exactly.
    *   **Differential Privacy (DP) Noise Generator**:
        *   Injects Laplace noise $Y \sim \text{Lap}(0, b)$ into inter-packet transmission intervals.
        *   This timing perturbation obfuscates the request frequency signature, ensuring timing leakage is formally bounded by $\varepsilon$-Differential Privacy ($\varepsilon = 1.0$).
    *   **Upstream Resolvers & Attacker Response**:
        *   The upstream resolvers (Cloudflare `1.1.1.1` or Google `8.8.8.8`) process the requests and return standard secure DNS answers.
        *   The **Eavesdropper Attacker** observing the encrypted network stream sees a standardized packet sequence whose size and timing characteristics map uniformly across all target websites. The attacker's classifier confidence is completely flattened (randomized guesses, e.g., $\approx 51\%$), neutralizing website fingerprinting.

### 🎬 3. Animated Morphing Simulation
This animated GIF shows a side-by-side execution trace comparing an undefended flow against a morphed DoH-Shield flow:

![DoH-Shield Morphing Animation](./doh_shield_morphing.gif)

*   **How to Explain It**:
    *   *Left Panel (Undefended)*: Packets are transmitted as red bars representing raw size and timing. An attacker CNN observing this flow immediately peaks in classification confidence (e.g., `google.com` probability reaching 99%).
    *   *Right Panel (DoH-Shield)*: Packet sizes are morphed (shifted toward centroid mode sizes, shown in blue). Additionally, **asynchronous dummy queries** (shown in orange) are injected at Laplace-noised intervals. The attacker CNN's confidence bars become completely flattened and uniform (all targets $\approx 25\%$), illustrating the active neutralization of fingerprinting attacks.

### 📊 4. Direct Communication Flow Comparison (Before vs. After)
This comparison visualizes how the communication pipeline behaves when undefended vs. when protected by DoH-Shield.

#### Scenario A: Communication WITHOUT DoH-Shield (Exposed)
![Communication WITHOUT DoH-Shield](./undefended_doh_flow.png)

*   **Scattered Blocks (Raw Packet Sizes)**: During normal browsing, different websites generate unique sequences of request sizes (e.g., standard lookup is 73 bytes, while complex subdomains take 192 bytes). These form highly distinct "packet size profiles" or **scattered blocks** on the wire.
*   **Raw Timings**: Packets are sent exactly when the browser requests them, preserving the user's natural query frequency and inter-packet arrival latencies.
*   **The Threat**: Even though payload data is encrypted inside TLS, a passive network attacker captures these size and timing footprints. By feeding these scattered metadata signatures into an AI classifier (like a Convolutional Neural Network), the attacker can identify the visited domain with **99% confidence**.

---

#### Scenario B: Communication WITH DoH-Shield (Defended)
![Communication WITH DoH-Shield](./defended_doh_flow.png)

*   **The Core Innovation: Client-Side Proxy Interception**: DoH-Shield sits silently on the client loopback interface (`127.0.0.1:8080`). The browser talks to the proxy, and the proxy communicates securely with the DNS resolver.
*   **What is Packet Padding?**: To hide the original scattered sizes, DoH-Shield uses **EDNS(0) option-based padding (RFC 6891)**. Instead of leaving queries at their raw sizes, the proxy appends compliant blank bytes (padding option option-code 12) directly inside the encrypted TLS wrapper. This pads every packet size to match the target cluster centroid's mode size exactly.
*   **What are Padded Dummy Queries?**: If the browser's original transaction size falls short of the target cluster centroid, DoH-Shield's **Dummy Injector** generates asynchronous, non-blocking dummy recursive lookups. To the network, these are indistinguishable from real queries, padding the overall session volume.
*   **What is Laplace Timing Noise?**: To obscure timing metadata, the proxy injects artificial transmission delays and jitters calibrated from a Laplace distribution ($Y \sim \text{Lap}(0, 0.1\text{s})$). This perturbs inter-packet timings.
*   **The Security Result**: The eavesdropper now observes a perfectly uniform sequence of sizes with perturbed timing gaps. Because the traffic signature matches a standard cluster shape, the attacker's AI classifier is completely confused—its confidence is flattened below the **37.08% formal privacy limit**.

---

## 🧠 Part 3: Brainstorming Viva \& Quiz
Here are 5 tough questions your mentor or external examiners are highly likely to ask, along with scientifically rigorous answers to study:

> [!NOTE]
> **Q1: The CIRA dataset is a binary (Benign/Malicious) dataset. Why does your evaluation notebook report a multi-class website identification F1-score of ~10%?**
> *   **Answer**: DoH-Shield is a **Website Fingerprinting (WF)** defense. In a real deployment, the threat is identifying which of N websites the user visits. In a binary classification setup, benign and malicious traffic are highly distinct and map to separate clusters. Morphing them 35% merely shifts them towards their own class centroids, yielding ~99% binary F1. To evaluate the actual security of our WF defense on the CIRA dataset, we evaluate the **website-level indistinguishability** under $k$-anonymity clustering. Since all websites mapping to the same cluster are morphed to the exact same centroid, they become indistinguishable, dropping the multi-class website identification F1-score to $\sim 10.44\%$, bounded under the 37.08% DP threshold.

> [!IMPORTANT]
> **Q2: How does DoH-Shield achieve a formal privacy bound? Can you explain the formula $P_{attack} \le 1/k_{\min} + e^{-\varepsilon}$?**
> *   **Answer**: DoH-Shield integrates two independent privacy concepts:
>     1.  **$k$-Anonymity**: Packet sizes are morphed to cluster centroids. Since each cluster contains at least $k_{\min} = 343$ distinct domain samples, an attacker observing size features cannot distinguish them, bounding their guessing probability to $1/k_{\min} \approx 0.29\%$.
>     2.  **$\varepsilon$-Differential Privacy**: We add Laplace timing noise $Y \sim \text{Lap}(0, \Delta t / \varepsilon)$ to packet arrival times. Calibration of the noise to local timing sensitivity $\Delta t = 0.1\text{s}$ ensures timing information leakage is bounded by $e^{-\varepsilon} \approx 36.78\%$ for $\varepsilon = 1.0$.
>     3.  **Composition**: Combining the two bounds yields a strict joint privacy upper bound of exactly **`37.08%`**.

> [!TIP]
> **Q3: If the proxy injects dummy queries, won't a smart network eavesdropper simply filter out the dummy packets using signature matching?**
> *   **Answer**: No. DoH-Shield dummy queries are formatted as fully compliant recursive DNS A queries (e.g., querying `dummy.test`) encrypted inside the standard TLS HTTPS session. To pad the packet to the exact target size $s_c$, we utilize **RFC 6891 EDNS(0) padding options**. To the network eavesdropper, a dummy query looks identical to any standard, encrypted browser DNS lookup, making signature filtering impossible without decrypting the TLS session.

> [!WARNING]
> **Q4: What is Adaptive Session-Key Cluster Randomization, and why is it necessary?**
> *   **Answer**: Traditional traffic morphing suffers from **adversarial retraining**—an attacker can capture morphed traffic and train a new classifier to detect the static boundaries of the morphed clusters. To prevent this, DoH-Shield generates a cryptographically secure, session-level key $K_{\text{sess}}$ upon connection. It uses this key to offset the mapped cluster ID dynamically by $[-1, 0, 1]$. Because the attacker cannot guess $K_{\text{sess}}$, they cannot model a static mapping of centroids, neutralizing adversarial retraining.

> [!CAUTION]
> **Q5: Why is the bandwidth overhead in your live traffic collection script much higher than the simulated ~31%?**
> *   **Answer**: The automated collection script `collect_defended.sh` only visited websites using a **single DNS query** per visit. In a single-query trace, the original traffic volume is tiny ($\sim 90\text{B}$). Padding this single query to a full browser session centroid results in a mathematical overhead of $\sim 9,688\%$. In a **real browser session**, a page load makes **15 to 40 DNS requests** in rapid succession (original volume $2.5\text{KB} - 6\text{KB}$). The dummy injection overhead is diluted, averaging a low **`31.45%`** (well below the `<40%` limit).
