#!/usr/bin/env python3
"""Compare the first host 0x80:0 game records in two decoded Eden captures.

Reports only changed offsets and lengths, not private packet payloads.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


TYPES = {bytes.fromhex(value) for value in ("80332c", "80332d", "80332e", "803330")}


def first_records(path: Path, host_ip: str = "192.168.1.1") -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("event") != "proxy" or row.get("source_ip") != host_ip:
            continue
        for message in row.get("messages", ()):
            if (message.get("protocol"), message.get("port")) != (0x80, 0):
                continue
            reliable = message.get("reliable") or {}
            if reliable.get("is_ack"):
                continue
            data = bytes.fromhex(message.get("decompressed") or reliable.get("payload", ""))
            kind = data[:3]
            if kind in TYPES:
                found.setdefault(kind.hex(), data)
        if len(found) == len(TYPES):
            break
    return found


def compare(left: Path, right: Path) -> list[dict[str, object]]:
    a, b = first_records(left), first_records(right)
    result = []
    for kind in sorted(TYPES):
        key = kind.hex()
        x, y = a.get(key), b.get(key)
        if x is None or y is None:
            result.append({"type": key, "missing": "left" if x is None else "right"})
            continue
        changes = [index for index, (one, two) in enumerate(zip(x, y)) if one != two]
        result.append({"type": key, "left_length": len(x), "right_length": len(y),
                       "changed_count": len(changes), "changed_offsets": changes[:100],
                       "changed_offsets_truncated": len(changes) > 100})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.left, args.right), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
