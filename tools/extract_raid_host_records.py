#!/usr/bin/env python3
"""Extract the raid host's reliable 0x81:0 record set from an Eden proxy capture."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("capture", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--host-ip", default="192.168.1.1")
    ap.add_argument("--port", type=int, default=0,
                    help="0 for the host station stream, 1 for the first guest")
    ap.add_argument("--allow-any-set", action="store_true",
                    help="extract the observed sequence set without enforcing the known host set")
    args = ap.parse_args()

    records: dict[int, bytes] = {}
    order: list[int] = []
    for line in args.capture.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("event") != "proxy" or row.get("source_ip") != args.host_ip:
            continue
        for msg in row.get("messages", []):
            rel = msg.get("reliable") or {}
            if msg.get("protocol") != 0x81 or msg.get("port") != args.port:
                continue
            if rel.get("is_ack") or not rel.get("flag_names"):
                continue
            if "ZLIB" not in rel["flag_names"]:
                continue
            seq = int(rel["sequence_id"])
            payload = bytes.fromhex(rel["payload"])
            if seq in records:
                if records[seq] != payload:
                    raise SystemExit(f"sequence {seq} changed inside the capture")
                continue
            records[seq] = payload
            order.append(seq)

    if not args.allow_any_set and sorted(records) != list(range(1, 5)) + list(range(7, 47)):
        raise SystemExit(f"unexpected sequence set: {sorted(records)}")
    args.output.mkdir(parents=True, exist_ok=True)
    for seq, payload in records.items():
        (args.output / f"{seq:03d}.bin").write_bytes(payload)
    (args.output / "order").write_text(
        "".join(f"{seq}\n" for seq in order), encoding="ascii"
    )
    print(f"extracted {len(records)} records in captured order to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
