#!/usr/bin/env python3
"""Compare the accepted two-Eden LDN opening with a saved NetworkInfo profile."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POKELDN = ROOT.parent / "pokeldn-research"
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(POKELDN))

from analyze_eden_capture import enet_payloads, parse_ldn  # noqa: E402
from pokeldn.ldn import ldn_mitm, ldn_mitm_host  # noqa: E402


def collect(capture: Path) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    fragments: dict[tuple[object, ...], dict[str, object]] = {}
    with capture.open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            row = json.loads(line)
            for command in enet_payloads(bytes.fromhex(row["hex"])):
                app = command["payload"]
                if command["command"] in (8, 12):
                    key = (
                        row["client"], row["direction"], command["channel"],
                        command["start_sequence"], command["total_length"],
                    )
                    bucket = fragments.setdefault(key, {
                        "buffer": bytearray(command["total_length"]),
                        "received": set(), "count": command["fragment_count"],
                    })
                    start = command["fragment_offset"]
                    bucket["buffer"][start:start + len(app)] = app
                    bucket["received"].add(command["fragment_number"])
                    if len(bucket["received"]) != bucket["count"]:
                        continue
                    app = bytes(bucket["buffer"])
                    del fragments[key]
                if len(app) < 15 or app[0] != 6:
                    continue
                ldn = parse_ldn(app)
                if ldn["kind"] not in (1, 3):
                    continue
                data = ldn["data"]
                if len(data) != ldn_mitm.NETWORK_INFO_SIZE:
                    continue
                events.append({
                    "line": line_no,
                    "client": row["client"],
                    "direction": row["direction"],
                    "kind": ldn["kind"],
                    "data": data,
                })
    return events


def describe(info: bytes) -> dict[str, object]:
    app = ldn_mitm.advertise_data(info)
    nodes = []
    for index in range(8):
        base = ldn_mitm_host.OFF_NODES + index * ldn_mitm.NODE_INFO_SIZE
        connected = info[base + 0x0B]
        if connected:
            ip, mac, node_id, _connected, name = ldn_mitm_host.read_node(info, index)
            nodes.append({
                "index": index,
                "node_id": node_id,
                "ip": ip,
                "mac": mac.hex(),
                "name": name.decode(errors="replace"),
                "version": ldn_mitm_host.node_local_comm_version(info, index),
            })
    return {
        "ssid": ldn_mitm.session_id(info).hex(),
        "host_mac": ldn_mitm.host_mac(info).hex(),
        "channel": int.from_bytes(info[ldn_mitm_host.OFF_CHANNEL:ldn_mitm_host.OFF_CHANNEL + 2], "little", signed=True),
        "node_count": info[ldn_mitm_host.OFF_NODE_COUNT],
        "node_count_max": info[ldn_mitm_host.OFF_NODE_COUNT_MAX],
        "app_data_len": len(app),
        "app_num_players": app[0x16] if len(app) > 0x16 else None,
        "raid_code": app[92:96].decode(errors="replace") if len(app) >= 96 else None,
        "nodes": nodes,
    }


def byte_diff(left: bytes, right: bytes) -> list[dict[str, object]]:
    spans = []
    start = None
    for pos, (a, b) in enumerate(zip(left, right)):
        if a != b and start is None:
            start = pos
        if a == b and start is not None:
            spans.append({"start": start, "end": pos, "left": left[start:pos].hex(), "right": right[start:pos].hex()})
            start = None
    if start is not None:
        spans.append({"start": start, "end": len(left), "left": left[start:].hex(), "right": right[start:].hex()})
    return spans


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("capture", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    events = collect(args.capture)
    canonical: list[dict[str, object]] = []
    seen: set[tuple[int, bytes]] = set()
    for event in events:
        key = (event["kind"], event["data"])
        if key in seen:
            continue
        seen.add(key)
        canonical.append({
            "line": event["line"], "kind": event["kind"],
            "client": event["client"], "direction": event["direction"],
            "fields": describe(event["data"]),
        })
    first_scan = next((e for e in events if e["kind"] == 1), None)
    first_sync = next((e for e in events if e["kind"] == 3), None)
    report = {
        "unique_network_infos": canonical,
        "scan_to_first_sync_diff": byte_diff(first_scan["data"], first_sync["data"])
        if first_scan and first_sync else [],
    }
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
