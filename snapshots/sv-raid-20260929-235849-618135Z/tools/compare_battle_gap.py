#!/usr/bin/env python3
"""Compare the host reliable-window jump near 70/85 in private Eden/radio captures.

Only header fields, payload lengths/digest equality, and ACK milestones are reported.
No captured payloads or station identities are printed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import socket
import sys


POKELDN = Path(__file__).resolve().parents[2] / "pokeldn-research"
sys.path.insert(0, str(POKELDN))
from pokeldn import sv  # noqa: E402
from pokeldn.ldn import pia6, reliable5  # noqa: E402


WATCH = set(range(69, 88))


def _record(message: dict[str, object], pia_flags: int) -> dict[str, object] | None:
    if (message["protocol"], message["port"]) != (0x80, 0):
        return None
    reliable = message["reliable"]
    if reliable["is_ack"] or reliable["sequence_id"] not in WATCH:
        return None
    raw_payload = reliable["payload"]
    payload = bytes.fromhex(raw_payload) if isinstance(raw_payload, str) else raw_payload
    return {"seq": reliable["sequence_id"], "low": reliable["lowest_pending"],
            "reliable_flags": reliable["flags"], "pia_flags": pia_flags,
            "bitmap": reliable["bitmap"], "payload_len": len(payload),
            "payload_sha256": hashlib.sha256(payload).hexdigest()}


def eden(path: Path) -> tuple[list[dict[str, object]], int | None]:
    records: dict[tuple[int, int], dict[str, object]] = {}
    high_ack: int | None = None
    with path.open(encoding="utf-8") as capture:
        for line in capture:
            row = json.loads(line)
            if row.get("event") != "proxy":
                continue
            for message in row.get("messages", ()):
                if row.get("source_ip") == "192.168.1.1":
                    entry = _record(message, int(message["flags"])) if message.get("reliable") else None
                    if entry:
                        records.setdefault((entry["seq"], entry["low"]), entry)
                elif (row.get("source_ip") == "192.168.1.2"
                      and (message.get("protocol"), message.get("port")) == (0x80, 0)):
                    reliable = message.get("reliable") or {}
                    if reliable.get("is_ack"):
                        for ack in reliable5.parse_ack_payload(
                                bytes.fromhex(reliable["payload"]))["entries"]:
                            if ack["stream_id"] == 0:
                                high_ack = max(high_ack or 0, ack["ack_id"])
    return sorted(records.values(), key=lambda item: (item["seq"], item["low"])), high_ack


def radio(path: Path) -> tuple[list[dict[str, object]], int | None]:
    records: dict[tuple[int, int], dict[str, object]] = {}
    high_ack: int | None = None
    with path.open(encoding="utf-8") as capture:
        host = json.loads(next(capture))
        keys = sv.session_keys(bytes.fromhex(host["ssid"]))
        for line in capture:
            row = json.loads(line)
            if (row.get("rec") == "out" and row.get("kind") == "send-at"
                    and (row.get("protocol"), row.get("port")) == (0x80, 0)
                    and row.get("seq") in WATCH):
                _header, plain, _footer = pia6.parse_packet(
                    keys.session_key, socket.inet_aton(host["our_ip"]), keys.network_id,
                    bytes.fromhex(row["hex"]))
                if plain is None:
                    raise ValueError("unauthenticated host packet")
                for message in pia6.parse_messages(plain):
                    rel = reliable5.parse(message.payload)
                    entry = _record({"protocol": message.protocol, "port": message.port,
                                     "reliable": rel}, message.message_flags)
                    if entry:
                        records.setdefault((entry["seq"], entry["low"]), entry)
            elif (row.get("rec") == "msg" and row.get("protocol") == 0x80
                  and row.get("port") == 0):
                rel = reliable5.parse(bytes.fromhex(row["payload"]))
                if rel["is_ack"]:
                    for ack in reliable5.parse_ack_payload(rel["payload"])["entries"]:
                        if ack["stream_id"] == 0:
                            high_ack = max(high_ack or 0, ack["ack_id"])
    return sorted(records.values(), key=lambda item: (item["seq"], item["low"])), high_ack


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("eden_capture", type=Path)
    parser.add_argument("radio_capture", type=Path)
    args = parser.parse_args()
    left, eden_ack = eden(args.eden_capture)
    right, radio_ack = radio(args.radio_capture)
    left_by_key = {(item["seq"], item["low"]): item for item in left}
    right_by_key = {(item["seq"], item["low"]): item for item in right}
    comparison = []
    for key in sorted(left_by_key.keys() | right_by_key.keys()):
        a, b = left_by_key.get(key), right_by_key.get(key)
        comparison.append({"seq": key[0], "low": key[1],
                           "present_eden": a is not None, "present_radio": b is not None,
                           "header_equal": (a is not None and b is not None and
                                            {k: v for k, v in a.items() if k != "payload_sha256"} ==
                                            {k: v for k, v in b.items() if k != "payload_sha256"}),
                           "header_changed_fields": ([field for field in a
                                                      if field != "payload_sha256" and
                                                      a[field] != b[field]]
                                                     if a is not None and b is not None else []),
                           "pia_flags_eden": a["pia_flags"] if a is not None else None,
                           "pia_flags_radio": b["pia_flags"] if b is not None else None,
                           "payload_equal": (a is not None and b is not None and
                                             a["payload_sha256"] == b["payload_sha256"])})
    print(json.dumps({"eden_ack_max": eden_ack, "radio_ack_max": radio_ack,
                      "host_packets": comparison}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
