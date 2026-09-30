#!/usr/bin/env python3
"""Compare guest 0x81:1 records in two private decoded Eden captures.

Only record numbers, lengths, and change counts are printed; captured bodies stay private.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


POKELDN = Path(__file__).resolve().parents[2] / "pokeldn-research"
sys.path.insert(0, str(POKELDN))
from pokeldn.sv import streams  # noqa: E402


def guest_records(path: Path, guest_ip: str = "192.168.1.2") -> dict[int, bytes]:
    records: dict[int, bytes] = {}
    with path.open(encoding="utf-8") as capture:
        for line in capture:
            row = json.loads(line)
            if row.get("event") != "proxy" or row.get("source_ip") != guest_ip:
                continue
            for message in row.get("messages", ()):
                if (message.get("protocol"), message.get("port")) != (0x81, 1):
                    continue
                reliable = message.get("reliable") or {}
                if reliable.get("is_ack") or not reliable.get("payload"):
                    continue
                seq = int(reliable["sequence_id"])
                raw = bytes.fromhex(reliable["payload"])
                body = streams.decompress(raw) if reliable["flags"] & 0x10 else raw
                old = records.setdefault(seq, body)
                if old != body:
                    raise ValueError(f"guest record {seq} changed within {path.name}")
    return records


def compare(left: Path, right: Path) -> dict[str, object]:
    a, b = guest_records(left), guest_records(right)
    rows = []
    for seq in sorted(a.keys() | b.keys()):
        one, two = a.get(seq), b.get(seq)
        if one is None or two is None:
            rows.append({"seq": seq, "missing": "left" if one is None else "right"})
        elif one != two:
            rows.append({"seq": seq, "left_length": len(one), "right_length": len(two),
                         "changed_bytes": sum(x != y for x, y in zip(one, two)),
                         "length_delta": len(two) - len(one)})
    return {"left": left.name, "right": right.name,
            "left_record_count": len(a), "right_record_count": len(b),
            "changed_records": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.left, args.right), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
