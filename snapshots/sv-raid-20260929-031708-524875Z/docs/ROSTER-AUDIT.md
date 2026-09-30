# Offline roster audit — 2026-09-28

Scope: one synthetic host (PR with support Mew) and one physical Violet guest. Evan is the
Scarlet save/reference identity, not an additional synthetic station. This audit used the private
two-Eden decoded capture and extracted host/guest record sets; it did not open the radio or prove
that the physical Switch's raid battle is playable.

## What the working two-Eden session actually contains

- The host's Session type-5 updates, sequence 0 and 1, each list exactly two stations. Their
  station indices and join orders are `(0, 0)` for the host and `(1, 1)` for the guest; each has
  one PlayerInfo. The PlayerInfo name is a single space and its 16-byte ID is the same neutral
  value on both stations. These fields alone do not carry the displayed trainer names.
- On game stream `0x81:0`, kind-1 record `001` carries the trainer identity. The reference host
  record names its host; the guest record names its guest. The synthetic host patches its own
  kind-1 name and four-byte trainer ID to PR. None of the other extracted host/guest records
  contains those trainer names or IDs in plaintext. No record-set entry names Evan.
- The host and guest each publish a `0x80332e` selected-Pokémon message on `0x80:0`. The
  successful reference happened to use identical selected PK9 bytes on both Edens; it does not
  demonstrate correct handling of *different* Pokémon. The synthetic host replaces its opening
  selection with PR's Mew and captures the Violet guest's own `0x80332e` selection.
- The host's `0x80332f` battle-start message spans reliable sequences 52 and 53 (1,400 bytes
  after reassembly). A valid local selected PK9 begins at offset 21 and a valid Mewtwo PK9 at
  offset 724. The synthetic host patches only the local PK9 at 21 with the physical guest's
  selection. It must not replace that field with PR's Mew: an earlier A/B caused the Violet
  player to enter as Mew. A regression test now checks these offsets against the private capture.

## Interpretation and remaining uncertainty

The synthetic Session builder also declares two stations at indices 0 and 1, so there is no
evidence that an extra Evan station is being explicitly created there. PR's trainer ID is separate
from the Mew's OT/ID by design. The observed PR-in-slot-3-with-guest-Pokémon and invisible allies
remain a *game-state association failure*, not evidence that two extra players should be sent.
The all-identical selections in the working reference are a limitation of that comparison. The
precise cause could still be a port-2 seat mapping, a missing/delayed game record, or a difference
in the physical guest's admission flow; the current evidence does not choose among them.
The synthetic wrapper loads no dedicated NPC roster, appearance, or Pokémon files. It replays
opaque battle-start records from the working two-Eden capture; those records may contain an NPC
selection or RNG state that we have not decoded. The user's observed "empty places filled" message
appears only after Start, not when trainers join the lobby. One NPC Pokémon has appeared in a
malformed synthetic battle, while other allies were invisible or duplicated. This supports
investigating the start-transition roster, but does not prove whether the host sends NPC IDs or
the client chooses them locally. Do not synthesize extra network PlayerInfo stations for NPCs.
One concrete port-2 difference is worth isolating: the functional Eden raid has a host type-6
pair mapping, a guest type-3 join asking for slot `0`, and a host type-9 accept for slot `0`, but
no type-7 announcement. The earlier standalone radio host stalled without type-7 because its
compressed type-6 still carried stale Eden IDs. After correcting those IDs, `7284` joined
without type-7. The default still sends an optional type-7 for comparison, but it is not
required for admission in the corrected path and its slot byte did not fix the Pokémon mapping.

## Why the earlier HP-bar attempt is not a protocol baseline

The private captures from runs `7318` and `6418` were decrypted and compared offline. In both,
the Violet guest selected its own Iron Hands in `0x80332e` and sent game-stream sequences 1–6
around battle start. In `7318`, however, outgoing battle-start sequences 52 and 53 were each
marked `START|END` instead of `START` then `END`, and the host put PR's Mew in the field that
becomes the guest's local Pokémon. In `6418`, fragment boundaries were corrected and that field
contained the guest's Iron Hands. `7318` displayed an initial Mew HP bar, but neither run reached
the move menu. Thus the earlier visual milestone does not justify restoring its malformed
fragmentation or the wrong Pokémon patch. A regression test now locks the reference 52/53 flags.

## Physical A/B result and next gate

The controlled lobby-only tests compared type-7 announcement slot `0` (`4186`) with slot `1`
(`9024`). Both reached the Violet lobby, but names/icons stayed empty even after the late Session
update. Selecting Iron Hands filled the first seat. On disconnect in `9024`, Violet rendered its
trainer in seat 2 and PR in seat 3, with PR holding a duplicate Iron Hands. The host's transmitted
kind-1 record decoded as PR with the configured ID; its `0x80332e` decoded as Mew; the guest's
record-set bulk ACK reached 47. That proves delivery, not correct application by the game. The
slot byte alone was not the fix.

An early-opening probe (`5649`) failed differently: the additional type-7 was sent first as
port-2 sequence 1, then the type-9 accept became sequence 2. Violet stayed on `Communicating`.
The functional Eden reference and both lobby-entering synthetic tests have type-9 at sequence 1.
That probe's timing option was removed; do not use it as a new baseline.

Next compare the game-level identity/roster state applied between record-set receipt and lobby
rendering. Keep PR/Mew as the sole synthetic host; do not add fake network players or NPC files.
Only after PR/Mew and the physical guest appear in the correct seats should another Ready/battle
test require a moving timer and usable move menu.

One identity-field difference was found after the A/B: the two-Eden offline host's kind-1 account
field (bytes 45–66) is all zero, but the synthetic wrapper previously overwrote it with an
invented `u-...` account. The raid wrapper now preserves those captured offline bytes while still
patching PR's trainer name and four-byte ID. A local regression test validates this transformation.
This is an evidence-based reduction of a wire difference, **not** a lobby fix. In the physical
Violet lobby-only retest `6742`, the lobby timer advanced and the late Session update was sent,
but the trainer names/icons remained empty. No Ready or battle transition was attempted.

## Session-generation comparison after `6742`

The working Eden join response and two station-list updates use sequence generations `0/0/1`.
The physical synthetic baseline uses `1/1/2`. Both declare two stations, host at index/order 0
and guest at index/order 1, with the same neutral one-space PlayerInfo name and ID. The first
four host game records follow the guest's first two game records by about 0.05–0.08 s in both
captures; their later wall-clock start on radio follows the guest's later opening. Eden Session
replies carry message flags 0; the radio baseline carries establishing flags 1 and a type-1
join ACK, so the two Session flows are not byte-equivalent. `--session-seq-base 0` isolates just
the generation numbers for a future lobby-only A/B; no physical result exists for it yet.

The physical `2851` A/B then used `0/0/1` and still showed an empty roster while the countdown
advanced. Its 44 host records were acknowledged through 47 and the late update was sent at
+49.07 s. Therefore generation numbers alone are not the missing UI association.

On host disconnect in `2851`, the Violet UI briefly rendered the physical guest in seat 2 and
PR in seat 3, both with Mew. The guest's authenticated `0x80332e` sequence 2 actually contained
Iron Hands (species 992); the host's sequence 4 contained Mew (species 151). There was no later
guest selection. In `9024`, the user selected Iron Hands again; guest sequence 3 followed the
host's Mew selection, and after disconnect both displayed seats held Iron Hands. The common
last-selected-Pokémon pattern is evidence of a shared/misassigned presentation state, not of
two correctly initialized trainer/Pokémon pairs. The precise roster key or event ordering that
causes this remains undecoded. The user confirmed they did not use Change your Pokémon in `2851`.

The no-Session-join-ACK `4638` A/B still reached a blank, ticking lobby after sending and
acknowledging the host record set, so that ACK alone is not the association fault.

More importantly, the radio host's early `0x7c:2` type-6 mapping at +0.14 s was already
present, but it was ZLIB-compressed. The ID-patching branch checked the compressed bytes for
leading `0x06`, never matched, and transmitted the captured Eden IDs unchanged. Decrypting
`6742` confirmed they did not match that run's current host ID. The working Eden type-6 contains
two identical copies of the *host* station ID, while the host and guest Session IDs are distinct.
The sender now decompresses, writes the current host ID to both tagged fields, and recompresses
the existing **single** type-6. A test confirms the reference's two IDs are equal and the
patched result repeats the chosen host ID. Diagnostic `6184` accidentally injected a duplicate
type-6 and failed before lobby; `7023` used just one but incorrectly wrote the guest ID into its
second field and also failed before lobby, with no type-3 join received. Neither tested the
reference-shaped correction; `8167` below did.

The corrected single type-6 was physically tested as `8167`. Its two decoded IDs matched the
current host, and Violet displayed PR in seat 1 and the physical guest in seat 2 with a moving countdown —
the first correct trainer-name/seat-order lobby in this synthetic-host track. The icons still
looked the same. The host's Mew appeared in the guest's seat, while the guest's fresh Iron Hands
selection appeared in PR's seat; the guest's opening Iron Hands had already been received before
the host Mew announcement. Thus the transport/seat mapping improved, but the Pokémon mapping is
still crossed. No Ready or battle was attempted. In the later `7284` A/B, the corrected type-6
allowed Violet to enter without type-7 through guest type-3 and host type-9. Names/seats remained
correct, but selecting Iron Hands still changed PR's seat while the guest retained Mew. The
`4792` A/B changed only the host's Session reply flags to 0, matching Eden, and reproduced the
same crossed selection. Neither type-7 nor Session flags alone caused the mapping fault.

The functional two-Eden reference used identical selected PK9s on host and guest, so it cannot
discriminate which selection message belongs to which seat. A new functional two-Eden capture
with **different** Pokémon, or decoding the 4.0.0 game's selection/roster handler, is the next
useful evidence. Avoid blind slot or flag sweeps and defer battle tests until the lobby maps
PR/Mew and guest/Iron Hands separately.
