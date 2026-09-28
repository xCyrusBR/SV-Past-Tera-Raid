# Scarlet/Violet local Tera Raid synthetic-host research

Research prototype for hosting an offline local Tera Raid for an unmodified Nintendo Switch using a PC and an ESP32-S3 radio. This is **not yet a playable host**. It is intended for protocol review and reproducible experiments, not distribution of game content.

## Verified state (2026-09-28)

- A physical Violet client can discover and join the synthetic local lobby.
- The client sends a real Ready event. The host now waits for it before sending the battle transition.
- The client reaches the Mewtwo scene but has not shown a running battle timer or move-selection menu. The roster is wrong: PR/Mew may appear late or in the wrong slot, while two allies appear invisible and Pokémon are duplicated.
- A separate two-Eden Scarlet 4.0.0 run reached a battle with both real clients. Its capture is the protocol reference; the raw capture is **not** part of this public snapshot.
- The experimental Eden-to-Switch bridge is a separate track. Association alone is not a game connection.

See `docs/PROGRESS.md` for the latest measured milestones, `docs/EDEN-REFERENCE-REPLAY.md` for the replay design, `docs/ROSTER-AUDIT.md` for the offline identity/slot comparison, and `docs/RELATED-WORK.md` for related project boundaries. Please do not report lobby entry or received ACKs as a playable raid.

## Layout

- `tools/sv_raid_host.py`: raid-specific wrapper and reference replay.
- `past_raids/raid_wire.py`: raid advertisement construction.
- `tests/test_sv_raid_host.py`: replay/identity checks; some tests require a private reference capture.
- `pokeldn_overlay/`: modified files from [Decryptu/pokeldn](https://github.com/Decryptu/pokeldn), under its AGPL-3.0 license. These files are provided for review; they are **not** a complete replacement for that repository.

## Reproducing locally

1. Use Windows with the ESP32-S3 native USB interface and a compatible, locally built radio firmware. This snapshot does not contain firmware binaries.
2. Keep this folder beside a compatible `pokeldn-research` checkout. Review the overlay and integrate its changes into that checkout. The overlay alone may not include every local ESP32 adaptation; do not blindly overwrite a working installation.
3. Supply your own legally obtained `prod.keys` at `%USERPROFILE%\.switch\prod.keys` (or pass `--keys`), a 344-byte host PK9 at `lab/host-mew.pk9` (or pass `--mew`), and your own decoded two-client reference at `lab/eden-two-client-raid-decoded.jsonl`. None is included here. The script also expects a locally captured `lab/mewtwo-host-records/` record set.
4. From this folder, run `py tools/sv_raid_host.py --code 1234 --seconds 240 --capture lab/test.jsonl --host-name PR --host-id 4294423561`. The host ID is the trainer's 32-bit ID, independent of the selected Pokémon's OT/ID.
5. On Violet, use the offline local-raid code. Observe both trainer slots before Ready, then the running battle timer and move menu. Stop the host with Ctrl+C after recording the result.

The project currently relies on a private reference capture and is **not plug-and-play** for another researcher. The most useful contribution is a decoded, legally shareable two-client comparison of the Session station list, player identity records, port-2 messages, and `0x80:0` game records around lobby admission and battle start.

## Safety and publication

Never upload ROMs, game updates, saves, PK9 files, console keys, raw radio traces, Discord/chat exports, or unreviewed captures. This snapshot uses an allowlist; `lab/`, `source-materials/`, and `artifacts/` from the private workspace are intentionally absent. Review `MANIFEST.json` before uploading this **snapshot folder only**. Do not upload the parent workspace directory.

The `pokeldn_overlay/` files retain the upstream AGPL-3.0 licensing terms in `LICENSE-POKELDN`. No license has been chosen for the project-specific code; the owner should select one before accepting code contributions.
