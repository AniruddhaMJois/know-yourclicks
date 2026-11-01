#!/usr/bin/env bash
# KnowYourClicks - Automated Permissions Setup for Linux
# Automatically configures /dev/input access and udev rules without manual terminal commands.

set -e

TARGET_USER="${SUDO_USER:-$USER}"

echo "=== KnowYourClicks Linux Permissions Setup ==="

# Helper to execute privileged operations automatically via pkexec or sudo
run_root() {
    if [ "$(id -u)" -eq 0 ]; then
        bash -c "$*"
    elif command -v pkexec >/dev/null 2>&1 && [ -n "$DISPLAY$WAYLAND_DISPLAY" ]; then
        pkexec bash -c "$*"
    elif command -v sudo >/dev/null 2>&1; then
        sudo bash -c "$*"
    else
        echo "Error: Root privileges required to configure hardware input permissions." >&2
        return 1
    fi
}

# 1. Add user to input group and configure udev rules
echo "Configuring hardware permissions for user '$TARGET_USER'..."

PERM_CMD=$(cat <<'EOF'
TARGET_USER="$1"

# Add to input group
if ! groups "$TARGET_USER" 2>/dev/null | grep -q "\binput\b"; then
    usermod -aG input "$TARGET_USER" 2>/dev/null || true
fi

# Modern udev rule with systemd uaccess tag for immediate desktop user access
RULE_FILE="/etc/udev/rules.d/99-knowyourclicks.rules"
cat <<'RULE' > "$RULE_FILE"
# KnowYourClicks: allow logged-in user access to input events and uinput
KERNEL=="event*", SUBSYSTEM=="input", TAG+="uaccess"
KERNEL=="uinput", SUBSYSTEM=="misc", TAG+="uaccess", MODE="0660"
RULE

chmod 644 "$RULE_FILE"

# Reload udev
udevadm control --reload-rules 2>/dev/null || true
udevadm trigger 2>/dev/null || true

# Grant immediate ACL read access to current session devices
if command -v setfacl >/dev/null 2>&1; then
    setfacl -m u:"$TARGET_USER":r /dev/input/event* 2>/dev/null || true
    setfacl -m u:"$TARGET_USER":rw /dev/uinput 2>/dev/null || true
fi
EOF
)

run_root "$PERM_CMD" _ "$TARGET_USER"

echo "✓ Hardware permissions and udev rules successfully configured!"
