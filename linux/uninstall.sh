#!/usr/bin/env bash
# KnowYourClicks - Linux Uninstaller Script
set -e

echo "=== Uninstalling KnowYourClicks ==="

# Stop systemd service
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user stop knowyourclicks.service 2>/dev/null || true
    systemctl --user disable knowyourclicks.service 2>/dev/null || true
    rm -f "$HOME/.config/systemd/user/knowyourclicks.service"
    systemctl --user daemon-reload 2>/dev/null || true
fi

# Stop daemon if running manually
if [ -f "$HOME/.local/bin/knowyourclicks" ]; then
    "$HOME/.local/bin/knowyourclicks" stop 2>/dev/null || true
fi

# Remove files
rm -f "$HOME/.local/bin/knowyourclicks"
rm -f "$HOME/.local/share/applications/knowyourclicks.desktop"
rm -rf "$HOME/.local/share/knowyourclicks/app"

# Remove icons
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/knowyourclicks.svg"
rm -f "$HOME/.local/share/icons/hicolor/128x128/apps/knowyourclicks.png"
rm -f "$HOME/.local/share/icons/hicolor/64x64/apps/knowyourclicks.png"
rm -f "$HOME/.local/share/icons/hicolor/48x48/apps/knowyourclicks.png"
rm -f "$HOME/.local/share/icons/hicolor/32x32/apps/knowyourclicks.png"

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

echo "✓ KnowYourClicks application and service removed successfully."
echo "Note: Your local database at ~/.local/share/knowyourclicks/stats.db was preserved."
