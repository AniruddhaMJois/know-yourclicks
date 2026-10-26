#!/usr/bin/env bash
# Helper script to configure Linux permissions for global /dev/input device access

set -e

echo "=== KnowYourClicks Linux Permissions Setup ==="
echo "To allow background keystroke monitoring without root, your user needs"
echo "membership in the 'input' group."
echo ""

if groups "$USER" | grep -q "\binput\b"; then
    echo "✓ User '$USER' is already in the 'input' group."
else
    echo "Adding user '$USER' to 'input' group..."
    sudo usermod -aG input "$USER"
    echo "✓ Added '$USER' to 'input' group."
    echo "⚠️ IMPORTANT: You must log out and log back in (or reboot) for group changes to take effect."
fi

# Optional: Udev rule for /dev/uinput text expansion
if [ ! -f /etc/udev/rules.d/99-knowyourclicks.rules ]; then
    echo ""
    echo "Setting up udev rule for /dev/uinput (text expander)..."
    echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/99-knowyourclicks.rules > /dev/null
    sudo udevadm control --reload-rules && sudo udevadm trigger
    echo "✓ Udev rule configured."
fi

echo ""
echo "Setup completed successfully!"
