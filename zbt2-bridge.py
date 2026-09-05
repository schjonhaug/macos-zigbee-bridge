#!/usr/bin/env python3
"""
Bridge a USB Zigbee coordinator's serial port to TCP, allowing a Home Assistant
VM to connect via socket:// when macOS blocks USB passthrough.

Requires: pyserial (`pip3 install pyserial`)
"""

import argparse
import asyncio
from pathlib import Path

import serial


def detect_serial_port() -> str:
    """Return the first likely ZBT-1 or ZBT-2 device on macOS."""
    for pattern in ("/dev/cu.usbmodem*", "/dev/cu.usbserial*"):
        ports = sorted(Path("/dev").glob(pattern.removeprefix("/dev/")))
        if ports:
            return str(ports[0])
    raise FileNotFoundError("No ZBT-1/ZBT-2 serial device found")


def defaults_for_port(serial_port: str) -> tuple[int, bool]:
    """Return (baudrate, rtscts) defaults for the two Connect generations."""
    if "usbserial" in serial_port:
        # ZBT-1/SkyConnect uses a CP2102N USB bridge.
        return 115200, True
    # ZBT-2 uses an ESP32-S3 USB controller.
    return 460800, False


async def bridge(
    serial_port: str, baudrate: int, tcp_port: int, host: str, rtscts: bool
) -> None:
    ser = serial.Serial(serial_port, baudrate, timeout=0, rtscts=rtscts)
    clients: list[tuple[asyncio.StreamReader, asyncio.StreamWriter]] = []

    async def handle_client(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        addr = writer.get_extra_info("peername")
        print(f"Client connected: {addr}", flush=True)
        clients.append((reader, writer))
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                ser.write(data)
        except Exception:
            pass
        finally:
            clients.remove((reader, writer))
            writer.close()
            print(f"Client disconnected: {addr}", flush=True)

    async def serial_reader() -> None:
        loop = asyncio.get_event_loop()
        while True:
            data = await loop.run_in_executor(
                None, lambda: ser.read(ser.in_waiting or 1)
            )
            if data:
                for reader, writer in list(clients):
                    try:
                        writer.write(data)
                        await writer.drain()
                    except Exception:
                        pass
            else:
                await asyncio.sleep(0.001)

    server = await asyncio.start_server(handle_client, host, tcp_port)
    print(
        f"ZBT bridge: {serial_port} -> tcp://{host}:{tcp_port} "
        f"(baud {baudrate}, rtscts {rtscts})",
        flush=True,
    )
    asyncio.create_task(serial_reader())
    await server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bridge a Zigbee USB serial port to TCP for Home Assistant"
    )
    parser.add_argument(
        "--port",
        default=None,
        help="Serial port path (default: auto-detect usbmodem/usbserial)",
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=None,
        help="Serial baud rate (default: 460800 for ZBT-2, 115200 for ZBT-1)",
    )
    parser.add_argument(
        "--tcp-port",
        type=int,
        default=8888,
        help="TCP port to listen on (default: %(default)s)",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Address to bind (default: %(default)s)"
    )
    parser.add_argument(
        "--rtscts",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable hardware RTS/CTS (default: on for ZBT-1, off for ZBT-2)",
    )
    args = parser.parse_args()
    serial_port = args.port or detect_serial_port()
    default_baudrate, default_rtscts = defaults_for_port(serial_port)
    baudrate = args.baudrate or default_baudrate
    rtscts = default_rtscts if args.rtscts is None else args.rtscts
    asyncio.run(bridge(serial_port, baudrate, args.tcp_port, args.host, rtscts))


if __name__ == "__main__":
    main()
