from __future__ import annotations

import argparse
import json
import struct
import sys
from collections import Counter
from pathlib import Path

import zstandard


POKELDN = Path(__file__).resolve().parents[2] / "pokeldn-research"
sys.path.insert(0, str(POKELDN))

from pokeldn import sv  # noqa: E402
from pokeldn.sv import streams  # noqa: E402
from pokeldn.ldn import pia6, reliable5  # noqa: E402


ENET_SENT_TIME = 0x8000
ENET_COMPRESSED = 0x4000

COMMAND_SIZES = {
    1: 8,   # acknowledge
    2: 48,  # connect
    3: 44,  # verify connect
    4: 8,   # disconnect
    5: 4,   # ping
    6: 6,   # send reliable
    7: 8,   # send unreliable
    8: 24,  # send fragment
    9: 8,   # send unsequenced
    10: 12, # bandwidth limit
    11: 16, # throttle configure
    12: 24, # send unreliable fragment
}

ID_JOIN_SUCCESS = 2
ID_PROXY_PACKET = 5
ID_LDN_PACKET = 6
LDN_SCAN_RESPONSE = 1


def enet_payloads(datagram: bytes) -> list[dict[str, object]]:
    if len(datagram) < 2:
        return []
    peer = int.from_bytes(datagram[:2], "big")
    if peer & ENET_COMPRESSED:
        raise ValueError("compressed ENet datagram is not supported")
    offset = 4 if peer & ENET_SENT_TIME else 2
    result: list[dict[str, object]] = []
    while offset < len(datagram):
        if offset + 4 > len(datagram):
            raise ValueError(f"short ENet command at {offset}")
        command_byte = datagram[offset]
        command = command_byte & 0x0F
        size = COMMAND_SIZES.get(command)
        if size is None or offset + size > len(datagram):
            raise ValueError(f"unknown/short ENet command {command} at {offset}")
        channel = datagram[offset + 1]
        sequence = int.from_bytes(datagram[offset + 2 : offset + 4], "big")
        payload = b""
        if command == 6:
            data_size = int.from_bytes(datagram[offset + 4 : offset + 6], "big")
            payload = datagram[offset + size : offset + size + data_size]
            size += data_size
        elif command in (7, 8, 9, 12):
            data_size = int.from_bytes(datagram[offset + 6 : offset + 8], "big")
            payload = datagram[offset + COMMAND_SIZES[command] : offset + COMMAND_SIZES[command] + data_size]
            size += data_size
        item: dict[str, object] = {
                "command": command,
                "command_byte": command_byte,
                "channel": channel,
                "sequence": sequence,
                "payload": payload,
        }
        if command in (8, 12):
            item.update(
                {
                    "start_sequence": int.from_bytes(datagram[offset + 4 : offset + 6], "big"),
                    "fragment_count": int.from_bytes(datagram[offset + 8 : offset + 12], "big"),
                    "fragment_number": int.from_bytes(datagram[offset + 12 : offset + 16], "big"),
                    "total_length": int.from_bytes(datagram[offset + 16 : offset + 20], "big"),
                    "fragment_offset": int.from_bytes(datagram[offset + 20 : offset + 24], "big"),
                }
            )
        result.append(item)
        offset += size
    return result


def parse_ldn(payload: bytes) -> dict[str, object]:
    size = struct.unpack(">I", payload[11:15])[0]
    return {
        "kind": payload[1],
        "local_ip": ".".join(map(str, payload[2:6])),
        "remote_ip": ".".join(map(str, payload[6:10])),
        "broadcast": bool(payload[10]),
        "data": payload[15 : 15 + size],
    }


def parse_proxy(payload: bytes) -> tuple[bytes, bytes, bytes]:
    size = struct.unpack(">I", payload[17:21])[0]
    compressed = payload[21 : 21 + size]
    return payload[2:6], payload[9:13], zstandard.ZstdDecompressor().decompress(compressed)


def json_value(value: object) -> object:
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Decode a two-client Eden UDP capture")
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    states: dict[str, dict[str, object]] = {}
    counters: Counter[str] = Counter()
    output: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    fragments: dict[tuple[object, ...], dict[str, object]] = {}
    first_time: int | None = None

    with args.capture.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            capture = json.loads(line)
            client = capture["client"]
            state = states.setdefault(client, {"local_ip": None, "keys": None})
            time_ns = int(capture["time_ns"])
            if first_time is None:
                first_time = time_ns
            elapsed = round((time_ns - first_time) / 1_000_000_000, 6)
            try:
                commands = enet_payloads(bytes.fromhex(capture["hex"]))
            except Exception as exc:
                errors.append({"line": line_number, "client": client, "error": str(exc)})
                continue
            for command in commands:
                app = command.pop("payload")
                counters[f"enet_command_{command['command']}"] += 1
                if command["command"] in (8, 12):
                    fragment_key = (
                        client,
                        capture["direction"],
                        command["channel"],
                        command["start_sequence"],
                        command["total_length"],
                    )
                    bucket = fragments.setdefault(
                        fragment_key,
                        {
                            "buffer": bytearray(command["total_length"]),
                            "received": set(),
                            "count": command["fragment_count"],
                        },
                    )
                    start = command["fragment_offset"]
                    end = start + len(app)
                    if end > len(bucket["buffer"]):
                        errors.append({"line": line_number, "client": client, "error": "fragment exceeds total length"})
                        continue
                    bucket["buffer"][start:end] = app
                    bucket["received"].add(command["fragment_number"])
                    if len(bucket["received"]) != bucket["count"]:
                        continue
                    app = bytes(bucket["buffer"])
                    del fragments[fragment_key]
                    command["reassembled"] = True
                if not app:
                    continue
                event: dict[str, object] = {
                    "line": line_number,
                    "elapsed": elapsed,
                    "client": client,
                    "direction": capture["direction"],
                    **command,
                    "app_id": app[0],
                    "app_length": len(app),
                }
                if app[0] == ID_JOIN_SUCCESS and len(app) >= 5:
                    state["local_ip"] = app[1:5]
                    event["event"] = "room_join_success"
                    event["local_ip"] = ".".join(map(str, app[1:5]))
                elif app[0] == ID_LDN_PACKET and len(app) >= 15:
                    ldn = parse_ldn(app)
                    event["event"] = "ldn"
                    event.update({key: value for key, value in ldn.items() if key != "data"})
                    data = ldn["data"]
                    event["data_length"] = len(data)
                    if ldn["kind"] == LDN_SCAN_RESPONSE and len(data) >= 0x20:
                        keys = sv.session_keys(data[0x10:0x20])
                        state["keys"] = keys
                        event["event"] = "ldn_scan_response"
                        event["ssid"] = keys.ssid.hex()
                        event["network_id"] = keys.network_id
                elif app[0] == ID_PROXY_PACKET and len(app) >= 21:
                    event["event"] = "proxy"
                    keys = state.get("keys")
                    if keys is None:
                        event["error"] = "proxy before session keys"
                    else:
                        source_ip, remote_ip, raw = parse_proxy(app)
                        event["source_ip"] = ".".join(map(str, source_ip))
                        event["remote_ip"] = ".".join(map(str, remote_ip))
                        event["pia_length"] = len(raw)
                        header, plain, footer = pia6.parse_packet(
                            keys.session_key, source_ip, keys.network_id, raw
                        )
                        event["pia_header"] = repr(header)
                        event["pia_footer"] = json_value(footer)
                        event["authenticated"] = plain is not None
                        messages: list[dict[str, object]] = []
                        if plain is not None:
                            for message in pia6.parse_messages(plain):
                                item: dict[str, object] = {
                                    "protocol": message.protocol,
                                    "port": message.port,
                                    "flags": message.message_flags,
                                    "payload": message.payload.hex(),
                                }
                                if message.protocol in (0x7C, 0x80, 0x81) and len(message.payload) >= reliable5.HEADER_SIZE:
                                    try:
                                        parsed_reliable = reliable5.parse(message.payload)
                                        item["reliable"] = json_value(parsed_reliable)
                                        if (
                                            parsed_reliable["flags"] & reliable5.FLAG_APPLICATION_DATA
                                            and parsed_reliable["flags"] & reliable5.FLAG_ZLIB
                                        ):
                                            item["decompressed"] = streams.decompress(parsed_reliable["payload"]).hex()
                                    except Exception as exc:
                                        item["reliable_error"] = str(exc)
                                messages.append(item)
                                counters[f"pia_{message.protocol:02x}_port_{message.port}"] += 1
                        event["messages"] = messages
                else:
                    event["event"] = "room"
                    event["payload"] = app.hex()
                counters[f"app_{app[0]}"] += 1
                output.append(event)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for event in output:
            stream.write(json.dumps(event, separators=(",", ":")) + "\n")
    summary = {
        "capture": str(args.capture),
        "decoded_events": len(output),
        "clients": {
            client: {
                "local_ip": ".".join(map(str, state["local_ip"])) if state["local_ip"] else None,
                "has_keys": state["keys"] is not None,
            }
            for client, state in states.items()
        },
        "counters": dict(sorted(counters.items())),
        "errors": errors,
    }
    args.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
