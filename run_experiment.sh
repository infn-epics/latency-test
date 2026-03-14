#!/bin/bash
# Run all three latency test scenarios end-to-end
# This script orchestrates Kubernetes and bare-metal tests
#
# Prerequisites:
#   - kubectl configured and connected to the cluster
#   - EPICS Base compiled on both servers (for bare-metal scenario)
#   - Docker images built and pushed (for K8s scenarios)
#   - Python3 with pyepics, numpy, matplotlib installed on Server B (for bare-metal/external scenarios)
#
# Usage: ./run_experiment.sh <SERVER_A_HOSTNAME> <SERVER_B_HOSTNAME> <SERVER_A_IP>

set -euo pipefail

SERVER_A="${1:?Usage: $0 <SERVER_A_HOSTNAME> <SERVER_B_HOSTNAME> <SERVER_A_IP>}"
SERVER_B="${2:?Usage: $0 <SERVER_A_HOSTNAME> <SERVER_B_HOSTNAME> <SERVER_A_IP>}"
SERVER_A_IP="${3:?Usage: $0 <SERVER_A_HOSTNAME> <SERVER_B_HOSTNAME> <SERVER_A_IP>}"
ITERATIONS="${4:-1000}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================================"
echo "EPICS CA Latency Experiment"
echo "  Server A (IOC):    ${SERVER_A} (${SERVER_A_IP})"
echo "  Server B (Client): ${SERVER_B}"
echo "  Iterations:        ${ITERATIONS}"
echo "============================================================"
echo ""

mkdir -p "${SCRIPT_DIR}/results"

# ----------------------------------------------------------------
# Scenario 1: Kubernetes Pod-to-Pod
# ----------------------------------------------------------------
run_k8s_scenario() {
    echo "=== Scenario 1: Kubernetes Pod-to-Pod ==="

    # Patch manifests with actual hostnames
    sed "s/<SERVER_A_HOSTNAME>/${SERVER_A}/g" "${SCRIPT_DIR}/k8s/ioc-pod.yaml" | kubectl apply -f -
    echo "Waiting for IOC pod to be ready..."
    kubectl wait --for=condition=Ready pod/latency-ioc -n latency-test --timeout=120s

    # Deploy client pod
    sed -e "s/<SERVER_B_HOSTNAME>/${SERVER_B}/g" \
        -e "s/\"1000\"/\"${ITERATIONS}\"/g" \
        "${SCRIPT_DIR}/k8s/client-pod.yaml" | kubectl apply -f -

    echo "Waiting for client pod to complete..."
    kubectl wait --for=condition=Ready pod/latency-client -n latency-test --timeout=60s || true
    kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/latency-client -n latency-test --timeout=600s

    # Extract results
    echo "Extracting results..."
    kubectl cp latency-test/latency-client:/app/results/k8s-pod-to-pod_latency.csv \
        "${SCRIPT_DIR}/results/k8s-pod-to-pod_latency.csv"
    kubectl cp latency-test/latency-client:/app/results/k8s-pod-to-pod_stats.csv \
        "${SCRIPT_DIR}/results/k8s-pod-to-pod_stats.csv"

    echo "Scenario 1 complete."
    echo ""
}

# ----------------------------------------------------------------
# Scenario 2: Bare Metal (instructions only — must run manually)
# ----------------------------------------------------------------
print_bare_metal_instructions() {
    echo "=== Scenario 2: Bare Metal ==="
    echo ""
    echo "Run the following commands manually:"
    echo ""
    echo "--- Server A (IOC) ---"
    echo "  cd /path/to/epics-base && make -j\$(nproc)"
    echo "  cd ${SCRIPT_DIR}/ioc"
    echo "  /path/to/epics-base/bin/linux-x86_64/softIoc -d test.db"
    echo ""
    echo "--- Server B (Client) ---"
    echo "  export EPICS_CA_ADDR_LIST=\"${SERVER_A_IP}\""
    echo "  export EPICS_CA_AUTO_ADDR_LIST=NO"
    echo "  python3 ${SCRIPT_DIR}/client/latency_client.py \\"
    echo "    --iterations ${ITERATIONS} \\"
    echo "    --scenario bare-metal \\"
    echo "    --output ${SCRIPT_DIR}/results"
    echo ""
}

# ----------------------------------------------------------------
# Scenario 3: External Client → Kubernetes IOC
# ----------------------------------------------------------------
print_external_to_k8s_instructions() {
    echo "=== Scenario 3: External Client to Kubernetes IOC ==="
    echo ""
    echo "Ensure the IOC pod is running in Kubernetes (from Scenario 1)."
    echo "Find the NodePort assigned to the IOC service:"
    echo "  kubectl get svc latency-ioc -n latency-test"
    echo ""
    echo "Then on Server B (bare metal), run:"
    echo "  export EPICS_CA_ADDR_LIST=\"${SERVER_A_IP}\""
    echo "  export EPICS_CA_AUTO_ADDR_LIST=NO"
    echo "  export EPICS_CA_SERVER_PORT=<NodePort for ca-tcp>"
    echo "  python3 ${SCRIPT_DIR}/client/latency_client.py \\"
    echo "    --iterations ${ITERATIONS} \\"
    echo "    --scenario external-to-k8s \\"
    echo "    --output ${SCRIPT_DIR}/results"
    echo ""
}

# ----------------------------------------------------------------
# Main
# ----------------------------------------------------------------
run_k8s_scenario
print_bare_metal_instructions
print_external_to_k8s_instructions

echo "============================================================"
echo "After all scenarios complete, generate comparison report:"
echo "  python3 ${SCRIPT_DIR}/client/compare_results.py -d ${SCRIPT_DIR}/results"
echo "============================================================"
