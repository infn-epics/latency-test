# EPICS CA Latency Experiment

Reproducible round-trip latency measurement of EPICS Channel Access `caput`/`caget` operations across three deployment scenarios.

## Experiment Overview

```
client → caput TEST:SET → IOC processes → readback → client caget TEST:READ
```

The experiment measures the round-trip time (RTT) for 1000 iterations in each scenario, comparing EPICS performance under different networking conditions.

### Scenarios

| # | Scenario | IOC Location | Client Location | Networking |
|---|----------|-------------|-----------------|------------|
| 1 | **K8s Pod-to-Pod** | Pod on Server A | Pod on Server B | Kubernetes overlay |
| 2 | **Bare Metal** (baseline) | Process on Server A | Process on Server B | Direct Ethernet |
| 3 | **External → K8s IOC** | Pod on Server A | Process on Server B | NodePort / host network |

### Measured Metrics

- Average RTT (ms)
- Median RTT (ms)
- Min / Max RTT (ms)
- Standard Deviation
- 95th and 99th percentile
- Full time-series and histogram plots

## Project Structure

```
latency-test/
├── README.md                  # This file
├── run_experiment.sh          # Orchestration script
├── ioc/
│   ├── test.db                # EPICS test database
│   ├── st.cmd                 # IOC startup script
│   └── start.sh               # IOC launch wrapper
├── client/
│   ├── latency_client.py      # Python latency measurement client
│   ├── compare_results.py     # Cross-scenario comparison & plotting
│   └── requirements.txt       # Python dependencies
├── docker/
│   ├── Dockerfile.ioc         # IOC container image
│   ├── Dockerfile.client      # Client container image
│   └── build.sh               # Image build script
└── k8s/
    ├── ioc-pod.yaml           # IOC Pod + Service (Server A)
    └── client-pod.yaml        # Client Pod (Server B)
```

## Prerequisites

- Two Linux servers (Server A, Server B) connected via Ethernet
- Kubernetes cluster with both servers as nodes
- Docker (for building images)
- EPICS Base 7.0.8.1 (for bare-metal scenario)
- Python 3.10+ with `pyepics`, `numpy`, `matplotlib`

## Quick Start

### 1. Build and Push Docker Images

```bash
cd docker/
chmod +x build.sh
./build.sh ghcr.io/infn-epics

docker push ghcr.io/infn-epics/latency-test-ioc:latest
docker push ghcr.io/infn-epics/latency-test-client:latest
```

### 2. Configure Node Names

Find your Kubernetes node hostnames:

```bash
kubectl get nodes -o wide
```

Edit the YAML manifests to replace placeholders:
- `k8s/ioc-pod.yaml` → replace `<SERVER_A_HOSTNAME>`
- `k8s/client-pod.yaml` → replace `<SERVER_B_HOSTNAME>`

### 3. Run All Scenarios

```bash
chmod +x run_experiment.sh
./run_experiment.sh <SERVER_A_HOSTNAME> <SERVER_B_HOSTNAME> <SERVER_A_IP> [iterations]
```

Or run scenarios individually (see below).

---

## Scenario 1 — Kubernetes Pod-to-Pod

### Deploy IOC

```bash
# Edit k8s/ioc-pod.yaml: set <SERVER_A_HOSTNAME>
kubectl apply -f k8s/ioc-pod.yaml
kubectl wait --for=condition=Ready pod/latency-ioc -n latency-test --timeout=120s
```

### Deploy Client

```bash
# Edit k8s/client-pod.yaml: set <SERVER_B_HOSTNAME>
kubectl apply -f k8s/client-pod.yaml
```

### Monitor and Extract Results

```bash
kubectl logs -f latency-client -n latency-test
kubectl cp latency-test/latency-client:/app/results/ ./results/
```

### Cleanup

```bash
kubectl delete pod latency-client -n latency-test
# Keep IOC running for Scenario 3
```

---

## Scenario 2 — Bare Metal (Baseline)

### Compile EPICS Base on Both Servers

```bash
# On Server A and Server B:
cd /opt
git clone --branch R7.0.8.1 --depth 1 https://github.com/epics-base/epics-base.git
cd epics-base
make -j$(nproc)
export EPICS_BASE=/opt/epics-base
export PATH="${EPICS_BASE}/bin/linux-x86_64:${PATH}"
```

### Start IOC on Server A

```bash
cd /path/to/latency-test/ioc
softIoc -d test.db
```

### Run Client on Server B

```bash
cd /path/to/latency-test/client
pip install -r requirements.txt

export EPICS_CA_ADDR_LIST="<SERVER_A_IP>"
export EPICS_CA_AUTO_ADDR_LIST=NO

python3 latency_client.py \
    --iterations 1000 \
    --scenario bare-metal \
    --output ../results
```

---

## Scenario 3 — External Client → Kubernetes IOC

This scenario uses the IOC already deployed in Kubernetes from Scenario 1.

### Verify IOC is Running

```bash
kubectl get pods -n latency-test
kubectl get svc latency-ioc -n latency-test
```

Note the NodePort assigned to `ca-tcp` (e.g., `32064`).

### Run Client on Server B (Bare Metal)

```bash
export EPICS_CA_ADDR_LIST="<SERVER_A_IP>"
export EPICS_CA_AUTO_ADDR_LIST=NO
export EPICS_CA_SERVER_PORT=<NodePort>  # e.g., 32064

python3 latency_client.py \
    --iterations 1000 \
    --scenario external-to-k8s \
    --output ../results
```

---

## Data Analysis

After all scenarios are complete, generate the comparison report:

```bash
python3 client/compare_results.py --results-dir results/
```

### Output Files

| File | Description |
|------|-------------|
| `*_latency.csv` | Raw RTT measurements per scenario |
| `*_stats.csv` | Summary statistics per scenario |
| `*_histogram.png` | Latency distribution per scenario |
| `*_timeseries.png` | RTT over iterations per scenario |
| `comparison_histogram.png` | Overlay histogram of all scenarios |
| `comparison_boxplot.png` | Box plot comparison |
| `comparison_bar.png` | Average latency bar chart |
| `comparison_report.txt` | Text summary table |

### Expected Results Format

```
Scenario                    Avg RTT    Median       Min       Max    StdDev       P95       P99
Bare Metal                  X.XXX ms   X.XXX ms   X.XXX ms  X.XXX ms  X.XXX ms  X.XXX ms  X.XXX ms
K8s Pod-to-Pod              X.XXX ms   X.XXX ms   X.XXX ms  X.XXX ms  X.XXX ms  X.XXX ms  X.XXX ms
External → K8s IOC          X.XXX ms   X.XXX ms   X.XXX ms  X.XXX ms  X.XXX ms  X.XXX ms  X.XXX ms
```

## EPICS Test Database

The minimal IOC uses two records linked by `FLNK`:

```
record(ao, "TEST:SET") {         # Setpoint — written by client
    field(FLNK, "TEST:READ")     # Triggers readback update
}
record(ai, "TEST:READ") {        # Readback — read by client
    field(INP, "TEST:SET NPP")   # Copies value from TEST:SET
}
```

The forward link ensures `TEST:READ` updates immediately after `TEST:SET` is written, so the round-trip measures the full caput → process → caget path.

## Cleanup

```bash
kubectl delete namespace latency-test
```
