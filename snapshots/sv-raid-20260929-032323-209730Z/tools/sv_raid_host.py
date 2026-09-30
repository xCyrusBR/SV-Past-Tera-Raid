#!/usr/bin/env python3
"""Advertise a Scarlet/Violet Tera Raid through pokeldn's physical radio host.

Phase 1 deliberately reuses the proven SV host transport and session machinery while replacing
the Link Trade advertisement with the captured Tera Raid shape.  It is a discovery/session probe,
not yet a claim that the battle protocol is complete.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import runpy
import sys


ROOT = Path(__file__).resolve().parents[1]
POKELDN = ROOT.parent / "pokeldn-research"
SV_HOST = POKELDN / "bin" / "sv_host.py"
DEFAULT_KEYS = Path.home() / ".switch" / "prod.keys"
LAB_KEYS = ROOT / "lab" / "eden-participant" / "user" / "keys" / "prod.keys"
DEFAULT_RECORD_SET = ROOT / "lab" / "mewtwo-host-records"
DEFAULT_REFERENCE_CAPTURE = ROOT / "lab" / "eden-two-client-raid-decoded.jsonl"
LOBBY_STATE_DELAY = 3.20
LOBBY_TIMING_SHIFT = LOBBY_STATE_DELAY - 2.00
# In the working Eden pair the host publishes Session update 0 immediately, then update 1 at
# +49.105 s: 1.05 s before the fragmented 0x80332f battle-start record.  The late update is the
# roster commit.  Publishing only update 1 at join time left Violet with invisible fallback NPCs.
SESSION_ROSTER_COMMIT_DELAY = 49.05
DEFAULT_MEW = Path(os.environ.get("SV_RAID_MEW", ROOT / "lab" / "host-mew.pk9"))

# Opening burst captured from the real Mewtwo host.  The 0x80:2 station announcement remains
# generated dynamically by sv_host because it contains this run's station id and IP address.
RAID_OPENING_SENDS = (
    "0.10:0x81:5:000500000ff00800000000",
    "0.14:0x7c:1:484bdac9c8b69369275335032388326284504c108a194c3534184369134600000000ffff030036430d09:z",
    "0.14:0x7c:2:484b62dbc90a846cac2c0c7b381960604f4303c3c0839d8ccd0c0c4c0c2b18190f30ec6241e2ed646480a03d2c20758c0c00000000ffff0300570c0dcb:z",
    "0.18:0x81:1:0000000000f38800000000",
    "3.20:0x80:0:80333001a7000000000014000000000000000c0000000000060008000400060000008b000000",
    "3.24:0x80:0:484b6a30d6615cc100023a0c08300d89cd0ec4bc40cc08c45b9f4fad00891941e500000000ffff0300a717053b:z",
    "3.28:0x80:0:80332d01a900000000000c00000000000000080000000400040004000000",
    "3.32:0x80:0:80332e01aa00000000005801000000000000" + "00" * 344,
)


def raid_countdown_sends(count: int = 39) -> tuple[str, ...]:
    """Continue the real host's 0x80:0 lobby heartbeat through sequence 43."""
    template = bytearray.fromhex(
        "80333001ab000000000014000000000000000c0000000000060008000400060000008a000000"
    )
    sends = []
    for index in range(count):
        payload = bytearray(template)
        payload[4] = (0xAB + index) & 0xFF
        payload[34] = max(0, 0x8A - index)
        sends.append(f"{3.00 + LOBBY_TIMING_SHIFT + index:.2f}:0x80:0:{payload.hex()}")
    return tuple(sends)


def patch_host_trainer_announce(spec: str, pokemon_module, mew: Path) -> str:
    """Replace the captured host's selected and battle Pokemon with PR's Mew."""
    delay, protocol, port, raw = spec.split(":", 3)
    if protocol == "skip":
        return spec
    encoded, *suffixes = raw.split(":")
    data = bytearray.fromhex(encoded)
    if data.startswith(b"\x80\x33\x2e") and len(data) == 362:
        pokemon_offset = 18
    else:
        return spec
    selected = mew.read_bytes()
    if len(selected) != 344:
        raise ValueError(f"Mew must be a 344-byte PK9, got {len(selected)}")
    data[pokemon_offset:pokemon_offset + 344] = pokemon_module.encrypt(
        pokemon_module.load(selected))
    suffix = "" if not suffixes else ":" + ":".join(suffixes)
    return f"{delay}:{protocol}:{port}:{data.hex()}{suffix}"


def host_identity(name: str, full_id: int) -> tuple[str, str]:
    """Encode the host trainer independently of the Pokemon they selected.

    A traded Pokemon may retain another OT and ID. The kind-1 identity describes the
    trainer occupying the host seat, not necessarily the PK9's original trainer.
    """
    if not name:
        raise ValueError("host trainer has no name")
    if not 0 <= full_id <= 0xFFFFFFFF:
        raise ValueError("host trainer ID must be a 32-bit unsigned integer")
    return (full_id.to_bytes(4, "little") + bytes(12)).hex(), name


def session_sequence_args(base: int) -> list[str]:
    """Keep join response and first roster update on the same generation."""
    if base not in (0, 1):
        raise ValueError("Session sequence base must be 0 or 1")
    return ["--join-seq", str(base), "--update-first-seq", str(base),
            "--update-seq", str(base + 1)]


def _fragment_suffix(flag_names: tuple[str, ...] | list[str]) -> str:
    """Encode the reference reliable boundary flags without turning fragments into wholes."""
    names = set(flag_names)
    suffixes = []
    if "ZLIB" in names:
        suffixes.append("z")
    start, end = "START" in names, "END" in names
    if start != end:
        suffixes.append("start" if start else "end")
    elif not start:
        suffixes.append("middle")
    return "" if not suffixes else ":" + ":".join(suffixes)


def raid_reference_sends(capture: Path = DEFAULT_REFERENCE_CAPTURE,
                         first: int = 44, last: int = 219) -> tuple[str, ...]:
    """Replay the complete successful Eden host transition with exact stream boundaries.

    The old implementation stopped at sequence 70 and flattened fragmented records 52/53 and
    69/70 into independent complete messages.  The working Eden session continues through 219
    and deliberately leaves sequence gaps after large state records.  Both details are observable
    receiver state, so this routine preserves flags, gaps and timing from the first occurrence of
    every host record while ignoring retransmissions.
    """
    found: list[tuple[float, int, int, str, tuple[str, ...]]] = []
    seen: set[tuple[int, int, str, tuple[str, ...]]] = set()
    for line in capture.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("event") != "proxy" or row.get("source_ip") != "192.168.1.1":
            continue
        for message in row.get("messages", ()):
            reliable = message.get("reliable") or {}
            sequence = reliable.get("sequence_id")
            if (message.get("protocol"), message.get("port")) != (0x80, 0):
                continue
            if sequence is None or not first <= sequence <= last or reliable.get("is_ack"):
                continue
            low = int(reliable["lowest_pending"])
            payload = reliable["payload"]
            flag_names = tuple(reliable.get("flag_names", ()))
            key = (sequence, low, payload, flag_names)
            if key in seen:
                continue
            seen.add(key)
            found.append((float(row["elapsed"]), sequence, low, payload, flag_names))
    sequences = {item[1] for item in found}
    if first not in sequences or last not in sequences:
        raise ValueError(f"reference capture lacks boundary sequence {first} or {last}")
    origin = next(item[0] for item in found if item[1] == first)
    base = 42.70
    sends = []
    for elapsed, sequence, low, payload, flag_names in found:
        due = base + elapsed - origin
        sends.append(
            f"{due:.3f}:0x80:0:{payload}{_fragment_suffix(flag_names)}"
            f":seq={sequence}:low={low}"
        )
    return tuple(sends)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(POKELDN))

from past_raids.raid_wire import (  # noqa: E402
    RAID_MAX_PARTICIPANTS,
    RAID_SCENE_ID,
    build_raid_advertise_data,
)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--code", default="0000", help="four-digit local raid link code")
    ap.add_argument("--seconds", type=float, default=240.0)
    ap.add_argument("--channel", type=int, choices=(1, 6, 11), default=6)
    ap.add_argument("--violet", action="store_true",
                    help="advertise Violet's local communication id")
    ap.add_argument("--port", default="COM4", help="ESP32-S3 native USB serial port")
    ap.add_argument("--mew", type=Path, default=DEFAULT_MEW,
                    help="PR's 344-byte support Mew PK9 for the host's first party slot")
    ap.add_argument("--host-name", default="PR", help="host trainer name, independent of the PK9 OT")
    ap.add_argument("--host-id", type=lambda value: int(value, 0), default=4294423561,
                    help="host trainer's 32-bit full ID (PR: 4294423561), independent of the PK9")
    ap.add_argument("--keys", default=None, help="prod.keys (auto-detected when omitted)")
    ap.add_argument("--capture", default=str(ROOT / "lab" / "sv-raid-radio.jsonl"))
    ap.add_argument("--record-set", default=str(DEFAULT_RECORD_SET),
                    help="captured host identity/state records; empty disables them")
    ap.add_argument("--lobby-only", action="store_true",
                    help="send only the opening lobby state; do not replay ready/start/battle state")
    ap.add_argument("--no-port2-announce", action="store_true",
                    help="omit the synthetic port-2 type 7; Violet joined without it in 7284 "
                         "after the type-6 host IDs were corrected")
    ap.add_argument("--port2-announce-slot", type=int, choices=(0, 1), default=1,
                    help="diagnostic slot encoded in the optional type-7 announcement")
    ap.add_argument("--session-seq-base", type=int, choices=(0, 1), default=1,
                    help="Session join/first-update generation; 0 matches the two-Eden capture, "
                         "1 preserves the physical-lobby baseline")
    ap.add_argument("--session-message-flags", type=int, choices=(0, 1), default=1,
                    help="Session reply message flags; 0 matches Eden, 1 preserves the "
                         "physical-lobby baseline")
    ap.add_argument("--omit-session-ack", action="store_true",
                    help="diagnostic only: omit the type-1 Session join ACK absent from the "
                         "working two-Eden capture")
    ap.add_argument("--dry-run", action="store_true")
    return ap


def main() -> int:
    args = parser().parse_args()
    if len(args.code) != 4 or not args.code.isdigit():
        raise SystemExit("--code must contain exactly four decimal digits")
    if not SV_HOST.is_file():
        raise SystemExit(f"missing pokeldn host: {SV_HOST}")
    keys = Path(args.keys).expanduser() if args.keys else (
        DEFAULT_KEYS if DEFAULT_KEYS.is_file() else LAB_KEYS
    )
    if not keys.is_file():
        raise SystemExit("prod.keys not found; pass its path with --keys")
    if not args.mew.is_file():
        raise SystemExit(f"Mew PK9 not found: {args.mew}")

    print(f"[raid] ESP32-S3={args.port} scene={RAID_SCENE_ID} code={args.code} channel={args.channel}")
    if args.dry_run:
        print("[raid] dry run: radio was not opened")
        return 0

    os.environ["POKELDN_RADIO"] = f"esp32:{args.port}"
    namespace = runpy.run_path(str(SV_HOST), run_name="pokeldn_sv_host")
    # sv_host's root check is meaningful on Linux.  Windows has no geteuid and
    # the ESP32 transport does not require process elevation.
    if not hasattr(os, "geteuid"):
        os.geteuid = lambda: 0  # type: ignore[attr-defined]
    sv = namespace["sv"]
    session_module = sys.modules[sv.build_advertise_data.__module__]
    build_pia_header = session_module.build_pia_header
    pokemon_module = namespace["pokemon"]
    host_player_id, host_player_name = host_identity(args.host_name, args.host_id)

    def raid_advertise(*, password: bytes | None = None, num_players: int = 1,
                       game_data=None) -> bytes:
        del game_data
        return build_raid_advertise_data(
            build_pia_header,
            args.code,
            password=password,
            num_players=num_players,
        )

    sv.SCENE_ID = RAID_SCENE_ID
    sv.MAX_PARTICIPANTS = RAID_MAX_PARTICIPANTS
    sv.build_advertise_data = raid_advertise
    sys.argv = [
        str(SV_HOST),
        "--seconds", str(args.seconds),
        "--channel", str(args.channel),
        "--keys", str(keys),
        "--capture", args.capture,
        "--player-name", host_player_name,
        "--host-player-name", host_player_name,
        # The game-level kind-1 ID describes PR, not necessarily the selected Pokemon's OT.
        # Pia PlayerInfo is a separate layer: the
        # successful two-Eden capture uses the same neutral id and one-space name for both seats.
        "--host-player-id", host_player_id,
        "--session-host-player-id", "a5b9defccd3b551fb249360d27546e03",
        "--session-host-player-name", " ",
        "--session-console-player-id", "a5b9defccd3b551fb249360d27546e03",
        "--session-console-player-name", " ",
        "--session-flags", str(args.session_message_flags),
        # The working offline host's kind-1 account field is all zero. Do not invent an online
        # account for PR; patch only the trainer ID/name and preserve the captured offline field.
        "--host-account-id", "",
        "--rtt-probe",
        "--net-property",
        "--clock",
        "--net-stations", "4",
        "--scarlet-response",
        # Preserve the two Session station-list generations observed in the successful Eden pair.
        # Update 0 establishes the lobby; update 1 commits the same two stations immediately before
        # battle start.  The standalone radio host must retain its establishing flag and type-1
        # acknowledgement even though ldn_mitm makes those implicit in the Eden trace.
        # The radio baseline uses generations 1/2; --session-seq-base 0 isolates the reference
        # generations 0/1 without also changing transport flags, type-1 ACK or game records.
        *session_sequence_args(args.session_seq_base),
        "--update-delay", str(SESSION_ROSTER_COMMIT_DELAY),
        # The working two-Eden raid sent type 9 accept but no type 7 announce. Earlier no-type-7
        # A/B 2846 stalled with stale type-6 IDs; after fixing them, 7284 joined without type 7.
        "--accept-port2-join",
        "--patch-record-identity",
        # The first PK9 in 0x80332f is local to the receiving player, not the host.  Capture the
        # Violet's 0x80332e selection and put that Pokemon into the battle-start record.  PR's Mew
        # remains in the separate host lobby announcement patched above.
        "--patch-raid-pokemon",
    ]
    if not args.lobby_only:
        # The reference's first battle-transition record followed the guest's Ready by 4.62 s.
        # A fixed +42.7 s schedule can otherwise begin *before* a human presses Ready.
        sys.argv.extend(["--raid-ready-gate-after", "42.7", "--raid-ready-lead", "4.6"])
    if not args.no_port2_announce:
        sys.argv.extend(["--announce", "--announce-delay", "3.0",
                         "--announce-slot", str(args.port2_announce_slot)])
    if args.omit_session_ack:
        sys.argv.append("--no-session-ack")
    for spec in RAID_OPENING_SENDS:
        spec = patch_host_trainer_announce(spec, pokemon_module, args.mew)
        sys.argv.extend(["--send-at", spec])
    # The countdown records are part of a live lobby, not the battle transition.
    # Keep them in diagnostic mode so a valid lobby still displays and advances time.
    for spec in raid_countdown_sends(139 if args.lobby_only else 39):
        sys.argv.extend(["--send-at", spec])
    if not args.lobby_only:
        for spec in raid_reference_sends():
            spec = patch_host_trainer_announce(spec, pokemon_module, args.mew)
            sys.argv.extend(["--send-at", spec])
    if args.record_set:
        record_set = Path(args.record_set)
        if not record_set.is_dir():
            raise SystemExit(f"raid record set not found: {record_set}")
        sys.argv.extend(["--record-set", str(record_set), "--record-delay", "0.35"])
    if args.violet:
        sys.argv.append("--violet")
    return int(namespace["main"]() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
