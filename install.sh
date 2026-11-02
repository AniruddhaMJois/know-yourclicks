#!/usr/bin/env bash
# KnowYourClicks - Linux Desktop Application & Service Installer
# Installs as a 100% offline desktop application with desktop launcher, icon, systemd service,
# and automatically requests necessary hardware permissions.

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

INSTALL_DIR="$HOME/.local/share/knowyourclicks/app"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICONS_BASE="$HOME/.local/share/icons/hicolor"
SERVICE_DIR="$HOME/.config/systemd/user"
TARGET_USER="${SUDO_USER:-$USER}"

echo "=========================================================="
echo "    KnowYourClicks - Desktop App & Service Installer"
echo "    100% Offline | Zero Cloud | Privacy Whitelist"
echo "=========================================================="
echo ""

# Helper to run privileged commands automatically via pkexec (GUI dialog) or sudo
run_privileged() {
    if [ "$(id -u)" -eq 0 ]; then
        bash -c "$*"
    elif command -v pkexec >/dev/null 2>&1 && [ -n "$DISPLAY$WAYLAND_DISPLAY" ]; then
        pkexec bash -c "$*"
    elif command -v sudo >/dev/null 2>&1; then
        sudo bash -c "$*"
    else
        echo "Notice: Root privileges required for system-wide hardware permissions." >&2
        return 1
    fi
}

# 1. Check and automatically request hardware permissions if needed
echo "[1/6] Checking keyboard input device permissions..."
NEED_PERMS=0
TEST_DEV=$(ls /dev/input/event* 2>/dev/null | head -n 1)

if [ -n "$TEST_DEV" ]; then
    if [ ! -r "$TEST_DEV" ]; then
        NEED_PERMS=1
    fi
fi

if [ "$NEED_PERMS" -eq 1 ]; then
    echo "Hardware key monitoring permissions needed. Requesting authorization..."
    PERM_CMD=$(cat <<'EOF'
TARGET_USER="$1"

# Add user to input group
if ! groups "$TARGET_USER" 2>/dev/null | grep -q "\binput\b"; then
    usermod -aG input "$TARGET_USER" 2>/dev/null || true
fi

# Priority 70 ensures TAG+="uaccess" is evaluated before 73-seat-late.rules
rm -f /etc/udev/rules.d/99-knowyourclicks.rules 2>/dev/null || true
RULE_FILE="/etc/udev/rules.d/70-knowyourclicks.rules"
cat <<'RULE' > "$RULE_FILE"
# KnowYourClicks: allow logged-in user access to input events and uinput
KERNEL=="event*", SUBSYSTEM=="input", TAG+="uaccess"
KERNEL=="uinput", SUBSYSTEM=="misc", TAG+="uaccess", MODE="0660"
KERNEL=="event*", SUBSYSTEM=="input", GROUP="input", MODE="0660"
RULE

chmod 644 "$RULE_FILE"

# Reload udev rules and trigger immediately
udevadm control --reload-rules 2>/dev/null || true
udevadm trigger 2>/dev/null || true

# Apply instant ACL read access for current session
if command -v setfacl >/dev/null 2>&1; then
    setfacl -m u:"$TARGET_USER":r /dev/input/event* 2>/dev/null || true
    setfacl -m u:"$TARGET_USER":rw /dev/uinput 2>/dev/null || true
fi
EOF
)
    if run_privileged "$PERM_CMD" _ "$TARGET_USER"; then
        echo "✓ Hardware permissions automatically configured!"
    else
        echo "Notice: Continuing user-space installation..."
    fi
else
    echo "✓ Device access permissions already verified."
fi

# 2. Stop running daemon before updating
if [ -f "$BIN_DIR/knowyourclicks" ]; then
    "$BIN_DIR/knowyourclicks" stop 2>/dev/null || true
elif [ -f "$DIR/knowyourclicks" ]; then
    "$DIR/knowyourclicks" stop 2>/dev/null || true
fi

# 3. Create target directories
echo "[2/6] Creating installation directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$APPS_DIR"
mkdir -p "$SERVICE_DIR"
mkdir -p "$ICONS_BASE/scalable/apps"
mkdir -p "$ICONS_BASE/128x128/apps"
mkdir -p "$ICONS_BASE/64x64/apps"
mkdir -p "$ICONS_BASE/48x48/apps"
mkdir -p "$ICONS_BASE/32x32/apps"

# 4. Copy application files
echo "[3/6] Copying application files to $INSTALL_DIR..."
cp -r "$DIR/src" "$INSTALL_DIR/"
cp -r "$DIR/icons" "$INSTALL_DIR/"
cp "$DIR/knowyourclicks" "$INSTALL_DIR/knowyourclicks"
chmod +x "$INSTALL_DIR/knowyourclicks"
if [ -f "$DIR/remove_permissions.sh" ]; then
    cp "$DIR/remove_permissions.sh" "$INSTALL_DIR/"
    cp "$DIR/remove_permissions.sh" "$HOME/.local/share/knowyourclicks/"
    chmod +x "$INSTALL_DIR/remove_permissions.sh" "$HOME/.local/share/knowyourclicks/remove_permissions.sh"
fi
if [ -f "$DIR/uninstall.sh" ]; then
    cp "$DIR/uninstall.sh" "$INSTALL_DIR/"
    cp "$DIR/uninstall.sh" "$HOME/.local/share/knowyourclicks/"
    chmod +x "$INSTALL_DIR/uninstall.sh" "$HOME/.local/share/knowyourclicks/uninstall.sh"
fi

# Symlink to ~/.local/bin/knowyourclicks
ln -sf "$INSTALL_DIR/knowyourclicks" "$BIN_DIR/knowyourclicks"

# 5. Install desktop launcher icons
echo "[4/6] Installing desktop icons..."
if [ -f "$DIR/icons/knowyourclicks.svg" ]; then
    cp "$DIR/icons/knowyourclicks.svg" "$ICONS_BASE/scalable/apps/knowyourclicks.svg"
fi
if [ -f "$DIR/icons/knowyourclicks-128.png" ]; then
    cp "$DIR/icons/knowyourclicks-128.png" "$ICONS_BASE/128x128/apps/knowyourclicks.png"
fi
if [ -f "$DIR/icons/knowyourclicks-64.png" ]; then
    cp "$DIR/icons/knowyourclicks-64.png" "$ICONS_BASE/64x64/apps/knowyourclicks.png"
fi
if [ -f "$DIR/icons/knowyourclicks-48.png" ]; then
    cp "$DIR/icons/knowyourclicks-48.png" "$ICONS_BASE/48x48/apps/knowyourclicks.png"
fi
if [ -f "$DIR/icons/knowyourclicks-32.png" ]; then
    cp "$DIR/icons/knowyourclicks-32.png" "$ICONS_BASE/32x32/apps/knowyourclicks.png"
fi

# 6. Install .desktop file
echo "[5/6] Installing desktop launcher (.desktop entry)..."
cat <<EOF > "$APPS_DIR/knowyourclicks.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=KnowYourClicks
GenericName=Keystroke Analytics & Speed Monitor
Comment=Privacy-first keystroke analytics, space-triggered text expander, and speed monitor
Exec=$BIN_DIR/knowyourclicks app
Icon=knowyourclicks
Terminal=false
Categories=Utility;Office;Monitor;
StartupNotify=true
StartupWMClass=knowyourclicks
Keywords=keyboard;clicks;keystrokes;speed;wpm;analytics;shortcuts;typing;
X-Purism-FormFactor=Workstation;Mobile;
EOF

chmod +x "$APPS_DIR/knowyourclicks.desktop"

# Update desktop and icon databases
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$ICONS_BASE" >/dev/null 2>&1 || true
fi

# 7. Configure and start systemd background daemon service
echo "[6/6] Configuring background monitoring service..."
cat << 'EOF' > "$SERVICE_DIR/knowyourclicks.service"
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

if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload
    systemctl --user enable knowyourclicks.service
    systemctl --user restart knowyourclicks.service
    echo "✓ Background tracking service active via systemd."
fi

# Verify user PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "Notice: Add 'export PATH=\"\$HOME/.local/bin:\$PATH\"' to your ~/.bashrc or ~/.zshrc."
fi

echo ""
echo "=========================================================="
echo "    ✓ Installation Completed Successfully!"
echo "=========================================================="
echo ""
echo "KnowYourClicks is installed and ready to use:"
echo "  • Open your Application Menu (Super key / Search) and click 'KnowYourClicks'"
echo "  • Or launch in terminal by running: knowyourclicks app"
echo "  • Or run the start script: $DIR/start.sh"
echo ""
