#!/usr/bin/env python3
"""Summarize selected-Pokémon announcements in a decoded two-Eden capture.

Both directions are considered because a capture may proxy only the guest; in
that case the host's original messages appear only on the server-to-client
relay. Source station and sequence deduplication prevent these relays and
retransmissions from becoming additional selections. The encrypted PK9 is
represented by a digest, never printed or exported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SELECTION_PREFIX = bytes.fromhex("80332e")
SELECTION_LENGTH = 362
PK9_OFFSET = 18
PK9_LENGTH = 344


def selections(path: Path) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    seen: set[tuple[str, int, str]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("event") != "proxy":
            continue
        source = row.get("source_ip")
        for message in row.get("messages", ()):
            if (message.get("protocol"), message.get("port")) != (0x80, 0):
                continue
            reliable = message.get("reliable") or {}
            if reliable.get("is_ack"):
                continue
            raw = bytes.fromhex(reliable.get("payload", ""))
            if not raw.startswith(SELECTION_PREFIX):
                continue
            if len(raw) != SELECTION_LENGTH:
                raise ValueError(f"unexpected selection size {len(raw)} at line {row.get('line')}")
            digest = hashlib.sha256(raw[PK9_OFFSET:PK9_OFFSET + PK9_LENGTH]).hexdigest()
            sequence = int(reliable["sequence_id"])
            key = (str(source), sequence, digest)
            if key in seen:
                continue
            seen.add(key)
            found.append({
                "elapsed": row["elapsed"],
                "source_ip": source,
                "sequence": sequence,
                "message_counter": raw[4],
                "pk9_sha256": digest,
            })
    return found


def summarize(path: Path) -> dict[str, object]:
    records = selections(path)
    first_by_station: dict[str, dict[str, object]] = {}
    last_by_station: dict[str, dict[str, object]] = {}
    for record in records:
        first_by_station.setdefault(str(record["source_ip"]), record)
        last_by_station[str(record["source_ip"])] = record
    first_digests = {record["pk9_sha256"] for record in first_by_station.values()}
    last_digests = {record["pk9_sha256"] for record in last_by_station.values()}
    return {
        "capture": path.name,
        "stations_with_selection": len(first_by_station),
        "first_selections_distinct": len(first_by_station) == 2 and len(first_digests) == 2,
        "latest_selections_distinct": len(last_by_station) == 2 and len(last_digests) == 2,
        "selections": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path, help="decoded Eden JSONL, kept private")
    args = parser.parse_args()
    print(json.dumps(summarize(args.capture), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
