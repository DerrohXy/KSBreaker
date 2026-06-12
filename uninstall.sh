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

systemctl stop ${SERVICE_NAME} || true
systemctl disable ${SERVICE_NAME} || true

rm -f /etc/systemd/system/${SERVICE_NAME}.service

systemctl daemon-reload

rm -rf /opt/ksbreaker

echo "Removed ${SERVICE_NAME}"