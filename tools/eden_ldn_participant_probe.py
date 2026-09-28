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
ID_PROXY_PACKET = 5
ID_LDN_PACKET = 6

LDN_SCAN = 0
LDN_SCAN_RESPONSE = 1
LDN_CONNECT = 2
LDN_SYNC_NETWORK = 3


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


def ldn_packet(packet_type: int, local_ip: bytes, remote_ip: bytes, broadcast: bool, data: bytes = b"") -> bytes:
    return (
        bytes([ID_LDN_PACKET, packet_type])
        + local_ip
        + remote_ip
        + bytes([int(broadcast)])
        + struct.pack(">I", len(data))
        + data
    )


def node_info(local_ip: bytes, name: str, version: int) -> bytes:
    stored_ip = local_ip[::-1]
    mac = bytes([0x02, 0x00]) + local_ip
    username = name.encode("utf-8")[:32].ljust(33, b"\x00")
    return (
        stored_ip
        + mac
        + b"\x00"       # host overwrites node id
        + b"\x01"       # connected
        + username
        + b"\x00"       # reserved/alignment
        + struct.pack("<h", version)
        + bytes(16)
    )


def parse_proxy(payload: bytes) -> dict[str, object]:
    if len(payload) < 21:
        return {"error": "short proxy packet", "hex": payload.hex()}
    data_len = struct.unpack(">I", payload[17:21])[0]
    return {
        "local_family": payload[1],
        "local_ip": ".".join(map(str, payload[2:6])),
        "local_port": struct.unpack(">H", payload[6:8])[0],
        "remote_family": payload[8],
        "remote_ip": ".".join(map(str, payload[9:13])),
        "remote_port": struct.unpack(">H", payload[13:15])[0],
        "protocol": payload[15],
        "broadcast": bool(payload[16]),
        "data_length": data_len,
        "data_hex": payload[21 : 21 + data_len].hex(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthetic LDN participant for an Eden room")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=24872)
    parser.add_argument("--nickname", default="RaidProbe")
    parser.add_argument("--password", default="past-raids")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=150.0)
    args = parser.parse_args()

    client = enet.Host(None, 1, 1, 0, 0)
    peer = client.connect(enet.Address(args.host.encode(), args.port), 1)
    deadline = time.monotonic() + args.timeout
    local_ip = b""
    host_ip = b""
    joined = False
    connected = False
    last_scan = 0.0
    records: list[dict[str, object]] = []
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def record(item: dict[str, object]) -> None:
        item["elapsed"] = round(time.monotonic() - (deadline - args.timeout), 6)
        records.append(item)
        args.output.write_text("\n".join(json.dumps(x, separators=(",", ":")) for x in records) + "\n", encoding="utf-8")

    while time.monotonic() < deadline:
        event = client.service(25)
        now = time.monotonic()
        if event.type == enet.EVENT_TYPE_CONNECT:
            peer.send(0, enet.Packet(join_packet(args.nickname, args.password), enet.PACKET_FLAG_RELIABLE))
            record({"event": "enet_connected"})
        elif event.type == enet.EVENT_TYPE_RECEIVE:
            payload = bytes(event.packet.data)
            message_id = payload[0] if payload else -1
            if message_id == ID_JOIN_SUCCESS and len(payload) >= 5:
                local_ip = payload[1:5]
                joined = True
                peer.send(0, enet.Packet(game_info_packet(), enet.PACKET_FLAG_RELIABLE))
                record({"event": "joined", "local_ip": ".".join(map(str, local_ip))})
            elif message_id == ID_LDN_PACKET and len(payload) >= 15:
                packet_type = payload[1]
                data_len = struct.unpack(">I", payload[11:15])[0]
                data = payload[15 : 15 + data_len]
                record({
                    "event": "ldn",
                    "packet_type": packet_type,
                    "local_ip": ".".join(map(str, payload[2:6])),
                    "remote_ip": ".".join(map(str, payload[6:10])),
                    "broadcast": bool(payload[10]),
                    "data_length": len(data),
                    "data_hex": data.hex(),
                })
                if packet_type == LDN_SCAN_RESPONSE and not connected:
                    host_ip = payload[2:6]
                    version = struct.unpack_from("<h", data, 0x68 + 46)[0]
                    node = node_info(local_ip, "RaidProbe", version)
                    peer.send(0, enet.Packet(ldn_packet(LDN_CONNECT, local_ip, host_ip, False, node), enet.PACKET_FLAG_RELIABLE))
                    client.flush()
                    connected = True
                    record({"event": "connect_sent", "host_ip": ".".join(map(str, host_ip)), "version": version})
            elif message_id == ID_PROXY_PACKET:
                record({"event": "proxy", **parse_proxy(payload)})
            else:
                record({"event": "room", "message_id": message_id, "length": len(payload)})
        elif event.type == enet.EVENT_TYPE_DISCONNECT:
            record({"event": "disconnected"})
            break

        if joined and not connected and now - last_scan >= 1.0:
            peer.send(0, enet.Packet(ldn_packet(LDN_SCAN, local_ip, bytes(4), True), enet.PACKET_FLAG_RELIABLE))
            client.flush()
            last_scan = now
            record({"event": "scan_sent"})

    peer.disconnect()
    client.flush()
    proxy_count = sum(1 for item in records if item["event"] == "proxy")
    print(f"DONE connected={connected} proxy_packets={proxy_count} records={len(records)}", flush=True)
    return 0 if connected else 2


if __name__ == "__main__":
    raise SystemExit(main())
