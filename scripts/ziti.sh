#!/bin/bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ZITI_PWD=${ZITI_PWD:-"admin123"}
ZITI_CTRL_PORT=${ZITI_CTRL_PORT:-80}
ZITI_ROUTER_PORT=${ZITI_ROUTER_PORT:-3022}

# Directories
WORK_DIR=$(pwd)
ZITI_HOME="${WORK_DIR}/.ziti-home"

# Function to print status
print_status() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

echo -e "${BLUE}=== Setting up Ziti Controller ===${NC}"
echo -e "${YELLOW}Ziti Controller Port: ${ZITI_CTRL_PORT}${NC}"
echo -e "${YELLOW}Ziti Router Port: ${ZITI_ROUTER_PORT}${NC}"
echo -e "${YELLOW}Ziti Home: ${ZITI_HOME}${NC}"
echo ""

# Check if ziti CLI is available
if ! command -v ziti >/dev/null 2>&1; then
    print_error "ziti CLI not found."
    exit 1
fi

# Create directory
if [ ! -d "${ZITI_HOME}" ]; then
    mkdir -p "${ZITI_HOME}"
    print_status "Directory created"
fi

# Initialize Ziti Quickstart if it doesn't exist
print_info "Starting Ziti Quickstart..."
ziti edge quickstart \
    --home "${ZITI_HOME}/quickstart" \
    --password "${ZITI_PWD}" \
    --ctrl-address "localhost" \
    --ctrl-port "${ZITI_CTRL_PORT}" \
    --router-address "localhost" \
    --router-port "${ZITI_ROUTER_PORT}"


