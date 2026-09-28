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
no type-7 announcement. The standalone radio host needs an added type-7 to leave
`Communicating`; its current default announces slot `1`. This mismatch motivates an A/B with
type-7 slot `0`, but it is not proof that the slot byte has the same role in type 3 and type 7.

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
