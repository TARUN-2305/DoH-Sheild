# Implementation Plan — DoH-Shield Phase 3 (Proxy Build)

We will build the **DoH-Shield local proxy** on the client machine to intercept DNS-over-HTTPS (DoH) traffic, extract real-time features, morph the traffic by injecting dummy requests to match a target cluster centroid, and apply Differential Privacy (DP) timing noise using the Laplace mechanism.

This plan outlines the architecture, components, and verification protocols for the 6 files comprising the Phase 3 implementation.

---

## User Review Required

> [!IMPORTANT]
> The proxy runs locally as a client-side interceptor. It uses `mitmproxy` to perform man-in-the-middle TLS interception for browser DoH requests to resolvers like `cloudflare-dns.com`. This requires trusting the mitmproxy CA certificate in the browser (Firefox) to operate correctly.

> [!WARNING]
> Since we do not have direct root access to bind to port 53 (standard DNS) or control browser processes natively, we will run the proxy on local port `8080` (as a standard HTTP/HTTPS proxy) or `8053` (as a dedicated DoH proxy endpoint) and route browser traffic through it.

---

## Open Questions

> [!NOTE]
> We will read the exact list of 29 features from `feature_names.npy` as soon as our environment installation completes, ensuring our `feature_extractor.py` implements the exact mathematical transformations used during Phase 1 training and Phase 2 clustering.

---

## Proposed Changes

We will create the local proxy structure under the workspace directory. The proxy consists of 6 components:

### DoH-Shield Proxy Components

#### [NEW] [feature_extractor.py](file:///home/tarun/Downloads/OneDrive_2026-05-30/New%20folder/feature_extractor.py)
Extracts all 29 statistical traffic features from live DoH flows in real-time. It accumulates packet timestamps, sizes, and directions (inbound vs. outbound) for a given flow/session, and computes statistical properties (mean, std dev, variance, mode, median, IAT percentiles, etc.) exactly matching the CIRA-CIC-DoHBrw-2020 feature representation.

#### [NEW] [morph_engine.py](file:///home/tarun/Downloads/OneDrive_2026-05-30/New%20folder/morph_engine.py)
Loads the offline trained models:
- `kmeans_clusterer.pkl` (reloaded as `cluster_model.pkl`)
- `cluster_scaler.pkl`
- `centroids.npy`

It implements:
1. **Cluster Assignment**: Scales raw features and maps the flow to its nearest K-Means cluster.
2. **Adaptive Session Randomization**: Deterministically offsets the target cluster ID using a session key to prevent attackers from learning a static target even with retraining.
3. **Morphing Plan**: Calculates the difference between the current flow metrics (e.g. packet counts, total bytes) and the target centroid's metrics, determining the exact number of dummy packets and their target sizes to inject.
4. **Differential Privacy Timing Noise**: Adds Laplace noise to inter-arrival timing gaps:
   $$\tilde{t}_j = t_j + \text{Lap}\left(\frac{\Delta t}{\varepsilon}\right)$$
   where $\Delta t$ is the timing sensitivity (typically $0.1$ seconds) and $\varepsilon$ is the privacy budget (default $\varepsilon = 1.0$).

#### [NEW] [dummy_injector.py](file:///home/tarun/Downloads/OneDrive_2026-05-30/New%20folder/dummy_injector.py)
Handles raw/async DNS-over-HTTPS request crafting using `dnspython` and `httpx`.
- Craft valid DNS query wire-formats (using harmless or non-existent domains that return `NXDOMAIN` to avoid polluting caches).
- Pad requests to target sizes (using EDNS(0) padding options or payload extension) to match the packet sizes specified in the morphing plan.
- Asynchronously inject queries with precise intervals noised by the DP module.

#### [NEW] [doh_shield.py](file:///home/tarun/Downloads/OneDrive_2026-05-30/New%20folder/doh_shield.py)
The core `mitmproxy` addon script.
- Intercepts HTTPS requests and responses destined for Cloudflare (`cloudflare-dns.com`) or Google DoH endpoints.
- Groups packets by browser session (using cookies, connection-state, or custom headers).
- Passes the captured packet trace to the feature extractor.
- Invokes the Morph Engine to get the morphing and timing plan.
- Triggers the Dummy Injector asynchronously to inject noised padding and dummy requests.

#### [NEW] [dashboard.py](file:///home/tarun/Downloads/OneDrive_2026-05-30/New%20folder/dashboard.py)
A visually stunning live terminal dashboard built with the `rich` library.
- Displays active sessions and flow captures.
- Shows real-time cluster assignments and distance to centroid.
- Displays injected dummy packet counts and bandwidth overhead percentage:
  $$\text{BW Overhead} = \frac{\text{Bytes(Dummies)}}{\text{Bytes(Original)}} \times 100\%$$
- Shows current formal privacy bounds ($P_{attack} \leq 1/l + e^{-\varepsilon}$).

#### [NEW] [run.sh](file:///home/tarun/Downloads/OneDrive_2026-05-30/New%20folder/run.sh)
A helper bash script that activates the virtual environment, performs self-tests/validation of the modules, and launches the `mitmdump` proxy alongside the dashboard.

---

## Verification Plan

### Automated Tests
We will build a self-contained unit test suite in `verify_shield.py` (which will be run by `run.sh` before startup) that:
1. Validates the `feature_extractor` on mock flow sequences.
2. Checks that `morph_engine` correctly loads the models and assigns clusters.
3. Verifies that the Laplace noise generator correctly fits the theoretical PDF.
4. Asserts that the dummy packet sizes match target sizes.

We will run:
```bash
./venv/bin/python -m unittest verify_shield.py
```

### Manual Verification
1. Run `./run.sh` to spin up the proxy on port `8080`.
2. Configure a test client (e.g. `curl` or browser proxy settings) to route DoH requests through the proxy.
3. Generate traffic by requesting domains.
4. Verify on the `dashboard.py` console that features are extracted, clusters are assigned, and dummies are successfully injected with noised latency.
5. Verify on Wireshark/tshark that dummy DNS-over-HTTPS packets are visible on the wire and conform to centroid sizes.
