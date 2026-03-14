#!/bin/bash
# Build Docker images for the latency test
# Usage: ./build.sh [registry]
#
# Example:
#   ./build.sh ghcr.io/infn-epics

set -euo pipefail

REGISTRY="${1:-ghcr.io/infn-epics}"
TAG="${2:-latest}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Building latency test images..."
echo "  Registry: ${REGISTRY}"
echo "  Tag:      ${TAG}"
echo ""

PLATFORM="linux/amd64"

# Build IOC image
echo "=== Building IOC image (${PLATFORM}) ==="
docker buildx build \
    --platform "${PLATFORM}" \
    -f "${SCRIPT_DIR}/Dockerfile.ioc" \
    -t "${REGISTRY}/latency-test-ioc:${TAG}" \
    --load \
    "${PROJECT_DIR}"

echo ""

# Build Client image
echo "=== Building Client image (${PLATFORM}) ==="
docker buildx build \
    --platform "${PLATFORM}" \
    -f "${SCRIPT_DIR}/Dockerfile.client" \
    -t "${REGISTRY}/latency-test-client:${TAG}" \
    --load \
    "${PROJECT_DIR}"

echo ""
echo "Images built:"
echo "  ${REGISTRY}/latency-test-ioc:${TAG}"
echo "  ${REGISTRY}/latency-test-client:${TAG}"
echo ""
echo "Push with:"
echo "  docker push ${REGISTRY}/latency-test-ioc:${TAG}"
echo "  docker push ${REGISTRY}/latency-test-client:${TAG}"
