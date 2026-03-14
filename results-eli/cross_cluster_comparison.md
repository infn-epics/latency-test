# Cross-Cluster EPICS CA Latency Comparison

## ELI-NP Cluster Inventory

### Kubernetes

| Property | Value |
|----------|-------|
| **Distribution** | kubeadm |
| **K8s Version** | v1.30.13 |
| **Container Runtime** | containerd 1.7.20 (worker), 2.2.0 (control-plane) |
| **CNI** | Calico v3.27.0 (vxlanMode: CrossSubnet, ipipMode: Never) |
| **Pod CIDR** | 10.244.0.0/16 |
| **Node Subnet** | 10.16.4.0/24 (all nodes same L2, → Calico uses direct routing) |

### Nodes

| Node | Role | IP | CPU | Cores/Threads | RAM | OS |
|------|------|----|-----|---------------|-----|-----|
| plelinpdom001 | control-plane | 10.16.4.99 | AMD EPYC 7402 (1S) | 24C/48T | 125 GiB | AlmaLinux 9.6 |
| plelinpdom002 | worker | 10.16.4.86 | AMD EPYC 7402 (1S) | 24C/48T | 125 GiB | AlmaLinux 9.6 |
| **plelinpdom003** | **worker (Server A)** | **10.16.4.87** | AMD EPYC 7402 (1S) | 24C/48T | 125 GiB | AlmaLinux 9.6 |
| **plelinpdom004** | **worker (Server B)** | **10.16.4.96** | AMD EPYC 7402 (1S) | 24C/48T | 125 GiB | AlmaLinux 9.6 |
| plelinpdom005 | control-plane | 10.16.4.97 | Intel Xeon Gold 5416S (2S) | 32C/64T | 251 GiB | AlmaLinux 9.6 |
| plelinpdom006 | control-plane | 10.16.4.95 | Intel Xeon Gold 5416S (2S) | 32C/64T | 251 GiB | AlmaLinux 9.6 |

### Network

| Property | Value |
|----------|-------|
| **NIC (workers/dom001)** | Intel XL710 4×10GbE (i40e driver) |
| **NIC (dom005/006)** | Intel XL710 2×10GbE (i40e) + Intel I350 2×1GbE (igb) |
| **Active Link Speed** | 10 Gbps |
| **Kernel** | 5.14.0-570.x.el9_6.x86_64 |

---

## LNF/DAFNE Cluster Inventory

### Kubernetes

| Property | Value |
|----------|-------|
| **Distribution** | RKE2 v1.33.1+rke2r1 |
| **K8s Version** | v1.33.1 |
| **Container Runtime** | containerd 2.0.5-k3s1 |
| **CNI** | Canal (Calico v3.30.0 policy + Flannel v0.26.7 VXLAN) with Multus |
| **Flannel Backend** | VXLAN (MTU 1450) |
| **Pod CIDR** | 10.42.0.0/16 (Flannel), 192.168.0.0/16 (Calico IPPool) |
| **Node Subnets** | 192.168.108.0/24 + 192.168.109.0/24 + 10.10.6.0/24 (multi-subnet) |

### Nodes

| Node | Role | IP | CPU | Cores/Threads | RAM | OS |
|------|------|----|-----|---------------|-----|-----|
| kube-chaos01 | CP, etcd, master | 10.10.6.18 | AMD EPYC 7282 (2S) | 32C/64T | 125 GiB | Rocky Linux 9.6 |
| kube-chaos02 | CP, etcd, master | 10.10.6.68 | AMD EPYC 7282 (2S) | 32C/64T | 125 GiB | Rocky Linux 9.6 |
| kube-chaos04 | worker | 10.10.6.80 | AMD EPYC 7282 (2S) | 32C/64T | 125 GiB | Rocky Linux 9.6 |
| plk8sdadom001 | worker | 192.168.108.10 | AMD EPYC 9754 (1S) | 128C/256T | 188 GiB | Ubuntu 24.04.3 |
| plk8sdadom002 | CP, etcd, master | 192.168.108.13 | AMD EPYC 7282 (2S) | 32C/64T | 126 GiB | Ubuntu 24.04.3 |
| **plk8sdadom003** | **worker (Server A)** | **192.168.108.14** | **AMD EPYC 7282 (2S)** | **32C/64T** | **252 GiB** | **Ubuntu 24.04.4** |
| **plk8sdadom004** | **worker (Server B)** | **192.168.108.15** | **AMD EPYC 7282 (1S)** | **16C/32T** | **126 GiB** | **Ubuntu 24.04.4** |
| plk8sdactrl001 | worker | 192.168.108.22 | Intel i7-13700 (1S) | 16C/24T | 62 GiB | Ubuntu 24.04.3 |
| plk8sdactrl002 | worker (NotReady) | 192.168.108.23 | Intel i7-13700 (1S) | 16C/24T | 62 GiB | Ubuntu 24.04.3 |
| plk8sdactrl003 | worker | 192.168.108.24 | Intel i7-13700 (1S) | 16C/24T | 62 GiB | Ubuntu 24.04.3 |
| plk8sdagpu001 | worker | 192.168.108.70 | AMD EPYC 7313 (1S) | 16C/32T | 63 GiB | Ubuntu 24.04.3 |
| plsparcdom001 | CP, etcd, master | 192.168.109.100 | AMD EPYC 7282 (2S) | 32C/64T | 251 GiB | AlmaLinux 9.6 |
| plsparcdom004 | worker | 192.168.109.106 | AMD EPYC 7282 (2S) | 32C/64T | 251 GiB | AlmaLinux 9.6 |
| plsparcgige001 | worker | 192.168.108.11 | Intel i7-7700 (1S) | 4C/8T | 31 GiB | Ubuntu 24.04.3 |

### Network

| Property | Value |
|----------|-------|
| **NIC (dom/chaos/sparc nodes)** | Intel X710 4×10GbE SFP+ (i40e driver), bonded |
| **NIC (dom001)** | Broadcom BCM57414 2×10/25GbE RDMA (bnxt_en), bonded |
| **NIC (ctrl nodes)** | Intel I219-LM 1GbE (e1000e) + Realtek RTL8111 1GbE |
| **NIC (gpu001)** | Intel X710 4×10GbE SFP+ (i40e) |
| **NIC (sparcgige001)** | Intel 82599ES 2×10GbE SFI/SFP+ (ixgbe) |
| **Active Link Speed** | 10 Gbps (server nodes), 1 Gbps (ctrl nodes) |
| **Kernel (Ubuntu)** | 6.8.0-86..101 |
| **Kernel (Rocky/Alma)** | 5.14.0-570.x.el9_6 |
| **GPU** | NVIDIA A2/A16 (plk8sdagpu001) |

---

## Cluster Configurations Summary

| Property | DAFNE/LNF | ELI-NP |
|----------|-----------|--------|
| **K8s Distribution** | RKE2 v1.33.1 | kubeadm v1.30.13 |
| **CNI** | Canal (Calico + Flannel VXLAN) | Calico v3.27.0 (vxlanMode: CrossSubnet) |
| **Flannel Backend** | VXLAN (all traffic encapsulated) | N/A (pure Calico, direct routing same-subnet) |
| **Nodes** | 14 (multi-subnet, heterogeneous) | 6 (single subnet, 2 HW classes) |
| **Server A** | plk8sdadom003 (192.168.108.14) | plelinpdom003 (10.16.4.87) |
| **Server B** | plk8sdadom004 (192.168.108.15) | plelinpdom004 (10.16.4.96) |
| **CPU (test nodes)** | AMD EPYC 7282 16C @2.8GHz | AMD EPYC 7402 24C @2.8GHz |
| **NIC (test nodes)** | Intel X710 10GbE (i40e), bonded | Intel XL710 10GbE (i40e) |
| **Subnet** | Same /24 (192.168.108.x) | Same /24 (10.16.4.x) |
| **OS (test nodes)** | Ubuntu 24.04.4 | AlmaLinux 9.6 |
| **EPICS Base** | R7.0.8.1 | R7.0.8.1 |

## Results Comparison (all values in ms)

### Scenario 1: K8s Pod-to-Pod

| Metric | DAFNE (Canal/VXLAN) | ELI-NP (Calico) | Improvement |
|--------|---------------------|------------------|-------------|
| **Average** | 2.193 | 0.702 | **3.12x faster** |
| **Median** | 1.301 | 0.539 | **2.41x faster** |
| **P99** | 28.550 | 0.815 | **35x faster** |
| **Min** | 0.889 | 0.435 | 2.04x faster |
| **Max** | 33.808 | 31.689 | 1.07x |
| **StdDev** | 4.455 | 2.033 | 2.19x lower |

### Scenario 2: Bare Metal

| Metric | DAFNE | ELI-NP | Improvement |
|--------|-------|--------|-------------|
| **Average** | 0.622 | 0.383 | **1.62x faster** |
| **Median** | 0.623 | 0.361 | **1.73x faster** |
| **P99** | 0.874 | 0.471 | 1.86x faster |
| **Min** | 0.405 | 0.307 | 1.32x faster |
| **Max** | 3.133 | 1.001 | 3.13x |
| **StdDev** | 0.099 | 0.048 | 2.06x lower |

### Scenario 3: External → K8s IOC

| Metric | DAFNE (Canal/VXLAN) | ELI-NP (Calico) | Improvement |
|--------|---------------------|------------------|-------------|
| **Average** | 0.726 | 0.455 | **1.60x faster** |
| **Median** | 0.724 | 0.447 | **1.62x faster** |
| **P99** | 0.906 | 0.592 | 1.53x faster |
| **Min** | 0.534 | 0.383 | 1.39x faster |
| **Max** | 1.110 | 1.668 | 0.67x (ELI outlier) |
| **StdDev** | 0.070 | 0.050 | 1.40x lower |

## K8s Overhead vs Bare Metal

| Cluster | K8s Pod-to-Pod Avg | Bare Metal Avg | **K8s Overhead** |
|---------|-------------------|----------------|------------------|
| **DAFNE (Canal/VXLAN)** | 2.193 ms | 0.622 ms | **+253%** (3.53x) |
| **ELI-NP (Calico)** | 0.702 ms | 0.383 ms | **+83%** (1.83x) |

## Key Findings

1. **CNI is the dominant factor in K8s latency.** The Canal VXLAN overlay adds 253% overhead vs bare metal, while Calico with direct routing (same-subnet) adds only 83%.

2. **ELI-NP hardware is faster overall.** Even bare metal shows 1.6x improvement, indicating better network hardware/configuration. However, the K8s Pod-to-Pod gap (3.12x) far exceeds the bare metal gap (1.62x), confirming CNI overhead as the primary differentiator.

3. **P99 latency is dramatically better with Calico.** DAFNE's P99 of 28.55ms vs ELI's 0.815ms (35x improvement) shows Canal/VXLAN produces severe tail latency spikes due to encapsulation/decapsulation overhead.

4. **External→K8s is close to bare metal on both clusters.** This confirms that CA traffic entering a pod traverses minimal CNI overhead when the client directly addresses the pod IP — the bottleneck is pod-to-pod overlay routing, not the pod network stack itself.

5. **Calico CrossSubnet with same-subnet nodes = near-native performance.** Since all ELI nodes share the 10.16.4.x/24 subnet, Calico uses direct routing (no VXLAN), delivering K8s latency only 83% above bare metal.

## Recommendation

For EPICS control systems on Kubernetes, **Calico with direct routing (or CrossSubnet mode)** should be the preferred CNI. The Canal (Flannel VXLAN) overlay introduces unacceptable latency overhead (253%) and severe P99 tail latency for real-time control applications.

If nodes share a L2 subnet, Calico's direct routing eliminates encapsulation entirely. For cross-subnet traffic, `ipipMode: CrossSubnet` adds minimal overhead compared to VXLAN.
