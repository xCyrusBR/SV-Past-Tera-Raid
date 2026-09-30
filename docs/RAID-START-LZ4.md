# Raid start roster correction — 30 September 2026

Status: reproduced offline, 42 passing project tests, and physical test 8264 completed.
The transmitted roster is corrected, but physical gameplay remains incomplete.

## Evidence from two working Eden captures

The 26 September same-save `0x80332f` spans sequences 52/53. The 30 September distinct-save
capture spans 58/59. First reassemble reliable fragments, decompressing each fragment marked
ZLIB. Both application messages have an 18-byte header followed by an LZ4 block. The little-endian
size at header offset 10 is 2720; LZ4 decompression produces exactly that many bytes in both runs.

| Offset in decompressed body | Same-save capture | Distinct-save capture |
| --- | --- | --- |
| 0 | host Skeledirge (911) | host Skeledirge (911) |
| 344 | guest Skeledirge (911) | guest Iron Hands (992) |
| 688 | empty PK9 (0) | empty PK9 (0) |
| 1032 | empty PK9 (0) | empty PK9 (0) |
| 1376 | Mewtwo (150) | Mewtwo (150) |

All five 344-byte entries pass PK9 checksum validation. The two distinct selected-Pokémon
records also match the PK9s at body offsets 0 and 344. This establishes host/guest ordering in
the observed two-station session. Empty entries in a working battle show that dedicated NPC
Pokemon need not be inserted at these two offsets. Later NPC initialization is still undecoded.

## Reproduced bug

The prior implementation treated application offset 21 as the guest's Pokemon and replaced
344 bytes there, inside the LZ4 block. Offset 21 is the first host literal in the old compressed
sample; the second identical PK9 is reconstructed using an LZ4 match. Replacing that literal with
the captured Iron Hands and then decompressing the result produces Iron Hands in **both** human
seats. The regression test reproduces this exactly. Earlier claims that offset 21 independently
described the receiving player were incorrect; an old on-screen Mew/HP observation could not
distinguish two seats sharing the same compressed data.

This proves a battle-start mutation error. It does not yet explain the lobby `0x80332e` seat
crossing or prove that fixing the start roster is sufficient to open the physical move menu.

## Implementation and controlled test

`pokeldn/sv/raid_start.py` validates the message and decompressed size, patches host PK9 at 0
and captured guest PK9 at 344, preserves bytes 688 onward, and recompresses the entire LZ4 body.
The host runtime reassembles the reference pair before mutation, splits the result into the
same two reliable sequence numbers, and reuses the identical closing fragment on retransmission.
It preserves the scheduled time, lowest-pending values and later replay. LZ4 is recorded in the
runtime requirements. The former route remains available as a comparison baseline.

Enable the opt-in wrapper flag `--correct-raid-start-roster` on the next controlled physical
run. It passes `--raid-host-pokemon` to the runtime. Keep the existing admission and lobby flags
identical to the prior full-replay experiment; this changes only construction of `0x80332f`.
Do not enable lobby-only or truncate before the closing start fragment.

The offline PR/Mew plus Iron Hands fixture generates a 1712-byte application message split into
1395 and 317 bytes. Decoding yields species `[151, 992, 0, 0, 150]`; the boss, empty entries and
remaining body are byte-identical to the original reference. All 42 project tests pass, including
five tests for the real LZ4 controls, duplicate-seat reproduction, corrected roster, template
reassembly/retransmission deduplication, and rejection of invalid PK9 sizes. No radio was opened.

Next physical check: enter with the party's own Pokemon, explicitly select the test Pokemon,
Ready, and observe battle initialization with the host connected. Record the four participants,
the selected guest Pokemon, HP/menu/timer and errors. Gameplay still requires a usable move menu
and advancing timer; the synthetic host has not achieved those yet.

Raw captures, decrypted bodies, saves and PK9 files remain private in `lab/`.

## Physical retest 8264

Violet joined and explicitly selected Iron Hands. The capture contains Ready and subsequent
game responses. Decrypting the actual outgoing sequences 52/53 gives 1395/317-byte fragments
(including the same 317-byte closing-fragment retry). LZ4 decoding the transmitted message
gives `[151, 992, 0, 0, 150]` at the five roster offsets: Mew, Iron Hands, two empty entries,
and Mewtwo. Thus the corrected independent human-seat fields were actually sent over radio.

The user observed two Mew instead of their selected Iron Hands, Arboliva and Dudunsparce,
with Logan and Evan names. On clarification, the user confirmed an HP bar and a general buff-like
animation, explicitly not a confirmed Mewtwo move. Three participants were visible and one was
invisible. No actionable move menu opened; the game then closed with a software error.
This is a visible HP/animation milestone, not playable battle. The highest contiguous
host-stream ACK was 64; the sender continued its scheduled replay through 219.

The remaining local-player/seat association failure can make the client apply slot 0 despite
its real selection being present in slot 1; this is a hypothesis supported by the lobby's crossed
selection and the two-Mew result, not a decoded game rule. The LZ4 mutation error is fixed by
the diagnostic option, but it is not sufficient for correct initialization. Next audit the
game-level player-to-seat association before changing any more battle data.

Private evidence: `lab/sv-raid-lz4-roster-8264.jsonl`, SHA-256
`C827486A1B497C670EF60C2A30A52F01BF51457D7FDAB592BBE251B889C39536`.
The exact direct Python host process was stopped after the game error; no host remains running.
