#!/bin/bash

# Fix for rpi_hardware_pwm: add missing dtoverlay=pwm-2chan

set -e

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)."
    exec sudo "$0" "$@"
    exit
fi
apt upgrade
apt install python3-lgpio
# Find config.txt
CONFIG_FILE=""
for candidate in /boot/firmware/config.txt /boot/config.txt; do
    if [ -f "$candidate" ]; then
        CONFIG_FILE="$candidate"
        break
    fi
done

if [ -z "$CONFIG_FILE" ]; then
    echo "ERROR: Could not find config.txt (searched /boot/config.txt and /boot/firmware/config.txt)"
    echo "Please locate your config.txt manually and add the line: dtoverlay=pwm-2chan"
    exit 1
fi

echo "Found config file at: $CONFIG_FILE"

OVERLAY_LINE="dtoverlay=pwm-2chan"

# Backup
BACKUP_FILE="${CONFIG_FILE}.bak.$(date +%Y%m%d_%H%M%S)"
echo "Creating backup: $BACKUP_FILE"
cp "$CONFIG_FILE" "$BACKUP_FILE"

# Check if already present
if grep -qE "^\s*$OVERLAY_LINE\s*$" "$CONFIG_FILE"; then
    echo "✅ $OVERLAY_LINE already present. No changes needed."
else
    echo "➕ Adding $OVERLAY_LINE to $CONFIG_FILE"
    echo "$OVERLAY_LINE" >> "$CONFIG_FILE"
    echo "✅ Added. Reboot required to activate PWM hardware."
    REBOOT_NEEDED=1
fi

echo ""
if [ -n "$REBOOT_NEEDED" ]; then
    read -p "Reboot now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Rebooting in 3 seconds... Press Ctrl+C to cancel"
        sleep 3
        reboot
    else
        echo "Please reboot later using: sudo reboot"
    fi
else
    echo "No changes made. If you still see the PWM error, try rebooting anyway."
fi
