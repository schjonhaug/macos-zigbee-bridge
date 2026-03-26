#!/bin/bash
set -euo pipefail

PLIST="$HOME/Library/LaunchAgents/com.zbt2.serial-bridge.plist"

if [ -f "$PLIST" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm "$PLIST"
    echo "Bridge service removed."
else
    echo "Bridge service not installed."
fi
