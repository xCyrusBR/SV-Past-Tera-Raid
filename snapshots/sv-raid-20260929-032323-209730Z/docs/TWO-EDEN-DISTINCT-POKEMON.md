# Two-Eden distinct-Pokémon reference

Status: prepared, **not captured**. This is a controlled reference test for the synthetic-host
roster bug, not a claim that the physical Violet raid is playable.

## Why this test

The functional 26 September two-Eden capture used the same first-party Pokémon in both saves.
On 29 September, read-only inspection of the two independent Scarlet saves confirmed that both
still have species 911 in party slot 1 and species 980 in slot 2. Therefore the old capture cannot
show whether a selected-Pokémon announcement belongs to the host's or guest's displayed seat.

## Minimal run

1. Keep the two existing Eden user/NAND directories independent. Do not copy or replace either
   save, ROM, update, keys, or event data. Use Scarlet 4.0.0 on both clients.
2. Host a local Eden room on UDP 24872. Place the capture proxy on UDP 24873 and connect the
   guest through that proxy, as in `CAPTURE-20260926.md`. Record into a **new** private `lab/`
   filename; never overwrite the 26 September reference.
3. Open the Mewtwo group lobby on the host. Leave the host's default first-party selection
   (species 911) untouched. On the guest, use **Change your Pokémon** to select party slot 2
   (species 980). Check on both screens that the host and guest names, icons, and different
   Pokémon occupy their own seats while the lobby timer advances. Do not infer success from the
   network capture alone.
4. End this first capture in the lobby, without Ready. Decode it with
   `tools/analyze_eden_capture.py` and compare the two `0x80332e` records, their originating
   station IDs, reliable sequence numbers, surrounding `0x80332c/0x80332d` messages, Session
   station list, and port-2 type-6/type-3/type-9 exchange against the old reference and physical
   Violet test 7284.
5. Only if the distinct-Pokémon lobby is correct on both Eden clients, make a second fresh
   capture through Ready/Start. Do not change the synthetic-host replay until the association
   rule is supported by both the visible result and the decoded packets.

## Interpretation gate

The useful result is host species 911 in seat 1 and guest species 980 in seat 2, with distinct
trainer identities and a moving countdown. If both seats change together, or a trainer/pokémon
appears under the wrong seat, preserve the raw capture and describe the screen; do not label the
test a functional reference. A working battle additionally needs a running battle timer and
actionable move menu, neither of which follows from lobby entry alone.

Raw captures, saves, Pokémon files, game files, and keys stay private. The collaboration snapshot
may contain this procedure and summarized observations only.
