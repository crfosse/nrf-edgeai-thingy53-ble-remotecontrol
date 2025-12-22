#!/bin/bash
# Run install.sh in dockerimages to verify that install works on all supported distros
# This does not actually test that the demo itself works, just that the install script completes without error
set -euo pipefail
trap 'echo "Error on line $LINENO"; exit 1' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."

cd "$PROJECT_ROOT"

for distro in ubuntu:24.04 fedora:latest debian:latest; do
  echo "Processing $distro"
  # Use no-cache to ensure we always get a fresh image as most of the dependecies
  # are not captured in layers due to install.sh installing them
  docker build --no-cache -t neuton-ble-remotecontrol-test-$distro -f "$SCRIPT_DIR/Dockerfile" --build-arg BASE_IMAGE=$distro .
done
