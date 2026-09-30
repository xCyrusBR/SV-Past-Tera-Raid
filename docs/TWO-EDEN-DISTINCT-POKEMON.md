# Two-Eden distinct-Pokémon reference

Status: **battle-capable Eden↔Eden reference captured and visually verified on 30 September 2026**.
This is a controlled reference for the synthetic-host roster bug, not a claim that the physical
Violet raid is playable.

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

## Battle capture with the attached guest save (30 September)

- The guest save was replaced byte-for-byte with the user-provided Scarlet `main` file; the prior
  guest save remains in `lab/backups/`. The host and guest visibly appeared as `Player` and
  `Hasashi`, respectively, with Skeledirge (species 911) and Iron Hands (species 992) in their
  own seats. The guest Eden UI was German; the raid still proceeded, so the language difference
  did not prevent this observed local session.
- Both clients showed the battle move menu and advancing raid timer. The user confirmed at least
  one action cycle completed. This is the first successful battle/menu reference in a run with
  different initial selected-Pokémon records; it does not establish that duplicate save IDs caused
  the synthetic-host roster bug.
- Private capture: `lab/eden-live-proxy-20260930-005118.jsonl` (9,206,210 bytes,
  SHA-256 `6648E0146B9B22899E2E0F8149D7EE5B64BA8C0345A9A8DF3D2BB131C51DAB02`). The proxy
  listened on UDP 24872 and relayed to the Eden host on UDP 24873. Decoder produced 13,798 events
  with zero errors. Keep raw and decoded captures private.
- `tools/compare_eden_selections.py` reports two stations and distinct first/latest selection
  digests for this capture. By contrast, the 26 September same-save battle reference reports
  identical first and latest digests. The separate 29 September Clodsire lobby capture had
  identical first selections until the guest changed its Pokémon. This isolates the old identical
  initial selection as a confound in those references, but does not prove it was causal.
- Comparing the current full-battle capture with the 26 September full-battle reference shows
  that host opening bodies `0x80332c`, `0x80332d`, and `0x80332e` are identical except for their
  per-sender counter at byte 4. The first countdown `0x803330` differs at that counter and its
  remaining-time byte. Thus the opening payload is stable across same-save and distinct-save
  runs; the newly distinct trainer identities/selected Pokémon do not by themselves explain the
  synthetic-host crossed-seat behavior.
- The guest's decrypted `0x81:1` identity/state stream has 46 records in this capture versus 44
  in the older full-battle reference; sequences 5 and 6 are the two additional records. This is
  an observed difference only. The physical Violet stream also had 46, but current evidence does
  not establish that these records are required for a Scarlet host or related to the roster bug.

## Battle-start follow-up

The selection and opening-body comparison is complete: the new battle-capable reference confirms
distinct selected-Pokémon messages from the expected stations and a stable host opening payload,
while the old full-battle Eden capture used identical selected Pokémon. Further decoding found
the same 2720-byte LZ4 roster in both captures, with host/guest PK9s at decoded offsets 0/344.
The old compressed-offset overwrite duplicates the guest selection into both seats; the opt-in
correction is locally tested in `RAID-START-LZ4.md`. Physical validation is pending.
The physical success gate remains PR/Mew in slot 1, the Violet
trainer and its selected Pokémon in slot 2, correct NPCs, a running timer, and an actionable move
menu.

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

The achieved result is host species 911 in seat 1 and guest species 992 in seat 2, with distinct
trainer identities, a moving lobby countdown, a running battle timer, and an actionable move menu
on both clients. This is a **functional Eden↔Eden reference**, not proof that the synthetic host
works. Do not change replay fields based only on a matching Pokémon digest or ACK.

Raw captures, saves, Pokémon files, game files, and keys stay private. The collaboration snapshot
may contain this procedure and summarized observations only.
