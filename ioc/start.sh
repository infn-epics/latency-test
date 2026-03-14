#!/bin/bash
# Start the latency test IOC
# Usage: ./start.sh [path_to_epics_base]

EPICS_BASE="${1:-/epics/base}"

if [ ! -f "${EPICS_BASE}/bin/linux-x86_64/softIoc" ]; then
    echo "ERROR: softIoc not found at ${EPICS_BASE}/bin/linux-x86_64/softIoc"
    echo "Usage: $0 [path_to_epics_base]"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

export EPICS_CA_ADDR_LIST="0.0.0.0"
export EPICS_CAS_INTF_ADDR_LIST="0.0.0.0"
export EPICS_CA_AUTO_ADDR_LIST="YES"
export EPICS_CA_SERVER_PORT="${EPICS_CA_SERVER_PORT:-5064}"
export EPICS_CA_REPEATER_PORT="${EPICS_CA_REPEATER_PORT:-5065}"

cd "${SCRIPT_DIR}"

echo "Starting latency test IOC..."
echo "  EPICS_CA_SERVER_PORT=${EPICS_CA_SERVER_PORT}"
echo "  EPICS_CA_REPEATER_PORT=${EPICS_CA_REPEATER_PORT}"

# Use tail to keep stdin open so softIoc doesn't exit on EOF in containers
tail -f /dev/null | "${EPICS_BASE}/bin/linux-x86_64/softIoc" -d test.db
