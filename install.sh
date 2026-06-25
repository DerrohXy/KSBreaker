#!/usr/bin/env bash

set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
    echo "ERROR: install.sh must be run as root."
    echo
    echo "Usage:"
    echo "    sudo ./install.sh"
    exit 1
fi

SERVICE_NAME="ksbreaker"
INSTALL_DIR="/opt/ksbreaker"
CLI_DIR="/usr/local/sbin"
VENV_DIR="$INSTALL_DIR/venv"
SCRIPT_NAME="ksbreaker.py"

echo "Installing ${SERVICE_NAME}..."

# ------------------------------------------------------------------
# Validate
# ------------------------------------------------------------------

if [[ ! -f "${SCRIPT_NAME}" ]]; then
    echo "ERROR: ${SCRIPT_NAME} not found in current directory."
    exit 1
fi

# ------------------------------------------------------------------
# Dependencies
# ------------------------------------------------------------------

if command -v apt-get >/dev/null 2>&1; then
    apt-get update
    apt-get install -y python3 python3-pip
elif command -v dnf >/dev/null 2>&1; then
    dnf install -y python3 python3-pip
elif command -v yum >/dev/null 2>&1; then
    yum install -y python3 python3-pip
else
    echo "Unsupported package manager."
    exit 1
fi

# python3 -m pip install --upgrade pip
# python3 -m pip install psutil

# ------------------------------------------------------------------
# Install Files
# ------------------------------------------------------------------

mkdir -p "${INSTALL_DIR}"
cp "${SCRIPT_NAME}" "${INSTALL_DIR}/${SCRIPT_NAME}"

echo "Setting up python virtual environment..."

python3 -m venv "$VENV_DIR"

chown -R root:root "${INSTALL_DIR}"
chmod 755 "${INSTALL_DIR}"
chmod 755 "${VENV_DIR}"
chmod 755 "${INSTALL_DIR}/${SCRIPT_NAME}"

echo "Installing python dependencies..."

"$VENV_DIR/bin/python3" -m pip install --upgrade pip
"$VENV_DIR/bin/python3" -m pip install psutil

# ------------------------------------------------------------------
# CLI util
# ------------------------------------------------------------------

echo "Setting up CLI util..."

cp "${SCRIPT_NAME}" "${CLI_DIR}/${SERVICE_NAME}"
chmod +x "${CLI_DIR}/${SERVICE_NAME}"

# ------------------------------------------------------------------
# Systemd Service
# ------------------------------------------------------------------

echo "Setting up systemd service..."

cat >/etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=KSBreaker Watchdog
After=network.target

[Service]
Type=simple
User=root
Group=root

WorkingDirectory=${INSTALL_DIR}

ExecStart=${VENV_DIR}/bin/python3 ${INSTALL_DIR}/${SCRIPT_NAME} start

Restart=always
RestartSec=10

StandardOutput=journal
StandardError=journal

NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

# ------------------------------------------------------------------
# Activate
# ------------------------------------------------------------------

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

echo
echo "Installation complete."
echo
echo "Service Status:"
systemctl --no-pager --full status ${SERVICE_NAME}