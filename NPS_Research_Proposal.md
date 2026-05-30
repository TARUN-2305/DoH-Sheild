# DoH-Shield: Adaptive DNS-over-HTTPS Traffic Morphing for Website Fingerprinting Resistance

**Course:** CS362IA — Network Programming and Security  
**Category:** Professional Core Course | Semester VI  
**Institution:** RV College of Engineering, Bengaluru

---

## 1. The Problem

### What is happening under the hood

When you visit a website, your browser must first resolve the domain name to an IP address via DNS. Traditionally, this DNS query is **plaintext** — your ISP, network admin, or any passive eavesdropper on the path can see exactly which domain you queried, even if the subsequent HTTPS traffic is encrypted.

**DNS-over-HTTPS (DoH)** was introduced (RFC 8484, 2018) to fix this: it tunnels DNS queries inside encrypted HTTPS connections. Major browsers (Chrome, Firefox, Edge) and resolvers (Cloudflare 1.1.1.1, Google 8.8.8.8) have widely adopted it.

### The Illusion of Privacy

The problem is that **DoH encrypts the content but not the behavioral fingerprint**. Each website causes a characteristic *pattern* of DNS sub-queries — unique counts of queries, response sizes, inter-query timing gaps, and query bursts — that together act like a fingerprint. An attacker (ISP, network monitor, nation-state) observing only the *metadata* of encrypted DoH flows can still identify which website you are visiting with **>95% accuracy** using machine learning, even without decrypting a single byte.

> This is the **Website Fingerprinting (WF) attack on DoH traffic** — a well-documented, actively exploited privacy threat, and the central open problem this project addresses.

### The Existing Defense Gap

| Defense Type | Example | Problem |
|---|---|---|
| RFC 8467 Padding | EDNS(0) padding | Attacker still achieves >95% accuracy |
| Traffic obfuscation (add dummies) | FRONT, WTF-PAD | Adaptive attackers retrain and recover accuracy; high overhead |
| Supersequence morphing | Tamaraw | Provably secure but >200% bandwidth overhead — impractical |
| Client-side obfuscation | Panchenko et al. 2022 | Reduces attacker to ~9%, but overhead not formally bounded |
| Backdoor poisoning | TrapFlow (2024) | Requires attacker to download a poisoned model — strong assumption |

**The open research gap:** No existing defense simultaneously satisfies:
1. Low bandwidth overhead (<40%)
2. Low latency overhead (<20ms)
3. Formally bounded attacker accuracy (provable security, not just empirical)
4. Works against **adaptive adversaries** who retrain on defended traffic
5. Deployable purely on the **client side** (no server cooperation needed)

This project builds **DoH-Shield** — a system targeting all five.

---

## 2. The Idea: DoH-Shield

### Core Concept

DoH-Shield is a **lightweight, adaptive traffic morphing proxy** that sits between the browser's DoH client and the resolver. It reshapes the observable DoH footprint of a website visit by:

1. **Cluster-aware morphing** — offline, cluster the DoH fingerprints of the top-N websites into groups based on behavioral similarity. Websites in the same cluster already look alike to an attacker.

2. **Targeted dummy injection** — instead of blindly padding all traffic, inject dummy queries *only at semantically sensitive positions* (identified by an attention-based classifier), morphing the current trace to match the centroid of its assigned cluster.

3. **Differential Privacy Noise Layer** — add calibrated Laplace noise to inter-query timing gaps to provide a formal (ε, δ)-DP privacy guarantee, mathematically bounding the attacker's ability to distinguish between sites in the same cluster.

4. **Adaptive Randomization** — randomly reassign cluster membership at each session using a secret key, preventing the attacker from learning a stable target even with retraining.

### Why This is Novel

- Existing work that achieves provable security (Tamaraw, Adaptive Tamaraw 2025) does so at extremely high overhead by morphing all traffic to a fixed supersequence.
- DoH-Shield uses **clustering + differential privacy** together — clustering reduces the "search space" the attacker faces, while DP-noise provides a formal information-theoretic bound *within* each cluster, at a fraction of Tamaraw's overhead.
- The combination of cluster-aware morphing + DP-timing noise + adaptive randomized assignment is **not present in any published work**.

---

## 3. How It Fits the Syllabus

This project directly exercises core curriculum topics:

| NPS Unit | Concept Used in Project |
|---|---|
| Unit I — Transport Layer & Sockets | Raw UDP/TCP socket capture of DoH flows, byte ordering |
| Unit II — TCP client/server | Proxy server intercepting browser's DoH TCP connections |
| Unit III — UDP & DNS / Name Server | DNS query parsing, recvfrom/sendto, getsockopt/setsockopt |
| Unit IV — Cryptosystems | RSA/ECDH for session key in adaptive cluster assignment; TLS analysis |
| Unit V — TLS & Wireless Security | DoH rides on TLS/HTTPS; HTTPS traffic analysis is the threat model |

---

## 4. Current State of Research

- <b>Attack side:</b> WF attacks on DoH achieve >95% F1-score (Panchenko et al., ESORICS 2024; Li et al., ESORICS 2024). HTTP/2 Key Frame Sequences now defeat padding-only defenses (Li et al., ESORICS 2025).
- <b>Defense side:</b> Adaptive Tamaraw (Khajavi & Wang, arXiv Sep 2025) is the current SOTA with formal bounds but 180–220% bandwidth overhead. RLpatch (IEEE 2025) uses RL to reduce overhead but has no formal guarantees. TrapFlow (2024) assumes attacker downloads a poisoned model.
- <b>Gap confirmed:</b> No published system achieves <40% overhead with formal (ε, δ)-DP bounds against adaptive adversaries on DoH specifically (most work targets Tor).

---

## 5. System Architecture

```
Browser (DoH enabled)
        |
        v
  [DoH-Shield Proxy]  ← runs locally on port 5353
        |
   ┌────────────────────────────────────────┐
   │  1. Capture DoH flow (TCP socket)      │
   │  2. Feature extractor                  │
   │     (query count, sizes, timing gaps)  │
   │  3. Cluster classifier (lightweight    │
   │     attention model, offline trained)  │
   │  4. Morph engine                       │
   │     - Dummy query injector             │
   │     - DP-Laplace timing noise          │
   │     - Session-key cluster reassigner   │
   │  5. Forward morphed flow to resolver   │
   └────────────────────────────────────────┘
        |
        v
  Cloudflare / Google DoH Resolver
```

**Implementation stack:** Python (asyncio, socket), mitmproxy for TLS interception, scikit-learn/PyTorch for the offline cluster model, dnspython for query parsing.

---

## 6. Mathematical Formulation

Let $F(w)$ denote the DoH traffic trace (feature vector) for website $w$.

**Clustering:** Partition websites $W$ into $k$ clusters $C_1, \ldots, C_k$ using k-means on $F(w)$. Each cluster has centroid $\mu_i$.

**Morphing:** Given observed trace $F(w)$ assigned to cluster $C_i$, inject dummy queries $\Delta$ such that $F(w) + \Delta \approx \mu_i + \mathcal{N}(0, \sigma^2)$.

**Differential Privacy on timing:** Let $t_j$ be the $j$-th inter-query gap. Publish $\tilde{t}_j = t_j + \text{Lap}(\Delta t / \varepsilon)$ where $\Delta t$ is the sensitivity. This satisfies $\varepsilon$-DP per query, and by composition, the full trace is $(\varepsilon \cdot |T|, \delta)$-DP.

**Attacker accuracy upper bound:** Within a cluster of size $|C_i|$ with $l$-diversity $\geq l$, the attacker's maximum success probability is bounded by:

$$P_{attack} \leq \frac{1}{l} + \exp(-\varepsilon)$$

This bound is **formally provable** and independent of the attacker's model.

**Overhead metric:**

$$\text{BW Overhead} = \frac{\sum|\Delta|}{|F(w)|} \times 100\%$$

Target: $< 40\%$ overhead with $P_{attack} < 15\%$ against adaptive adversaries.

---

## 7. Evaluation Plan

### Datasets
- Collect DoH traces for top-1000 Alexa/Tranco websites using Cloudflare and Google resolvers (20 samples/site, replicated over 2 weeks — following standard WF protocol).

### Attacks to Evaluate Against
| Attack | Why |
|---|---|
| Random Forest (153 features) | Baseline (Panchenko 2022 SOTA) |
| Deep Fingerprinting (CNN) | Standard DL-based WF attack |
| LASERBEAK (Transformer) | Current SOTA DL attack (2024) |
| Adaptive adversary | Attacker retrains on defended traces |

### Metrics
- Attacker accuracy (closed-world and open-world)
- Bandwidth overhead (%)
- Latency overhead (ms)
- Formal DP parameter ε

### Comparison Table (Expected Results)

| Defense | Attack Acc | BW Overhead | Formal Bound |
|---|---|---|---|
| RFC 8467 Padding (baseline) | ~95% | ~5% | No |
| Panchenko Obfuscation (2022) | ~9% | ~80% | No |
| Adaptive Tamaraw (2025) | ~8% | ~200% | Yes |
| **DoH-Shield (ours)** | **<15%** | **<40%** | **Yes** |

---

## 8. Expected Deliverables

1. **Working prototype** — Python-based local DoH proxy with morphing engine (runnable, tested against real resolvers).
2. **Dataset** — DoH traffic traces for 1000 websites (publicly releasable).
3. **Evaluation results** — Benchmark against 4 SOTA attacks with statistical significance.
4. **Formal proof** — Mathematical derivation of the DP-based attacker accuracy bound.
5. **Paper draft** — Targeting IEEE Networking Letters, NDSS Workshop on DNS Privacy, or ACM CCS Poster track (all accept student-first-author submissions).

---

## 9. Timeline (12 Weeks)

| Week | Milestone |
|---|---|
| 1–2 | Literature review finalization; set up DoH proxy skeleton (socket layer) |
| 3–4 | Data collection pipeline (1000 sites × 20 samples) |
| 5–6 | Feature extraction + clustering model (offline training) |
| 7–8 | Dummy injection engine + DP timing noise layer |
| 9–10 | Evaluation against 4 attacks; overhead measurement |
| 11 | Formal proof write-up; comparison table |
| 12 | Paper draft + code cleanup + submission |

---

## 10. Why This Project Satisfies All Conditions

| Condition | How DoH-Shield Satisfies It |
|---|---|
| Solves a real problem | DNS privacy is a real, actively exploited threat; affects every internet user |
| High implementational value | Working proxy, deployable today in any DoH-capable browser |
| Highly novel | No published work combines cluster morphing + DP timing bounds for DoH specifically |
| Research-continuation ready | Directly extends Adaptive Tamaraw (2025) and Panchenko (2022); citable gap |
| Publishable | Clear novel contribution, formal guarantee, standard evaluation protocol |
| Mathematically comparable | Formal DP bound + overhead metrics directly compare to all related work |
| Mathematically superior | Formal proof of <15% attacker accuracy at <40% overhead vs. 200% in SOTA |
| Not overkill | Python proxy + lightweight ML; no exotic hardware, no server-side changes |

---

*Prepared for CS362IA — Network Programming and Security, Semester VI, RV College of Engineering.*
