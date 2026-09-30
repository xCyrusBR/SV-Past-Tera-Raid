#!/usr/bin/env python3
"""Summarize authenticated SV selected-Pokémon messages in a private radio capture.

This does not export SSIDs, session keys, trainer identifiers, or PK9 bytes. It
reads the host's existing JSONL capture and reports source/sequence/species.
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
from pokeldn.ldn import pia6, pia_connect, reliable5  # noqa: E402
from pokeldn.sv import pokemon, streams  # noqa: E402


def summarize(path: Path) -> dict[str, object]:
    rows = (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
    host = next(rows)
    if host.get("rec") != "host":
        raise ValueError("capture does not begin with its host/session record")
    keys = sv.session_keys(bytes.fromhex(host["ssid"]))
    host_ip = host["our_ip"]
    found: list[dict[str, object]] = []
    seen: set[tuple[str, int, str]] = set()
    authenticated = 0
    join_vars: dict[str, int] | None = None
    first_time: float | None = None
    for row in rows:
        if row.get("rec") not in ("in", "out") or "hex" not in row:
            continue
        source = row.get("src") if row["rec"] == "in" else host_ip
        raw = bytes.fromhex(row["hex"])
        try:
            header, plain, _footer = pia6.parse_packet(
                keys.session_key, socket.inet_aton(source), keys.network_id, raw)
        except (ValueError, IndexError):
            continue
        if plain is None:
            continue
        authenticated += 1
        when = float(row["t"])
        if first_time is None:
            first_time = when
        for message in pia6.parse_messages(plain):
            if message.protocol == 0x98 and message.payload and join_vars is None:
                try:
                    join = pia_connect.parse_session_join_v11(message.payload)
                except (ValueError, IndexError):
                    join = None
                if join is not None:
                    join_vars = {"host": join["destination_var"],
                                 "guest": join["source_var"]}
            if (message.protocol, message.port) != (0x80, 0):
                continue
            try:
                reliable = reliable5.parse(message.payload)
            except ValueError:
                continue
            if reliable["is_ack"]:
                continue
            data = reliable["payload"]
            if reliable["flags"] & reliable5.FLAG_ZLIB:
                data = streams.decompress(data)
            if not data.startswith(bytes.fromhex("80332e")):
                continue
            if len(data) != 362:
                raise ValueError(f"selection size {len(data)} from {source}")
            block = data[18:]
            digest = hashlib.sha256(block).hexdigest()
            sequence = reliable["sequence_id"]
            key = (source, sequence, digest)
            if key in seen:
                continue
            seen.add(key)
            fields = pokemon.read(pokemon.load(block))
            found.append({
                "elapsed_from_first_pia": round(when - first_time, 3),
                "direction": row["rec"],
                "source_role": "host" if source == host_ip else "guest",
                "sequence": sequence,
                "message_counter": data[4],
                "pia_src_var": header.src_var,
                "pia_dst_var": header.dst_var,
                "destination_bitmap": reliable["bitmap"],
                "message_flags": message.message_flags,
                "reliable_flags": reliable["flags"],
                "lowest_pending": reliable["lowest_pending"],
                "species": fields["species"],
                "pk9_sha256": digest,
            })
    return {"capture": path.name, "authenticated_pia_packets": authenticated,
            "join_variable_ids": join_vars,
            "selections": found}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.capture), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
