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

## Next physical test, when the user is available

Keep PR/Mew as the sole synthetic host. Compare the current type-7 announcement slot `1` against
slot `0` in separate short runs, changing no other variable. Record the type-3 join slot, type-9
accept slot, Session station indices, and a Violet lobby screenshot *before Ready*. A valid lobby
must show PR/Mew in host slot 1 and the physical trainer with their own Pokémon in guest slot 2.
Only after that should we try Ready and require a moving raid timer and usable move menu. Neither
raid-injection tools nor a second artificial trainer can substitute for this check.
