#!/usr/bin/env bash

set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
    echo "ERROR: install.sh must be run as root."
    echo
    echo "Usage:"
    echo "    sudo ./uninstall.sh"
    exit 1
fi

SERVICE_NAME="ksbreaker"
INSTALL_DIR="/opt/ksbreaker"
CLI_DIR="/usr/local/sbin"

echo "Terminating service..."

systemctl disable ${SERVICE_NAME} || true
systemctl stop ${SERVICE_NAME} || true

echo "Uninstalling service..."

rm -f /etc/systemd/system/${SERVICE_NAME}.service

systemctl daemon-reload

rm -rf "$INSTALL_DIR"

echo "Uninstalling CLI util..."

rm -rf "${CLI_DIR}/${SERVICE_NAME}"

echo "Removed ${SERVICE_NAME}"
