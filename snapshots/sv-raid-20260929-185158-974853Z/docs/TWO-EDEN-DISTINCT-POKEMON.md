# Two-Eden distinct-Pokémon reference

Status: **lobby captured and visually verified on 29 September 2026**. This is a controlled
reference for the synthetic-host roster bug, not a claim that the physical Violet raid is playable.

## Observed result

- Two independent Scarlet 4.0.0 Eden instances joined the same local room (2/4). The guest
  connected through capture proxy UDP 24873 to the host room on UDP 24872.
- In the Mewtwo lobby, the host appeared in seat 1 with Skeledirge (species 911), the guest
  appeared in seat 2 with Clodsire (species 980), and the countdown advanced. The user verified
  both displayed seats. Neither player pressed Ready; no battle was tested in this capture.
- The decoded authenticated `0x80332e` stream contains guest species 911 at +49.844 s,
  host species 911 at +49.940 s, then the guest's change to species 980 at +65.320 s. The
  latter is reliable sequence 3 from guest station `192.168.1.2`. The host selection is
  reliable sequence 3 from `192.168.1.1`. Thus the visible guest-only change has a matching
  guest-origin selection announcement. The selection message's first 18 bytes have the same
  shape as the older reference except for its per-sender message counter; it contains no
  identified explicit seat number. The seat association must be established elsewhere or by
  sender identity. That is an inference, not a decoded game rule.
- Private raw capture: `lab/eden-two-client-distinct-20260929.jsonl` (1,254,775 bytes,
  SHA-256 `273E858172DD46BAB9D502E9496E8410BCAEA69416E61441F352B76699DB614A`).
  Decoded capture and summary remain beside it in `lab/`. Decoder reported 1,543 events,
  authenticated Pia keys, and zero decode errors. Do not publish these files.
- `tools/compare_eden_selections.py` reports two stations, identical initial selections, and
  distinct final selections. The follow-up offline comparison uses
  `tools/compare_radio_selections.py` on physical Violet run 7284: its guest/Iron Hands,
  host/Mew, guest/Iron Hands announcements carry the expected PIA source variable IDs from
  Session Join and the expected destination bitmaps (`[1]` for guest-to-host, `[2]` for
  host-to-guest), matching the working Eden route. This rules out a simple swapped PIA sender
  variable or destination bitmap in those selection packets; it does **not** identify the
  higher-level roster association fault. A comparison of the first host game records in the
  old and new working Eden captures finds only the per-sender message counter changed in
  `0x80332c`, `0x80332d`, and `0x80332e`; `0x803330` also changed its remaining-time byte.
  No other opening-body field changed. This rules out a stale run-specific field in those
  four replayed bodies as the direct explanation, but not an earlier state-mapping error.
  Full private suite: 27 tests passed.

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
   `tools/analyze_eden_capture.py`; then run `tools/compare_eden_selections.py` on the decoded
   private JSONL. Confirm it reports two stations and distinct first selections. Compare the
   two `0x80332e` records, their originating
   station IDs, reliable sequence numbers, surrounding `0x80332c/0x80332d` messages, Session
   station list, and port-2 type-6/type-3/type-9 exchange against the old reference and physical
   Violet test 7284.
5. Only if the distinct-Pokémon lobby is correct on both Eden clients, make a second fresh
   capture through Ready/Start. Do not change the synthetic-host replay until the association
   rule is supported by both the visible result and the decoded packets.

## Interpretation gate

The achieved result is host species 911 in seat 1 and guest species 980 in seat 2, with distinct
trainer identities and a moving lobby countdown. This is a **functional lobby reference only**.
A working battle additionally needs a running battle timer and actionable move menu, neither of
which follows from lobby entry alone. The next offline comparison should trace the sender/station
association around the guest's second selection and compare it with the physical Violet capture
where selecting Iron Hands updated PR's seat. Do not change replay fields based only on a
matching Pokémon digest or ACK.

Raw captures, saves, Pokémon files, game files, and keys stay private. The collaboration snapshot
may contain this procedure and summarized observations only.
