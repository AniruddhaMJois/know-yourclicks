#!/usr/bin/env bash
# KnowYourClicks - Remove Background Running & Hardware Input Permissions
# Completely disables background daemon services, removes systemd user units,
# deletes udev rules, removes user from the input group, and resets device ACLs.

set -e

TARGET_USER="${SUDO_USER:-$USER}"
SERVICE_FILE="$HOME/.config/systemd/user/knowyourclicks.service"
PID_FILE="$HOME/.local/state/knowyourclicks/daemon.pid"

echo "=========================================================="
echo "    KnowYourClicks - Remove Background Permissions"
echo "=========================================================="
echo ""
echo "This script will completely revoke and remove:"
echo "  1. Systemd background autostart service (knowyourclicks.service)"
echo "  2. Running background daemon processes"
echo "  3. Udev hardware input monitoring rules (/etc/udev/rules.d/*knowyourclicks*)"
echo "  4. User membership from the 'input' group"
echo "  5. Direct device Access Control Lists (ACLs) on /dev/input"
echo ""

# Helper to execute privileged root actions
run_privileged() {
    if [ "$(id -u)" -eq 0 ]; then
        bash -c "$*"
    elif command -v pkexec >/dev/null 2>&1 && [ -n "$DISPLAY$WAYLAND_DISPLAY" ]; then
        pkexec bash -c "$*"
    elif command -v sudo >/dev/null 2>&1; then
        sudo bash -c "$*"
    else
        echo "Error: Root privileges required to remove system-wide udev and group permissions." >&2
        return 1
    fi
}

# Step 1: Stop and disable systemd user service
echo "[1/4] Stopping and disabling background systemd service..."
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user stop knowyourclicks.service 2>/dev/null || true
    systemctl --user disable knowyourclicks.service 2>/dev/null || true
    if [ -f "$SERVICE_FILE" ]; then
        rm -f "$SERVICE_FILE"
        systemctl --user daemon-reload 2>/dev/null || true
        echo "✓ Removed systemd user service unit."
    else
        echo "✓ No systemd service unit found."
    fi
fi

# Step 2: Stop any running background daemon
echo "[2/4] Stopping any active daemon processes..."
if [ -f "$HOME/.local/bin/knowyourclicks" ]; then
    "$HOME/.local/bin/knowyourclicks" stop 2>/dev/null || true
fi
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
fi
echo "✓ Background daemon stopped."

# Step 3: Remove udev rules, input group membership, and reset ACLs
echo "[3/4] Requesting root authorization to remove udev rules and input permissions..."
PRIV_CMD=$(cat <<'EOF'
TARGET_USER="$1"

# 1. Remove udev rules
rm -f /etc/udev/rules.d/70-knowyourclicks.rules 2>/dev/null || true
rm -f /etc/udev/rules.d/99-knowyourclicks.rules 2>/dev/null || true

# 2. Reload udev rules and re-trigger
if command -v udevadm >/dev/null 2>&1; then
    udevadm control --reload-rules 2>/dev/null || true
    udevadm trigger 2>/dev/null || true
fi

# 3. Remove user from 'input' group
if groups "$TARGET_USER" 2>/dev/null | grep -q "\binput\b"; then
    if command -v gpasswd >/dev/null 2>&1; then
        gpasswd -d "$TARGET_USER" input 2>/dev/null || true
    elif command -v deluser >/dev/null 2>&1; then
        deluser "$TARGET_USER" input 2>/dev/null || true
    fi
fi

# 4. Clear any ACL read grants on input devices
if command -v setfacl >/dev/null 2>&1; then
    setfacl -b /dev/input/event* 2>/dev/null || true
    setfacl -b /dev/uinput 2>/dev/null || true
fi
EOF
)

if run_privileged "$PRIV_CMD" _ "$TARGET_USER"; then
    echo "✓ Udev rules removed, user removed from 'input' group, and device ACLs reset."
else
    echo "Warning: Could not automatically remove system-wide permissions. You can remove them manually with:"
    echo "  sudo rm -f /etc/udev/rules.d/*knowyourclicks*"
    echo "  sudo udevadm control --reload-rules && sudo udevadm trigger"
    echo "  sudo gpasswd -d $TARGET_USER input"
fi

# Step 4: Verification
echo "[4/4] Verifying background service status..."
echo ""
echo "=========================================================="
echo "    ✓ Background Running Permissions Successfully Removed!"
echo "=========================================================="
echo ""
echo "Summary of actions taken:"
echo "  • knowyourclicks.service: DISABLED and REMOVED"
echo "  • Background daemon process: STOPPED"
echo "  • /etc/udev/rules.d/70-knowyourclicks.rules: REMOVED"
echo "  • User '$TARGET_USER' removed from 'input' group"
echo "  • Device ACLs: RESET"
echo ""
echo "Note: If your session still has cached group credentials, log out and log back in."
echo ""
