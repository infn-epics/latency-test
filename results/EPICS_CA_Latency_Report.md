# EPICS Channel Access Latency Report

## Kubernetes CNI Impact on Control System Performance

**Date:** 14 March 2026
**Infrastructure:** INFN-LNF DAFNE Accelerator Complex — K8s Cluster (RKE2 v1.33.1)
**Servers:** plk8sdadom003 (192.168.108.14) ↔ plk8sdadom004 (192.168.108.15)
**Network:** Same L2 subnet (192.168.108.0/24), Gigabit Ethernet
**EPICS Version:** R7.0.8.1
**Iterations per test:** 1000

---

## 1. Experiment Design

The experiment measures the round-trip time (RTT) of an EPICS Channel Access set/readback cycle:

```
Client → caput TEST:SET → IOC forward link → caget TEST:READ → Client
```

Three deployment scenarios were tested:

| Scenario | IOC | Client | Network Path |
|---|---|---|---|
| **Bare Metal** (baseline) | Process on Server A | Process on Server B | Direct Ethernet |
| **K8s Pod-to-Pod** | Pod on Server A | Pod on Server B | K8s overlay network |
| **External → K8s IOC** | Pod on Server A | Process on Server B | Direct to Pod IP |

---

## 2. Measured Results

### Current CNI: Canal (Calico + Flannel VXLAN)

| Metric | Bare Metal | K8s Pod-to-Pod | External → K8s IOC |
|--------|-----------|---------------|-------------------|
| **Average RTT** | 0.622 ms | 2.193 ms (+253%) | 0.726 ms (+17%) |
| **Median RTT** | 0.623 ms | 1.301 ms (+109%) | 0.724 ms (+16%) |
| **Min RTT** | 0.405 ms | 0.889 ms | 0.534 ms |
| **Max RTT** | 3.133 ms | 33.808 ms | 1.110 ms |
| **Std Dev** | 0.099 ms | 4.455 ms | 0.070 ms |
| **P95** | 0.689 ms | 1.709 ms | 0.817 ms |
| **P99** | 0.874 ms | 28.550 ms | 0.906 ms |

### Key Observations

1. **Pod-to-Pod overhead is 3.5x** (average) over bare metal, rising to **32.6x at P99**
2. **External → K8s adds only 0.1 ms** — containerization itself has negligible impact
3. **The bottleneck is the overlay network**, not containerization
4. The P99 spike of 28.5 ms in Pod-to-Pod is unacceptable for real-time control loops

---

## 3. Current CNI Analysis: Canal (Calico + Flannel VXLAN)

### Architecture

```
Pod A (Server A)
  ↓ veth pair
cali* interface → Calico policy (iptables) → flannel.1 (VXLAN)
  ↓ VXLAN encapsulation (+50 bytes header)
Physical NIC (MTU 1500, effective payload MTU 1450)
  ↓ Ethernet
Physical NIC (Server B)
  ↓ VXLAN decapsulation
flannel.1 → Calico policy (iptables) → cali* interface
  ↓ veth pair
Pod B (Server B)
```

### Latency Sources

| Source | Impact | Description |
|--------|--------|-------------|
| VXLAN encap/decap | ~0.3–0.5 ms | 50-byte header wrapping (outer IP + UDP + VXLAN + inner Ethernet) |
| iptables traversal | ~0.1–0.3 ms | Calico network policy rules, conntrack table lookups |
| conntrack stalls | up to 30+ ms | Occasional hash table contention under conntrack (explains P99 spikes) |
| MTU reduction | Indirect | MTU 1450 vs 1500 — may cause fragmentation on larger payloads |
| Kernel softirq | Variable | VXLAN processing in kernel softirq context, susceptible to scheduling jitter |

---

## 4. CNI Alternatives — Expected Performance

The following analysis estimates Pod-to-Pod latency for each CNI option, based on the measured bare-metal baseline (0.622 ms) and the architectural overhead of each approach.

### 4.1 Calico — Direct Routing (No Encapsulation)

**Mode:** BGP with `ipipMode: Never`, `vxlanMode: Never`

```
Pod A → cali* → iptables → direct route → Physical NIC → Pod B
```

| Metric | Current (VXLAN) | Expected (Direct) | Improvement |
|--------|----------------|-------------------|-------------|
| Avg RTT | 2.193 ms | **0.75–0.90 ms** | ~60–65% |
| P99 RTT | 28.550 ms | **1.5–3.0 ms** | ~90% |
| Std Dev | 4.455 ms | **0.10–0.20 ms** | ~95% |

**Rationale:** Eliminates VXLAN encap/decap entirely. Still traverses iptables for network policy. Works on same-L2-subnet nodes without BGP peering. External→K8s result (0.726 ms) validates this estimate since that path already bypasses VXLAN.

**Prerequisites:** Nodes must be on the same L2 network (✓ confirmed: same /24 subnet).

**Migration effort:** Low — single IPPool patch:
```bash
kubectl patch ippools default-ipv4-ippool --type merge \
  -p '{"spec":{"vxlanMode":"Never","ipipMode":"Never"}}'
```

---

### 4.2 Calico — IPIP Mode

**Mode:** IP-in-IP tunnel (`ipipMode: Always`, `vxlanMode: Never`)

```
Pod A → cali* → iptables → tunl0 (IPIP) → Physical NIC → Pod B
```

| Metric | Current (VXLAN) | Expected (IPIP) | Improvement |
|--------|----------------|-----------------|-------------|
| Avg RTT | 2.193 ms | **1.0–1.4 ms** | ~40–55% |
| P99 RTT | 28.550 ms | **3.0–8.0 ms** | ~70–90% |
| Std Dev | 4.455 ms | **0.30–0.80 ms** | ~80% |

**Rationale:** IPIP adds only a 20-byte header (vs VXLAN's 50 bytes). Simpler kernel path, no UDP wrapping. Still traverses iptables. Conntrack spikes may still occur but are reduced.

**Migration effort:** Low — IPPool patch.

---

### 4.3 Calico — eBPF Dataplane

**Mode:** Calico with eBPF dataplane (replaces iptables/kube-proxy)

```
Pod A → cali* → eBPF programs (tc/XDP) → direct route → Physical NIC → Pod B
```

| Metric | Current (VXLAN) | Expected (eBPF) | Improvement |
|--------|----------------|-----------------|-------------|
| Avg RTT | 2.193 ms | **0.65–0.80 ms** | ~65–70% |
| P99 RTT | 28.550 ms | **1.0–2.0 ms** | ~93–96% |
| Std Dev | 4.455 ms | **0.08–0.15 ms** | ~97% |

**Rationale:** eBPF replaces iptables and conntrack with in-kernel BPF programs attached at the TC hook. Eliminates conntrack hash stalls (the main P99 spike source). Combined with direct routing, approaches bare-metal performance.

**Prerequisites:** Linux kernel ≥ 5.3 (✓ confirmed: 6.8.0). Requires disabling kube-proxy.

**Migration effort:** Medium — requires Calico operator reconfiguration and kube-proxy removal.

---

### 4.4 Cilium — Native Routing + eBPF

**Mode:** Full eBPF dataplane with native (direct) routing

```
Pod A → lxc* → eBPF (TC/XDP) → native route → Physical NIC → Pod B
```

| Metric | Current (VXLAN) | Expected (Cilium) | Improvement |
|--------|----------------|-------------------|-------------|
| Avg RTT | 2.193 ms | **0.63–0.75 ms** | ~66–71% |
| P99 RTT | 28.550 ms | **0.9–1.5 ms** | ~95–97% |
| Std Dev | 4.455 ms | **0.07–0.12 ms** | ~97% |

**Rationale:** Purpose-built eBPF dataplane. No iptables, no conntrack, no kube-proxy. Socket-level load balancing. With native routing on same-L2 nodes, achieves near-bare-metal latency. Best-in-class for latency-sensitive workloads.

**Prerequisites:** Linux kernel ≥ 5.10 recommended (✓). Full CNI replacement.

**Migration effort:** High — requires replacing Canal entirely, cluster-wide rollout, potential brief network disruption.

---

### 4.5 Cilium — VXLAN Mode (Default)

**Mode:** eBPF dataplane with VXLAN encapsulation

```
Pod A → lxc* → eBPF → cilium_vxlan → Physical NIC → Pod B
```

| Metric | Current (Canal VXLAN) | Expected (Cilium VXLAN) | Improvement |
|--------|----------------------|------------------------|-------------|
| Avg RTT | 2.193 ms | **0.85–1.10 ms** | ~50–60% |
| P99 RTT | 28.550 ms | **1.5–3.5 ms** | ~88–95% |
| Std Dev | 4.455 ms | **0.10–0.25 ms** | ~95% |

**Rationale:** Even with VXLAN, Cilium's eBPF path is faster than Canal's iptables path. eBPF handles encap/decap more efficiently than the flannel kernel module. No conntrack stalls.

**Migration effort:** High — full CNI swap.

---

### 4.6 Flannel — host-gw Mode

**Mode:** Direct routing via host gateway (no encapsulation)

```
Pod A → cni0 bridge → host route → Physical NIC → Pod B
```

| Metric | Current (VXLAN) | Expected (host-gw) | Improvement |
|--------|----------------|-------------------|-------------|
| Avg RTT | 2.193 ms | **0.80–1.00 ms** | ~55–63% |
| P99 RTT | 28.550 ms | **2.0–5.0 ms** | ~82–93% |
| Std Dev | 4.455 ms | **0.10–0.30 ms** | ~93% |

**Rationale:** No encapsulation overhead. However, Flannel uses basic iptables for masquerading and has no eBPF support. Less policy flexibility than Calico.

**Prerequisites:** Same L2 subnet required (✓).

**Migration effort:** Low — Flannel backend config change.

---

## 5. Comparison Summary

### Expected Average RTT by CNI

```
Bare Metal Baseline     ████████████  0.622 ms
                        
Cilium Native eBPF      █████████████  0.63–0.75 ms    (+1–21%)
Calico eBPF + Direct    █████████████  0.65–0.80 ms    (+5–29%)
Calico Direct Routing   ██████████████  0.75–0.90 ms    (+21–45%)
Flannel host-gw         ███████████████  0.80–1.00 ms    (+29–61%)
Cilium VXLAN eBPF       ████████████████  0.85–1.10 ms    (+37–77%)
Calico IPIP             ██████████████████  1.00–1.40 ms    (+61–125%)
Canal VXLAN (current)   ██████████████████████████████  2.19 ms    (+253%) ← YOU ARE HERE
```

### Expected P99 RTT by CNI

```
Bare Metal Baseline          █  0.874 ms
Cilium Native eBPF           █  0.9–1.5 ms
Calico eBPF + Direct         ██  1.0–2.0 ms
Calico Direct Routing        ██  1.5–3.0 ms
Flannel host-gw              ███  2.0–5.0 ms
Cilium VXLAN eBPF            ███  1.5–3.5 ms
Calico IPIP                  █████  3.0–8.0 ms
Canal VXLAN (current)        ████████████████████████████  28.55 ms  ← YOU ARE HERE
```

---

## 6. Recommendations

### For Accelerator Control Systems (Latency-Critical)

| Priority | Action | Expected Avg RTT | Effort |
|----------|--------|-----------------|--------|
| 🥇 **Quick win** | Calico direct routing (disable VXLAN) | ~0.80 ms | Low |
| 🥈 **Best performance** | Cilium native routing + eBPF | ~0.70 ms | High |
| 🥉 **Good balance** | Calico eBPF dataplane + direct routing | ~0.72 ms | Medium |

### Recommended Path

1. **Immediate:** Disable VXLAN on the existing Canal installation for same-subnet nodes. This is a single-command change and eliminates the dominant latency source.

2. **Medium-term:** Evaluate Calico eBPF dataplane to eliminate iptables and conntrack, removing the P99 spike source.

3. **Long-term:** If building a new cluster or during major upgrades, adopt Cilium with native routing for best-in-class latency.

---

## 7. Conclusion

The measured results demonstrate that **VXLAN overlay networking is the primary latency contributor** in Kubernetes-based EPICS deployments, not containerization itself. The External→K8s scenario (0.726 ms) proves that pods can achieve near-bare-metal performance when the overlay is bypassed.

For the INFN-LNF cluster, where IOC and client nodes share the same L2 subnet, **disabling VXLAN encapsulation is the highest-impact, lowest-risk optimization**, expected to reduce Pod-to-Pod latency from 2.2 ms to ~0.8 ms.

For sub-millisecond P99 guarantees required by accelerator feedback loops, an eBPF-based dataplane (Calico eBPF or Cilium) is recommended to eliminate iptables conntrack jitter.
