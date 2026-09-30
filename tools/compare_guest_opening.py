#!/usr/bin/env python3
"""Compare the first guest game record in Eden and physical Violet captures.

Input captures stay private; output reports only message shape and changed offsets.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


POKELDN = Path(__file__).resolve().parents[2] / "pokeldn-research"
sys.path.insert(0, str(POKELDN))
from pokeldn.sv import streams  # noqa: E402


def _plain(value: str) -> bytes:
    payload = bytes.fromhex(value)
    return streams.decompress(payload) if payload.startswith(b"HK") else payload


def eden_guest_opening(path: Path, guest_ip: str = "192.168.1.2") -> bytes:
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("event") != "proxy" or row.get("source_ip") != guest_ip:
            continue
        for message in row.get("messages", ()):
            reliable = message.get("reliable") or {}
            if ((message.get("protocol"), message.get("port")) == (0x80, 0)
                    and reliable.get("sequence_id") == 1 and not reliable.get("is_ack")):
                return _plain(reliable["payload"])
    raise ValueError("Eden guest opening record not found")


def radio_guest_opening(path: Path) -> bytes:
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if (row.get("rec") == "data" and row.get("protocol") == 0x80
                and row.get("port") == 0 and row.get("seq") == 1):
            return _plain(row["payload"])
    raise ValueError("radio guest opening record not found")


def compare(left: bytes, right: bytes) -> dict[str, object]:
    changed = [i for i, (a, b) in enumerate(zip(left, right)) if a != b]
    return {
        "eden_length": len(left),
        "radio_length": len(right),
        "eden_prefix": left[:3].hex(),
        "radio_prefix": right[:3].hex(),
        "changed_count": len(changed),
        "changed_offsets": changed[:120],
        "changed_offsets_truncated": len(changed) > 120,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("eden_decoded", type=Path)
    parser.add_argument("radio_capture", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(eden_guest_opening(args.eden_decoded),
                             radio_guest_opening(args.radio_capture)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
