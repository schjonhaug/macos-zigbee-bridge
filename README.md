# macOS Zigbee Bridge

Bridge a USB Zigbee coordinator — [Home Assistant Connect ZBT-1](https://www.home-assistant.io/connectzbt1/) (SkyConnect) or [ZBT-2](https://www.home-assistant.io/connectzbt2/) — to a Home Assistant VM over TCP when macOS blocks VirtualBox USB passthrough.

## The problem

On macOS Sonoma+, VirtualBox cannot capture USB serial devices like the ZBT-1 or ZBT-2. For the ZBT-2, the macOS CDC ACM kernel driver (`com.apple.driver.usb.cdc.acm`) claims the device and refuses to release it. The kext cannot be unloaded, and granting USB privacy permissions doesn't help — VirtualBox gets `VERR_SHARING_VIOLATION` every time.

Tools like `socat` and `ser2net` also fail to properly bridge the EZSP serial protocol, breaking the connection handshake.

## The solution

A lightweight Python script bridges the serial port to a TCP socket. Home Assistant's ZHA integration connects via `socket://` instead of a direct serial path.

```
Mac (serial) ──► zbt2-bridge.py (TCP :8888) ──► HA VM (socket://mac-ip:8888)
```

## Requirements

- macOS with Python 3.10+
- `pyserial` (`pip3 install pyserial`)
- A Zigbee USB coordinator (Home Assistant Connect ZBT-1/SkyConnect or ZBT-2)
- Home Assistant running in VirtualBox (or any VM)

## Quick start

1. Plug in your Zigbee coordinator

2. Run the installer:
   ```bash
   git clone https://github.com/YOUR_USERNAME/macos-zigbee-bridge.git
   cd macos-zigbee-bridge
   chmod +x install.sh
   ./install.sh
   ```

3. In Home Assistant, go to **Settings > Devices & Services > Add Integration > ZHA**:
   - Adapter type: **EZSP**
   - Serial port: **socket://YOUR_MAC_IP:8888**
   - Baudrate: **460800** for ZBT-2, **115200** for ZBT-1/SkyConnect
   - Flow control: **none** for ZBT-2, **hardware RTS/CTS** for ZBT-1/SkyConnect

The bridge auto-starts on login via a macOS LaunchAgent.

## Manual usage

```bash
# Default: auto-detect serial port and generation, TCP port 8888
python3 zbt2-bridge.py

# Custom settings
python3 zbt2-bridge.py --port /dev/cu.usbmodemXXXX --baudrate 460800 --tcp-port 9999

# SkyConnect/ZBT-1 explicitly (normally detected automatically)
python3 zbt2-bridge.py --port /dev/cu.usbserial-XXXX --baudrate 115200 --rtscts
```

The bridge identifies ZBT-2 devices by their `cu.usbmodem*` name and ZBT-1/SkyConnect
devices by `cu.usbserial*`. Use `--no-rtscts` or `--baudrate` to override firmware-specific settings.

## Uninstall

```bash
./uninstall.sh
```

## Troubleshooting

### ZBT-2 shows as "Espressif USB JTAG/serial debug unit"

The dongle is in debug mode instead of running Zigbee firmware. Reflash it at:
https://toolbox.openhomefoundation.org/home-assistant-connect-zbt-2/install/

You need the [Silicon Labs CP2102 driver](https://www.silabs.com/software-and-tools/usb-to-uart-bridge-vcp-drivers) installed for the flasher to work.

### "Unknown error" in ZHA setup

Check that the bridge is running:
```bash
lsof -i :8888
```

Check bridge logs:
```bash
cat /tmp/zbt2-bridge.log
```

### Why not socat or ser2net?

Both mangle the EZSP binary protocol. `socat` doesn't preserve framing, and `ser2net` has similar issues with the ASHv2 reset handshake. The Python bridge does raw byte forwarding without any interpretation, which is what EZSP needs.

## License

MIT
