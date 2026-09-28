from __future__ import annotations

import argparse
import json
import struct
import time
from pathlib import Path

import enet


ID_JOIN_REQUEST = 1
ID_JOIN_SUCCESS = 2
ID_SET_GAME_INFO = 4
ID_LDN_PACKET = 6

LDN_SCAN = 0
LDN_SCAN_RESPONSE = 1


def string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return struct.pack(">I", len(encoded)) + encoded


def join_packet(nickname: str, password: str) -> bytes:
    return (
        bytes([ID_JOIN_REQUEST])
        + string(nickname)
        + b"\xff\xff\xff\xff"
        + struct.pack(">I", 1)
        + string(password)
        + string("")
    )


def game_info_packet() -> bytes:
    return (
        bytes([ID_SET_GAME_INFO])
        + string("Pokemon Scarlet")
        + struct.pack(">Q", 0x0100A3D008C5C000)
        + string("4.0.0")
    )


def scan_packet(local_ip: bytes) -> bytes:
    return (
        bytes([ID_LDN_PACKET, LDN_SCAN])
        + local_ip
        + b"\x00\x00\x00\x00"
        + b"\x01"
        + struct.pack(">I", 0)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal Eden room LDN scanner")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=24872)
    parser.add_argument("--nickname", default="Scanner")
    parser.add_argument("--password", default="past-raids")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=45.0)
    args = parser.parse_args()

    client = enet.Host(None, 1, 1, 0, 0)
    peer = client.connect(enet.Address(args.host.encode(), args.port), 1)
    deadline = time.monotonic() + args.timeout
    joined = False
    local_ip = b""
    last_scan = 0.0
    events: list[dict[str, object]] = []

    while time.monotonic() < deadline:
        event = client.service(50)
        now = time.monotonic()

        if event.type == enet.EVENT_TYPE_CONNECT:
            peer.send(0, enet.Packet(join_packet(args.nickname, args.password), enet.PACKET_FLAG_RELIABLE))
            events.append({"event": "connected"})
        elif event.type == enet.EVENT_TYPE_RECEIVE:
            payload = bytes(event.packet.data)
            message_id = payload[0] if payload else -1
            events.append({"event": "receive", "message_id": message_id, "length": len(payload)})

            if message_id == ID_JOIN_SUCCESS and len(payload) >= 5:
                local_ip = payload[1:5]
                joined = True
                peer.send(0, enet.Packet(game_info_packet(), enet.PACKET_FLAG_RELIABLE))
                last_scan = 0.0
                events.append({"event": "joined", "ip": ".".join(map(str, local_ip))})
            elif message_id == ID_LDN_PACKET and len(payload) >= 15:
                packet_type = payload[1]
                data_length = struct.unpack(">I", payload[11:15])[0]
                data = payload[15 : 15 + data_length]
                events.append(
                    {
                        "event": "ldn",
                        "packet_type": packet_type,
                        "local_ip": ".".join(map(str, payload[2:6])),
                        "remote_ip": ".".join(map(str, payload[6:10])),
                        "broadcast": bool(payload[10]),
                        "data_length": len(data),
                    }
                )
                if packet_type == LDN_SCAN_RESPONSE and data:
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_bytes(data)
                    args.output.with_suffix(".json").write_text(
                        json.dumps(events, indent=2), encoding="utf-8"
                    )
                    peer.disconnect()
                    client.flush()
                    print(f"SCAN_RESPONSE {len(data)} bytes -> {args.output}", flush=True)
                    return 0
        elif event.type == enet.EVENT_TYPE_DISCONNECT:
            events.append({"event": "disconnected"})
            break

        if joined and now - last_scan >= 2.0:
            peer.send(0, enet.Packet(scan_packet(local_ip), enet.PACKET_FLAG_RELIABLE))
            client.flush()
            last_scan = now
            print("SCAN_SENT", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(json.dumps(events, indent=2), encoding="utf-8")
    print("TIMEOUT: no LDN scan response", flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
