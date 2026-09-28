#!/usr/bin/env python3
"""Join a physical SV raid as the synthetic PR support-Mew participant."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import runpy
import sys


ROOT = Path(__file__).resolve().parents[1]
POKELDN = ROOT.parent / "pokeldn-research"
SV_JOIN = POKELDN / "bin" / "sv_join.py"
REFERENCE = ROOT / "lab" / "eden-two-client-raid-decoded.jsonl"
SOURCE_RECORDS = ROOT / "lab" / "mewtwo-guest-records"
PR_RECORDS = ROOT / "lab" / "pr-mew-guest-records"
PR_FILLED_RECORDS = ROOT / "lab" / "pr-mew-guest-records-filled"
KEYS = ROOT / "lab" / "eden-participant" / "user" / "keys" / "prod.keys"

OT = "PR"
DISPLAY_TID = 423561
DISPLAY_SID = 4294
# Session identity observed on the real Eden guest whose complete record set is replayed. This is
# not the Pokemon trainer ID; changing it independently made the game show the Mew but leave the
# trainer name at Searching.
PLAYER_ID = bytes.fromhex("a5b9defccd3b551fb249360d27546e03")


def patch_identity(streams, *, fill_record_gaps: bool = False) -> Path:
    destination = PR_FILLED_RECORDS if fill_record_gaps else PR_RECORDS
    destination.mkdir(parents=True, exist_ok=True)
    for source in SOURCE_RECORDS.glob("*.bin"):
        payload = source.read_bytes()
        if source.name == "001.bin":
            plain = bytearray(streams.decompress(payload))
            if len(plain) != 1395 or plain[0] != 1:
                raise ValueError("record 001 is not the expected identity record")
            name = OT.encode("utf-16le")
            plain[19:45] = bytes(26)
            plain[19:19 + len(name)] = name
            payload = streams.compress(plain)
        (destination / source.name).write_bytes(payload)
    order = [int(line) for line in (SOURCE_RECORDS / "order").read_text(encoding="ascii").splitlines()]
    if fill_record_gaps:
        # The real guest skips 5 and 6. A retail Violet host has repeatedly kept its receive
        # base at 5 while acknowledging every later record in its bitmap. This diagnostic uses
        # the captured kind-2 body as a structurally valid stand-in at each missing sequence.
        # It does not claim to reproduce the original game's opaque body content.
        template = streams.decompress((SOURCE_RECORDS / "004.bin").read_bytes())
        if len(template) != 1395 or template[:2] != b"\x02\x00":
            raise ValueError("unexpected kind-2 record template")
        for seq, index in ((5, 10), (6, 12)):
            body = bytearray(template)
            body[2] = index
            (destination / f"{seq:03d}.bin").write_bytes(streams.compress(body))
        order[order.index(4) + 1:order.index(4) + 1] = [5, 6]
    (destination / "order").write_text(
        "".join(f"{seq}\n" for seq in order), encoding="ascii"
    )
    return destination


def raid_identity_messages(pokemon, streams, mew: Path) -> tuple[bytes, bytes, bytes, bytes]:
    found: dict[int, bytes] = {}
    for line in REFERENCE.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("source_ip") != "192.168.1.2":
            continue
        for message in row.get("messages", ()):
            reliable = message.get("reliable") or {}
            sequence = reliable.get("sequence_id")
            if (message.get("protocol"), message.get("port")) != (0x80, 0):
                continue
            if sequence not in (1, 2, 3, 4) or reliable.get("is_ack") or sequence in found:
                continue
            plain = bytes.fromhex(message.get("decompressed") or reliable.get("payload"))
            if plain.startswith((b"\x80\x33\x2d", b"\x80\x33\x2e")):
                # Keep the state and ready messages in their captured compressed wire form.
                # Sequence 2 is uncompressed and is patched below with PR's selected Mew.
                found[sequence] = (plain if sequence == 2
                                   else bytes.fromhex(reliable["payload"]))
    if set(found) != {1, 2, 3, 4}:
        raise ValueError(f"reference lacks guest raid identity messages: {sorted(found)}")
    selected = bytearray(found[2])
    if not selected.startswith(b"\x80\x33\x2e") or len(selected) != 362:
        raise ValueError("guest 80332e template has an unexpected shape")
    raw = mew.read_bytes()
    if len(raw) != 344:
        raise ValueError(f"Mew must be a 344-byte PK9, got {len(raw)}")
    selected[18:] = pokemon.encrypt(pokemon.load(raw))
    if streams.decompress(found[4])[34:38] != b"\x0d\x00\x00\x00":
        raise ValueError("unexpected guest start response")
    return found[1], bytes(selected), found[3], found[4]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mew", type=Path, required=True)
    ap.add_argument("--fill-record-gaps", action="store_true",
                    help="diagnostic: send kind-2 stand-ins at skipped sequence ids 5 and 6")
    ap.add_argument("--ready", action="store_true",
                    help="send the captured guest ready message after joining the lobby")
    ap.add_argument("--seconds", type=int, default=210)
    ap.add_argument("--capture", type=Path,
                    default=ROOT / "lab" / "violet-physical-host-pr-mew.jsonl")
    args = ap.parse_args()

    sys.path.insert(0, str(POKELDN))
    from pokeldn.sv import pokemon, streams

    records = patch_identity(streams, fill_record_gaps=args.fill_record_gaps)
    state, selected, ready, start_response = raid_identity_messages(pokemon, streams, args.mew)
    print(f"[raid-guest] OT={OT} displayed TID={DISPLAY_TID} SID={DISPLAY_SID} "
          f"player_id={PLAYER_ID.hex()}")
    print(f"[raid-guest] {pokemon.describe(pokemon.load(args.mew.read_bytes()))}")
    if args.fill_record_gaps:
        print("[raid-guest] diagnostic: synthetic kind-2 records at sequence ids 5 and 6")

    sends = [
        "--send-on-open", f"0.15:0x80:0:{state.hex()}:z",
        "--send-on-open", f"0.17:0x80:0:{selected.hex()}",
    ]
    if args.ready:
        sends.extend(("--send-on-open", f"5.00:0x80:0:{ready.hex()}:z"))
        print("[raid-guest] captured ready message scheduled 5 seconds after lobby join")

    sys.argv = [
        str(SV_JOIN), "--seconds", str(args.seconds), "--hold", "180",
        # The game has two names for a joining station: the LDN node name and the
        # participant record inside the Pia Session join.  The former already was
        # PR; leaving the latter at sv_join's default single space produces the
        # observed lobby state where the selected Pokemon appears but its trainer
        # remains "Searching".
        "--name", OT, "--join-player-name", OT, "--platform", "1", "--session-join",
        "--join-player-id", PLAYER_ID.hex(), "--game-channel", "--port2-now",
        "--send-after-port2",
        "--record-set", str(records), "--record-delay", "0.9",
        "--record-spacing", "0.05",
        *(["--raid-start-response", start_response.hex()] if args.ready else []),
        *sends,
        "--keys", str(KEYS), "--capture", str(args.capture),
    ]
    runpy.run_path(str(SV_JOIN), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
