#!/usr/bin/env python3
"""Compare normalized Eden and physical-host Session station lists.

Inputs remain private. Output excludes station IDs, IPs, tokens and PlayerInfo IDs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import sys


POKELDN = Path(__file__).resolve().parents[2] / "pokeldn-research"
sys.path.insert(0, str(POKELDN))

from pokeldn import sv  # noqa: E402
from pokeldn.ldn import pia6, pia_connect  # noqa: E402


def describe(payload: bytes) -> dict[str, object]:
    parsed = pia_connect.parse_session_update_v11(payload, route_bytes=0)
    if not parsed or parsed.get("truncated"):
        raise ValueError("invalid Session update")
    stations = parsed["stations"]
    return {
        "sequence": parsed["sequence_id"],
        "count": len(stations),
        "header_host_matches_first": bool(stations and
                                          parsed["host_constant_id"] == stations[0]["constant_id"] and
                                          parsed["host_var"] == stations[0]["variable_id"]),
        "stations": [{
            "index": station["station_index"],
            "join_order": station["join_order"],
            "route": station["route"],
            "port": station["port"],
            "nat": station["nat"],
            "private_ipv6": station["private_ipv6"],
            "token_zero": not any(station["token"]),
            "participants": station["participants"],
            "player_count": len(station["players"]),
        } for station in stations],
        "player_ids_equal": (len(stations) == 2 and
                             len(stations[0]["players"]) == len(stations[1]["players"]) == 1 and
                             stations[0]["players"][0]["player_id"] ==
                             stations[1]["players"][0]["player_id"]),
    }


def eden_updates(path: Path, host_ip: str = "192.168.1.1") -> list[dict[str, object]]:
    found = []
    seen = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("event") != "proxy" or row.get("source_ip") != host_ip:
            continue
        for message in row.get("messages", ()):
            payload = bytes.fromhex(message.get("payload", ""))
            if message.get("protocol") != 0x98 or not payload.startswith(b"\x05"):
                continue
            if payload in seen:
                continue
            seen.add(payload)
            found.append(describe(payload))
    return found


def radio_updates(path: Path) -> list[dict[str, object]]:
    rows = (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
    host = next(rows)
    keys = sv.session_keys(bytes.fromhex(host["ssid"]))
    found = []
    seen = set()
    for row in rows:
        if row.get("rec") != "out" or row.get("kind") != "session update":
            continue
        _header, plain, _footer = pia6.parse_packet(
            keys.session_key, socket.inet_aton(host["our_ip"]), keys.network_id,
            bytes.fromhex(row["hex"]))
        if plain is None:
            raise ValueError("unauthenticated host Session update")
        for message in pia6.parse_messages(plain):
            if message.protocol != 0x98 or not message.payload.startswith(b"\x05"):
                continue
            if message.payload in seen:
                continue
            seen.add(message.payload)
            found.append(describe(message.payload))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("eden_decoded", type=Path)
    parser.add_argument("radio_capture", type=Path)
    args = parser.parse_args()
    print(json.dumps({"eden": eden_updates(args.eden_decoded),
                      "physical": radio_updates(args.radio_capture)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
