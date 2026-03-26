#!/usr/bin/env python3
"""
Bridge a USB Zigbee coordinator's serial port to TCP, allowing a Home Assistant
VM to connect via socket:// when macOS blocks USB passthrough.

Requires: pyserial (`pip3 install pyserial`)
"""

import argparse
import asyncio
import signal
import sys

import serial


async def bridge(serial_port: str, baudrate: int, tcp_port: int) -> None:
    ser = serial.Serial(serial_port, baudrate, timeout=0)
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

    server = await asyncio.start_server(handle_client, "0.0.0.0", tcp_port)
    print(
        f"ZBT-2 bridge: {serial_port} -> tcp://0.0.0.0:{tcp_port} "
        f"(baud {baudrate})",
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
        default="/dev/cu.usbmodem441BF685F5301",
        help="Serial port path (default: %(default)s)",
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=460800,
        help="Serial baud rate (default: %(default)s)",
    )
    parser.add_argument(
        "--tcp-port",
        type=int,
        default=8888,
        help="TCP port to listen on (default: %(default)s)",
    )
    args = parser.parse_args()
    asyncio.run(bridge(args.port, args.baudrate, args.tcp_port))


if __name__ == "__main__":
    main()
