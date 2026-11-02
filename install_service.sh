#!/usr/bin/env bash
# Installs KnowYourClicks as a persistent Systemd User Service
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
SERVICE_DIR="$HOME/.config/systemd/user"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$SERVICE_DIR" "$BIN_DIR"

echo "=== Installing KnowYourClicks Systemd User Service ==="

# Copy executable link
ln -sf "$DIR/knowyourclicks" "$BIN_DIR/knowyourclicks"

# Copy service unit
cat <<EOF > "$SERVICE_DIR/knowyourclicks.service"
[Unit]
Description=KnowYourClicks Background Input Daemon
After=default.target

[Service]
Type=simple
ExecStart=%h/.local/bin/knowyourclicks start --foreground
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF

# Reload and enable
systemctl --user daemon-reload
systemctl --user enable knowyourclicks.service
systemctl --user restart knowyourclicks.service

echo ""
echo "✓ KnowYourClicks service installed and started!"
echo "Check status anytime with: systemctl --user status knowyourclicks.service"
