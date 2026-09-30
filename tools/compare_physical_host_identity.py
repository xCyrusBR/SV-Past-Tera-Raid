#!/usr/bin/env python3
"""Compare a private physical-host kind-1 record with the Eden reference.

Print offsets only, never the trainer name, ID, account, or full record bytes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
POKELDN = ROOT.parent / "pokeldn-research"
sys.path.insert(0, str(POKELDN))

from pokeldn.sv import streams  # noqa: E402


def physical_kind1(path: Path) -> bytes:
    with path.open(encoding="utf-8") as capture:
        for line in capture:
            if '"rec": "data"' not in line:
                continue
            row = json.loads(line)
            if (row.get("protocol"), row.get("port"), row.get("seq")) != (0x81, 0, 1):
                continue
            plain = row.get("plain")
            data = (bytes.fromhex(plain) if plain else
                    streams.decompress(bytes.fromhex(row["payload"])))
            if len(data) != 1395 or data[0] != 1:
                raise ValueError("physical sequence 1 is not a kind-1 identity record")
            return data
    raise ValueError("no physical-host kind-1 record found")


def compare(physical_capture: Path, eden_record: Path) -> dict[str, object]:
    physical = physical_kind1(physical_capture)
    eden = streams.decompress(eden_record.read_bytes())
    if len(eden) != 1395 or eden[0] != 1:
        raise ValueError("Eden sequence 1 is not a kind-1 identity record")
    identity_fields = set(range(11, 67))
    changes = [index for index, (a, b) in enumerate(zip(physical, eden)) if a != b]
    other = [index for index in changes if index not in identity_fields]
    # Large save-specific appearance blocks can otherwise dump hundreds of offsets. Group
    # adjacent changes so the report remains useful without exposing captured bytes.
    spans: list[list[int]] = []
    for index in other:
        if spans and index == spans[-1][1] + 1:
            spans[-1][1] = index
        else:
            spans.append([index, index])
    return {
        "physical_capture": physical_capture.name,
        "eden_record": eden_record.name,
        "record_length": len(physical),
        "changed_bytes": len(changes),
        "changed_identity_bytes": len(changes) - len(other),
        "changed_other_span_count": len(spans),
        "changed_other_spans_preview": spans[:20],
        "changed_other_spans_truncated": len(spans) > 20,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("physical_capture", type=Path)
    parser.add_argument("eden_record", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.physical_capture, args.eden_record), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
