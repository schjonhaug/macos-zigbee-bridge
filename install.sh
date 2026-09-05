#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
PLIST_NAME="com.zbt2.serial-bridge.plist"
PYTHON="$(command -v python3)"

# Detect serial port (ZBT-2 uses usbmodem; ZBT-1/SkyConnect uses usbserial)
SERIAL_PORT=$(find /dev -maxdepth 1 \( -name 'cu.usbmodem*' -o -name 'cu.usbserial*' \) -print | sort | head -1)
if [ -z "$SERIAL_PORT" ]; then
    echo "Error: No ZBT-1/ZBT-2 serial device found. Is the coordinator plugged in?"
    exit 1
fi
echo "Found serial port: $SERIAL_PORT"

# Check pyserial
if ! "$PYTHON" -c "import serial" 2>/dev/null; then
    echo "Installing pyserial..."
    "$PYTHON" -m pip install pyserial --break-system-packages -q
fi

# Create LaunchAgent
mkdir -p "$LAUNCH_AGENTS"
cat > "$LAUNCH_AGENTS/$PLIST_NAME" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.zbt2.serial-bridge</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$SCRIPT_DIR/zbt2-bridge.py</string>
        <string>--port</string>
        <string>$SERIAL_PORT</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/zbt2-bridge.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/zbt2-bridge.log</string>
</dict>
</plist>
PLIST

# Load the agent
launchctl unload "$LAUNCH_AGENTS/$PLIST_NAME" 2>/dev/null || true
launchctl load "$LAUNCH_AGENTS/$PLIST_NAME"

MAC_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "<your-mac-ip>")

echo ""
echo "Bridge installed and running!"
echo ""
echo "In Home Assistant, set up ZHA with:"
echo "  Adapter type:  EZSP"
echo "  Serial port:   socket://$MAC_IP:8888"
if [[ "$SERIAL_PORT" == *usbserial* ]]; then
    echo "  Baudrate:      115200"
    echo "  Flow control:  hardware (RTS/CTS)"
else
    echo "  Baudrate:      460800"
    echo "  Flow control:  none"
fi
