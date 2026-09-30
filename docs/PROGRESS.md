# Protocol progress and next gate

Updated 2026-09-30. Synthetic host and Eden bridge are independent tracks.

## Synthetic host

1. Confirmed: physical Violet associates with the ESP32-S3-hosted LDN network, completes Net and Pia Session, and reaches the local Mewtwo lobby.
2. Confirmed: guest `0x80332d` Ready is identifiable by its trailing state `1`. The host now gates battle-transition records until this event; the 8642 run previously began transition before Ready.
3. Confirmed: with gating, run 6418 received guest game sequences 1–6. The first four post-transition messages matched the working two-Eden session, but sequence 7 never arrived. On-screen: three Iron Hands, one Dudunsparce, two invisible allies; no HP bar or move menu.
4. Run 7354 configured trainer PR with full ID `4294423561`, independent of the Mew PK9. The physical Violet user saw their own Iron Hands in slot 1; on leaving, PR appeared in slot 3 with that Iron Hands. The radio log identified the physical trainer separately from Evan, who belongs to the Scarlet save/reference, not to the physical guest or a second synthetic participant. Host identity is not simply absent; player/slot state is late or misassigned. A matching Pokémon OT is not required for a valid host.
5. The working Eden raid sends port-2 type 9 accept but no type 7 announcement. In the standalone radio host, A/B 2846 omitted type 7 but retained type 9 and the full replay. Violet stayed on “Communicating”; type 7 is restored by default despite being absent in the Eden trace. The difference is still unexplained.
6. The `--port2-announce-slot 0` diagnostic was prepared to test whether the extra type-7 message assigns the host to the wrong position. The ordinary mode remains slot 1; the subsequent A/B below did not validate a slot-byte fix.
7. Live lobby-only A/B: code `4186` announced type-7 slot `0`; code `9024` announced slot `1`. Both physical Violet joins reached a lobby with all names/icons empty, even after the second Session update at +49.1 s. Choosing the guest's Iron Hands filled the first slot. On ending `9024`, the guest moved to slot 2 and PR appeared in slot 3 with a duplicate Iron Hands. Both captures show the PR kind-1 identity and Mew selection sent correctly, and guest bulk ACKs for the host record set reached 47. Thus changing only the type-7 slot does not fix the UI association.
8. A separate lobby-only timing probe `5649` advanced the extra type-7 ahead of the guest's type-3 join. Type-7 then consumed port-2 sequence 1, pushing type-9 accept to sequence 2; Violet remained on `Communicating`. The working Eden reference and the two lobby-entering synthetic tests send type-9 as sequence 1. The timing-probe code was removed after the test; do not reuse that ordering.
9. Offline kind-1 comparison found the working two-Eden host's 22-byte account field at offsets 45–66 is zero, whereas the wrapper fabricated a `u-...` account. The raid wrapper now preserves the reference's offline account field and still patches PR's name/ID. The local test passes. Physical Violet lobby-only retest `6742` joined and received the late Session update, but names/icons remained empty while the lobby timer advanced. Thus this identity-field correction alone did **not** fix the visible roster.
10. Offline opening comparison of the functional Eden pair and physical `6742`: each host published the first four `0x80:0` game records in the same order, roughly 0.05–0.08 s after its guest's first two game records. The later absolute start in `6742` follows the guest's later opening; it is not by itself evidence of a host timing bug. The 44-record host stream uses the same sequence set, order, destination bitmap, and flags; kind-1 compressed length differs after the intentional PR identity patch. A concrete Session difference remains: Eden join response/first update/late update use generations `0/0/1`, while `6742` uses `1/1/2`. Eden Session replies use message flags `0`; the radio host uses establishing flags `1` and adds a type-1 join ACK. Only the generation difference is prepared as a single-variable diagnostic (`--session-seq-base 0`); it has **not** been tried on Violet and is not a proven fix.
11. Physical Violet lobby-only A/B `2851` used `--session-seq-base 0`, changing only the join response and two updates to `0/0/1`. The Switch joined, the host sent all 44 identity/state records, the guest acknowledged through 47, and the second update went out at +49.07 s. The user saw the same empty names/icons with a moving countdown. Thus this generation shift alone did **not** repair the roster. The host was stopped before Ready. The next comparison should focus on another isolated Session difference, especially the type-1 join ACK or message flags, before more battle attempts.
12. After `2851` disconnected, the Violet UI briefly showed the guest in slot 2 and PR in slot 3, **both with Mew**. The authenticated game messages show the guest announced species 992 (Iron Hands) at `0x80:0` sequence 2 and the host announced species 151 (Mew) at sequence 4; no second guest selection was captured. The user confirmed they did not touch Change your Pokémon in `2851`. In `9024`, the guest made another species-992 selection at sequence 3 after the host's Mew announcement, and the post-disconnect UI showed both seats with Iron Hands. This is a strong correlation between the last selection announcement and both rendered Pokémon, consistent with a missing/incorrect trainer-to-selection association. It is not proof of the exact game mapping rule and does not imply the guest actually changed its party Pokémon to Mew.
13. A separate lobby-only `4638` omitted only the type-1 Session join ACK. Violet still joined, all 44 host records were sent and acknowledged through 47, and the late Session update went out at +49.11 s; names/icons remained blank with a moving timer. This ACK alone is not the fix.
14. A further audit found a **real station-ID patch bug** in the early compressed port-2 type-6 mapping. The wrapper already sent one type-6 at +0.14 s, but `sv_host.py` checked for uncompressed byte `0x06` and replayed the Eden IDs unchanged. The `6742` capture confirms they did not match its current host ID. The working Eden type-6 contains the **host ID twice**, not host then guest. Diagnostic `6184` accidentally duplicated type-6 and failed before lobby; after removing the extra copy, `7023` incorrectly replaced its second ID with the guest ID and also failed before lobby (the guest never sent type-3 join). Both failures are invalid tests of the reference shape. The current code now decompresses, writes the *current host ID to both fields*, and recompresses the existing single type-6. A regression test checks both equal tagged IDs. Its physical retest is item 15.
15. Physical lobby-only `8167` validated that corrected single type-6: both decoded tagged IDs matched the current host; Violet entered and displayed PR in slot 1 and the physical guest in slot 2 with a moving countdown. This is a genuine visible roster advance over the empty-lobby baseline, **not** a playable raid. Both trainer icons looked like the guest's; initially both Pokémon displayed Mew. The guest's authenticated opening selection was Iron Hands (species 992), the host's was Mew (151). After the user explicitly selected Iron Hands again, a second guest `0x80332e` arrived and the UI displayed PR with Iron Hands while the guest remained with Mew. Thus Pokémon assignment is crossed despite the corrected trainer names/slots. The two unused seats remained Searching. No Ready/battle test was attempted.
16. Physical lobby-only `7284` kept the corrected type-6 and omitted only the synthetic type-7. Violet still joined; the port-2 path was exactly host type-6, guest type-3, host type-9, with no type-7. PR/guest names and seats appeared correctly, but both initially displayed Mew and the icons still matched. After the guest selected Iron Hands, **PR's slot 1 changed to Iron Hands and the guest's slot 2 stayed Mew**. Thus type-7 is unnecessary for admission on the corrected type-6 path and is not the cause of the crossed Pokémon mapping. The timer advanced; no Ready/battle test was attempted.
17. Physical lobby-only `4792` changed only the host's Session-reply message flag from `1` to `0`, matching the two-Eden reference, while preserving the `7284` no-type-7 path. Violet joined, the late Session update was sent at +49.08 s, and the same wrong selection mapping persisted: a new guest Iron Hands selection changed PR's slot 1, not the guest's slot 2. This flag difference alone is not the fix. The host was stopped before Ready.

## Next controlled comparison

No second synthetic trainer is needed. Keep distinct: PR's trainer ID/name, the Mew's OT/ID, the physical guest's trainer identity, and that guest's selected Pokémon. The current wrapper contains no literal Evan participant; Evan is from the Scarlet save/reference and must not be copied into the synthetic roster. Corrected type-6 restores visible trainer names/seat order but not the Pokémon/icon association; removing type-7 and setting Session flags to 0 do not fix it. Stop blind live slot/flag sweeps. The **functional two-Eden lobby with different final selections has now been captured** (item 20). The next step is an offline sender/station-association comparison against the physical Violet capture where the guest selection changed PR's seat. Do not change the synthetic replay or test its battle until PR/Mew and guest/Iron Hands occupy their own seats.

18. On 29 September, read-only inspection confirmed that the existing host and guest Scarlet saves
    are independent but have identical first two party species (911, 980). A controlled
    distinct-selection run is specified in `TWO-EDEN-DISTINCT-POKEMON.md`: leave host slot 1 and
    select guest slot 2 in the lobby, capture to a new private file, and verify both screens before
    drawing a packet-level conclusion. No new Eden run has been captured yet; desktop-control
    initialization failed before the application could be opened.
19. `tools/compare_eden_selections.py` checks `0x80332e` announcements by source station
    from both proxy directions, deduplicates relays/retransmissions, and compares encrypted-PK9 digests
    without exporting Pokémon bytes. It finds exactly two first selections in the functional
    26 September reference, both with the same digest, confirming that capture alone cannot
    distinguish the host/guest selection association. At that point the distinct-Pokémon capture
    had not yet been taken. Local suite then: 23 tests passed. No new GitHub snapshot was generated.
20. The controlled two-Eden lobby succeeded on 29 September: host/Skeledirge in seat 1,
    guest/Clodsire in seat 2, lobby timer advancing, no Ready. Capture through UDP 24873
    yielded authenticated guest and host `0x80332e` messages: both first selected species 911,
    then only the guest sent species 980. The guest-only visible seat change corresponds to its
    own message, providing the missing distinct-Pokémon reference. See
    `TWO-EDEN-DISTINCT-POKEMON.md` for capture integrity and limits. This does not establish a
    playable raid or repair the synthetic host. Full private suite: 25 tests passed. No new
    GitHub snapshot was generated.
21. Offline comparison with physical run `7284` decoded three selected-Pokémon messages:
    guest/Iron Hands, host/Mew, guest/Iron Hands. Each PIA source variable ID matched the
    corresponding Session Join identity, and destination bitmaps matched the working Eden
    direction (`[1]` guest, `[2]` host). Thus the crossed Pokémon display is not explained
    by a simple source-variable or destination-bitmap swap in `0x80332e`. The remaining
    target is the earlier game-level trainer/selection association or its timing; no protocol
    field was changed on that inference alone. `tools/compare_radio_selections.py` and a
    private-capture regression test record this check. Full private suite: 26 tests passed.
22. The first host `0x80:0` game records in the old and new functional Eden captures were
    compared byte-for-byte. `0x80332c`, `0x80332d`, and `0x80332e` differ only at the
    per-sender message counter (offset 4); `0x803330` also differs in the countdown byte
    (offset 34). Thus those replayed opening bodies do not contain a newly changing
    run-specific participant/seat field. `tools/compare_eden_opening_records.py` and a
    private-capture regression test preserve this result. Full private suite: 27 tests passed.
23. Normalized Session type-5 lists were compared in the new two-Eden no-Ready lobby and
    physical synthetic `7284`. Both describe exactly two stations at index/order 0/0 and 1/1
    with one PlayerInfo each; the no-Ready Eden lobby sent only its first list, while `7284`
    sent a second automatically at about +49 s. The older Eden battle reference sent its
    second list near the Start transition. The synthetic `--lobby-only` mode now omits only
    this late list; full-battle replay still gates it on guest Ready. This is a controlled
    *untested* physical A/B, not an explanation of the crossed selection. 28 tests passed.
24. Physical no-late-update lobby A/B `6248` tested that isolation. Violet visibly showed
    PR/Mew in slot 1 and Cyrus/Mew in slot 2. After the guest selected Iron Hands, it appeared
    in **PR's slot 1**, not Cyrus's slot 2. The host sent exactly one Session type-5 list and
    received authenticated guest `0x80332e` selections (species 823, then 823, then 992);
    PR's outgoing selection was Mew (151). The guest's Iron Hands message arrived at about
    +47.1 s from first Pia traffic, before the former +49 s late-update schedule. Therefore
    that extra Session update is not required for the crossed display. No Ready/battle was
    attempted. Private capture `lab/sv-raid-no-late-update-6248.jsonl` has SHA-256
    `54ED2334FD9C8D78F65DCBEE60D05E3B0AA3DFD60F02C36C529BAFAAE4C9713A`.
25. Compared Eden and Violet's first guest lobby record: both are 42-byte `0x80332d` messages,
    differing only in the per-sender counter. Eden sends the host opening about 0.10 s after
    the guest selection; synthetic baselines were 1.22–1.73 s. A new opt-in gate sent the host
    opening 0.158 s after the initial selection in physical test `9351`, matching Eden timing.
    Violet still showed the same behavior when the guest changed to Iron Hands: PR's slot changed.
    The captured initial guest selection was sequence 2/species 823, PR's Mew was sequence
    4/species 151, and the later guest Iron Hands was sequence 3/species 992. Thus the timing
    difference alone is ruled out. No Ready/battle. Capture SHA-256:
    `9F07629782969874352745C262FBDF4DBADDF2CC4A1C47F255C3BFBD28F2FC92`.
26. In `9351`, the host's first opening record followed the initial guest selection by 0.158 s,
    close to Eden's 0.10 s. The host's first three opening records retained their established
    order; the first guest record body matched Eden except its per-sender counter. Selecting
    Iron Hands still moved PR's displayed slot, so the timing adjustment was insufficient.
    The mismatch is now narrowed to station/game roster association despite matching opening
    timing and matching guest-record body. No more timing-only tests are useful.
27. Began offline analysis of the local Scarlet 4.0.0 main image. The `0x80332e` tag appears at
    `0x3d3fdc8` beside a signed offset. Based at the entry start, it lands at `0x17e1ed0`, where
    code inserts 0x30-byte elements into a vector. Follow-up disassembly identifies it as generic
    vector growth/insertion (allocation, element move, and bounds update), not a raid selection
    handler. Neighboring entries also point into code, including interior blocks; the table's
    base convention, role, and caller remain unverified. ADR/ADRP+ADD/LDR, literal-load, and
    raw-pointer scans found no reference into the table page. Do not change packets from this
    lead; prioritize decoded capture comparison unless a caller can be tied to roster state.
28. Compared the reliable opening order in the distinct-Pokémon Eden reference with synthetic
    lobby captures `9351`, `6248`, and `7284`. Eden sends host `80332c/80332d/80332e` as sequences
    1/2/3, then first countdown `803330` as 4. All three synthetic captures send `803330` first,
    shifting the same host records to sequences 2/3/4. The guest selection itself remains sequence
    2 in both references; only the host's earlier countdown shifts its subsequent stream. Added
    opt-in `--match-eden-opening-order` to delay that first countdown from 3.20 to 3.36, without
    changing payloads or other settings. This is an untested lobby-only diagnostic, not a proven
    fix; the next Switch test should change only this option and verify distinct Pokémon stay in
    their own seats. No tests or live session were run in this step.
29. Physical lobby-only retests `6842` (Eden reliable opening order) and `7394` (same order plus
    guest-selection timing gate) both admitted Violet and transmitted host
    `80332c/80332d/80332e/803330` as sequences 1/2/3/4. The guest's authenticated Iron Hands
    change still displayed in PR's slot 1. In `7394`, PR's Mew followed the initial guest
    selection by 0.234 s. The order correction, even combined with near-reference timing, is
    insufficient. No Ready/battle. Capture hashes and the byte-level comparison are in
    `ROSTER-AUDIT.md`. A Windows launch also revealed a stale editable `ldn` import; the wrapper
    now prepends this checkout's Windows-compatible vendor path before loading the radio host.
    The focused option test passed, and both live hosts started and accepted Violet. Separate
    comparison found all 44 decompressed host record-set entries identical across the two Eden
    sessions, narrowing the remaining issue to admission/identity association rather than a
    changing host record-set payload.
30. Compared the complete port-2 admission bodies. Host type-6 (197 bytes) and type-9 (16 bytes)
    are byte-identical across the two Eden references. Relative to synthetic `7394`, type-6
    differs only in the two copies of the current host's six MAC bytes, and type-9 only in the
    current guest's six MAC bytes. This closes another plausible stale-ID explanation; no new
    wire field is identified for a safe patch.
31. Audited guest reliable-record ACKs against the working two-Eden reference. The physical `7394`
    capture lacked 18 of the reference's 44 guest `0x81:1` records (and also received sequence 6,
    which was unused in the reference), yet the old synthetic host ACKed through 46.
    Added opt-in contiguous ACK tracking in the protocol host and enabled it in the raid wrapper.
    Offline tests pass.
32. Physical lobby-only retest `5732` received every guest record sequence 1–46 with the new ACK
    tracking, but the user still saw Iron Hands change PR's slot. The host announced Mew separately;
    no Ready or battle was attempted. Missing guest records alone do not explain the crossed
    selection. See `ROSTER-AUDIT.md`; the private capture remains under `lab/`.
33. The same capture exposed a separate, untested header discrepancy: all 807 outgoing Pia
    packets carried packet ID zero, while the functional Eden host increments its IDs. Added an
    opt-in 16-bit per-packet allocator to the protocol host and enabled it in the raid wrapper.
    The 33-test suite passes.
34. Physical lobby-only retest `6187` exercised the packet-ID allocator: 1,032 outgoing host
    Pia packets had distinct IDs and guest records 1–46 arrived, but Iron Hands still changed
    PR's slot. No Ready or battle was attempted. Header-ID reuse is not a sufficient cause of
    the crossed selection. Continue admission/state comparison before another live A/B.
35. Physical lobby-only retest `2843` omitted the host's extra Session type-1 join ACK, which is
    absent from the working two-Eden trace. Violet entered, all 46 guest records arrived, and
    818 outgoing Pia packet IDs were distinct; Iron Hands still changed PR's slot. The extra
    ACK is not a sufficient cause. See `ROSTER-AUDIT.md` for private capture provenance.
36. Physical lobby-only `3619` additionally aligned the first Session generation and message
    flags to the functional Eden opening (generation 0, flags 0), while retaining no type-1
    ACK. Violet entered; all guest records arrived and 878 outgoing Pia IDs were distinct.
    Iron Hands still changed PR's slot. This combined Session alignment did not resolve the
    game-level Pokémon association. No Ready or battle was attempted.
37. Compared cross-station identity-record timing in both functional Eden captures with `3619`.
    Eden sent host kind-1 0.079 s after guest kind-1 in both runs; synthetic `3619` waited
    0.280 s. Added an opt-in gate to send the PR record set 0.08 s after the first guest
    `0x81:0` record. Offline tests pass.
38. Physical lobby-only `4952` used the gate: the captured host-minus-guest kind-1 gap fell to
    0.104 s, near the 0.079 s Eden reference. PR/Mew and Cyrus/Mew appeared in slots 1/2,
    but changing to Iron Hands still altered PR's slot. No Ready or battle was attempted.
    Further timing micro-tweaks are not supported by this result.
39. The two-Eden reference interleaves host and guest identity-record bursts. Synthetic `4952`
    sent all 44 host records in about 16 ms, before logging the guest's matching stream at
    +0.487 s. Added an opt-in paced-burst diagnostic; the 35-test suite passes.
40. Physical lobby-only `7270` tested that diagnostic. The 44 host records now span 46 ms,
    compared with 16 ms in `4952`, but the first guest `0x81:1` record was not processed until
    after the host burst. Violet still showed PR/Mew slot 1 and Cyrus/Mew slot 2; choosing Iron
    Hands changed PR's slot 1. The paced burst is not a fix, and the capture cannot distinguish
    on-air delay from receiver scheduling. No Ready or battle was attempted; details and private
    capture hash are in `ROSTER-AUDIT.md`.
41. Found a concrete host reliable-header difference: working Eden opening sequences 1/2/3 keep
    `lowest_pending=1`, whereas the synthetic sender had used 1/2/3. Added a narrow opt-in
    correction and a regression test; all 36 tests pass. Physical lobby-only `5638` confirmed
    the corrected sequence-3 header, but the visible slot association still crossed. Violet sent
    its actual party-leading Corviknight (823), then Iron Hands (992) after Change Pokémon; PR
    sent Mew (151). The capture proves the guest Pokémon data is not missing. No Ready or battle
    was attempted. See `ROSTER-AUDIT.md` for the private capture hash.
42. Hardware constraint clarified by the user: two Switch consoles are available, but only one
    Violet game copy. Do not assume a second simultaneous physical Scarlet/Violet player, ask
    the user to purchase another game, or conflate the existing functional two-Eden capture
    with a functional physical two-console session. Offline comparison of the two functional
    Eden captures found all 44 guest `0x81:1` record bodies byte-identical even though the newer
    run changed the guest's selected Pokémon and correctly updated slot 2. The physical Violet
    sent 46 records, including 5/6, but that title/save difference is not a proven cause.
43. Re-examined the earlier full-battle attempts before advancing more blocks. Run `7318`, which
    briefly showed Mew's HP, sent host `0x80:0` only through sequence 70 with malformed complete
    fragments and received guest game records only through sequence 6. The corrected, Ready-gated
    `6418` sent host records through 219, but the physical Violet's contiguous `0x80:0` ACK
    reached only 71 (with later selective ACK-mask bits) and the move menu did not appear. In the
    functional two-Eden battle the guest's ACK advanced to 220; it jumped from the low 70s to
    85 at the first long reference gap. Therefore merely sending later scheduled records has
    already been tried and did not establish gameplay. Investigate the reliable-window gap and
    fragment handling offline before another full-battle run; do not add arbitrary payloads or
    disconnect the host based on an HP-bar animation.
44. Found and corrected the apparent reliable gap offline. The Eden packet containing `0x80:0`
    sequences 69/70 has fourteen more same-size messages 71–84 behind Pia presence byte `0x00`,
    which inherits the previous message header. `pia6.parse_messages` delegated to a parser that
    stopped at `0x00`, so the decoded reference and synthetic replay omitted 84 real messages
    across six ranges. Pia6 now permits inherited zero-presence headers without changing Pia5's
    default behavior. Re-decoding the private two-Eden capture yields every sequence 44–219:
    176 distinct messages plus three retransmissions (179 total). The raid wrapper now uses this
    corrected capture, and all 36 project tests pass. The full replay has **not** yet been tested
    on physical Violet; do not claim gameplay or host-disconnect success from this offline fix.
45. Physical full replay `6412` tested the corrected zero-presence Pia decode with the host kept
    connected. Violet entered, gave Ready, and visibly advanced into the battle staging scene:
    three characters were visible and a fourth invisible. On follow-up, the user recalled
    their own participant, two displayed "Evan" names, and one Logan; the four Pokémon were
    two Iron Hands, one Dudunsparce, and one Arboliva, without a Mew identified. The exact
    name-to-Pokémon association was not visible/recalled. Evan/Dudunsparce and Logan/Arboliva
    are normal NPC possibilities, but the **second** Evan and absent PR/Mew remain unexplained.
    No HP bar or actionable move menu appeared.
    The guest's contiguous host-stream `0x80:0` ACK reached 66, meaning it had acknowledged
    host sequences through 65. The final inbound packet arrived just before the host sent
    sequence 66; host send-at then ran through 219 without further inbound radio traffic.
    This is **not** a playable
    raid. The capture is private at `lab/sv-raid-full-pia0-20260930.jsonl` (SHA-256
    `19D7E187B287B90F76DEFB21EE9DDAEA2D26E4D8402EA969205D573E1F45DEB2`).
    Evan is the Eden save's trainer name, but is also listed as a built-in Tera Raid NPC
    partner (Dudunsparce at high level); Logan/Arboliva is another listed NPC pair
    (https://www.serebii.net/scarletviolet/teraraidbattlepartners.shtml). Thus seeing Evan
    does not prove a leaked host identity. The existing roster audit found no explicit Evan
    record among the replayed identity fields. The duplicated Evan and absent PR/Mew still
    indicate erroneous visual/Pokémon association or an incomplete roster.
    Verify the source before changing identity bytes. The immediate transport question is why inbound
    traffic ceased around sequence 66; compare packet grouping, pacing, and receiver ACKs
    offline before another live full replay.
46. Controlled physical A/B `0174` used the same admission/lobby/start settings as `6412` but
    capped the battle-state replay at reliable sequence 65 (new diagnostic
    `--replay-last-seq 65`; default remains 219). All 37 local tests passed before the run.
    Violet again put the guest's chosen Iron Hands into PR's lobby slot 1. After Ready, Mewtwo's
    battle scene appeared with NPC-looking Dudunsparce and Arboliva but no HP or move menu; the
    user saw two Logan names and one Evan, one Logan without a character icon. The game then
    closed with a software error. The user clarified that `6412` also eventually closed with
    the same error. In `0174`, the guest's highest contiguous `0x80:0` ACK was 64 (received
    through sequence 63); the last inbound radio packet arrived after host 62/63 but before
    host 64/65. Capping at 65 therefore **did not** prevent the radio silence or crash and does
    not isolate sequence 66 as the trigger. Private capture:
    `lab/sv-raid-cap65-0174.jsonl` SHA-256
    `2B661C2210CDE31A38314F63FEB5F1ACAE1D5F450AB441A28AB9843DBBBEA265`.
    The common failure lies at or before the battle-state/roster transition, or in an earlier
    mismatch exposed there; do not keep running sequential blind truncation tests. The host
    wrapper's Windows Python launcher left its child process alive after Ctrl-C, so the exact
    verified `0174` processes were stopped before the capture hash was taken.

47. A second controlled Eden↔Eden capture used the user-provided Scarlet save byte-for-byte in
    the guest, with separate visible trainers and different default Pokémon: Player/Skeledirge
    in slot 1 and Hasashi/Iron Hands in slot 2. Both clients reached the battle move menu, both
    raid timers advanced, and the user confirmed one action cycle resolved. Guest UI language was
    German, but did not prevent this observed session. The private proxy capture
    `lab/eden-live-proxy-20260930-005118.jsonl` decoded to 13,798 events with zero errors.
    `compare_eden_selections.py` reports distinct first and latest PK9 digests; the old same-save
    26 September battle reference reports identical first selections. This confirms the duplicate
    initial selection was a confound in that reference, not that it caused the synthetic-host bug.
    Full captures remain private; no GitHub snapshot was generated.

48. Completed the first offline comparison of item 47. Host `0x80332c`, `0x80332d`, and
    `0x80332e` opening bodies match the 26 September full-battle reference except for the
    per-sender counter at byte 4; the first countdown also differs in its remaining-time byte.
    The new distinct-save capture has different first-selection PK9 digests by station, unlike
    the old same-save capture, confirming that identical selections were a confound but not that
    they caused the synthetic roster bug. The guest `0x81:1` stream has 46 records versus 44 in
    the older reference (additional sequences 5 and 6); Violet also emitted 46, but whether those
    records matter for the host is unknown. No synthetic packet fields changed. Next offline task:
    compare post-opening battle transitions and responses against synthetic `6418`, focusing on
    why the physical client never reaches a move menu.

49. Identified and reproduced a battle-start roster mutation bug using both working Eden
    captures. `0x80332f` has an 18-byte header and LZ4-encoded 2720-byte body: host PK9 at 0,
    guest at 344, empty entries at 688/1032, Mewtwo at 1376. The previous direct overwrite at
    application offset 21 edits the host literal inside compressed data; LZ4 matches then copy
    it into the guest seat too. A regression test reproduces two Iron Hands from that overwrite.
    Added opt-in `--correct-raid-start-roster` to decode, independently patch PR/Mew and the
    captured guest selection, and recompress. The reference's two sequence numbers, retry,
    timing and later replay remain intact. The fixture produces Mew/Iron Hands/empty/empty/Mewtwo
    with boss and remaining body unchanged. All 42 tests pass. Physical testing is pending;
    this is a proven battle-start construction bug, not yet a lobby mapping or gameplay fix.
    See `RAID-START-LZ4.md`; earlier offset-21 guest-Pokemon interpretations are superseded.

50. Physical test `8264` ran the opt-in decoded-roster correction. Actual outgoing fragments
    52/53 are 1395/317 bytes and decode to Mew/Iron Hands/empty/empty/Mewtwo; the closing retry
    is preserved. Violet selected Iron Hands, but the user saw two Mew, Arboliva and Dudunsparce,
    Logan/Evan names. The user clarified that an HP bar and general buff-like animation appeared,
    explicitly not a confirmed Mewtwo move; three participants were visible and one invisible.
    No move menu opened and the game closed with an error. Guest ACK reached
    64 while the scheduled replay ran through 219. This validates the roster rewrite on wire
    and a visible HP/animation milestone, but not gameplay or correct local-player mapping.
    The host was stopped and capture hash recorded in `RAID-START-LZ4.md`. Next work is offline
    player-to-seat association before any further physical trial.

### Next physical validation

51. The distinct-save Eden control exposes a Session PlayerInfo mismatch hidden by the old
    same-save control: the functioning host preserves the guest ID from the v11 join, while
    physical synthetic 8264 overwrote it with the old host-reference ID in both station lists.
    Added a strict parser for the join PlayerInfo trailer and opt-in
    `--preserve-guest-session-player`. Lobby-only test 5831 retained the exact incoming guest ID
    and distinct host/guest PlayerInfo on wire. The guest sent Corviknight then Iron Hands, but
    visually entered with Mew and the change still updated PR's slot 1. No Ready was attempted.
    Thus the real identity mismatch is corrected but is insufficient to fix the crossed lobby.
    See `SESSION-PLAYER-IDENTITY.md` for the capture hash and observation.

52. Compared Net setup against both working Eden raids. Net 0x11 length and four station slots
    match. Net 0x50 is 170 bytes in all three controls; both working Eden captures have value 7
    at body offset 27 while the synthetic static template has 4. The semantic meaning remains
    unknown. Added opt-in `--match-eden-net-property-body`, which changes only that byte, with
    an authenticated-packet regression test and both private reference checks. Next physical
    test is lobby-only with all 5831 settings unchanged except this flag. This is a controlled
    diagnostic difference, not an established fix; no battle or disconnect experiment yet.

53. Physical lobby test 6943 with Net-property byte 27 matched to 7 produced the same crossed
    selection: Cyrus still entered with Mew and Iron Hands updated PR's slot 1. No Ready or
    battle was attempted. Host stopped; private capture SHA256
    `A823B19AFD1456FFEA96310B10DFC73AB059D632B202A94D199DD104149C9CE6`.
    This isolated Net-property difference is insufficient. Keep it opt-in, not a default fix.

54. Both working Eden controls contain two type-9 admissions on 0x80:2: sequence 1 names the
    host with tuple fields 0/0, and sequence 2 names the guest with fields 0/1. Both lowest
    pending values are 1. Synthetic 6943 only sends the guest with fields 0/0 at sequence 1.
    Added opt-in `--match-eden-raid-admission` to reproduce the two bodies with current IDs,
    not an extra trainer. Two tests prove byte-exact matches to both private references.
    Previous descriptions of a single acceptance and uniform success code are incomplete.
    Physical lobby-only validation pending; see `RAID-PORT2-ADMISSION.md`.

55. Physical test 9064 validated correct synthetic lobby association for the first time:
    PR/Mew stayed in slot 1 with an independent icon; Cyrus automatically entered slot 2 with
    Corviknight and changing to Iron Hands updated only Cyrus. Authenticated selection messages
    confirm guest 823 then 992 and host 151. No Ready/battle was attempted. The working admission
    pair is now the validated lobby baseline; retain actual guest PlayerInfo and established
    opening settings. Next test combines this baseline with the independent decoded LZ4 start
    roster correction, checking actual battle menu/timer before any host-disconnect experiment.
    Capture hash and detailed evidence are in `RAID-PORT2-ADMISSION.md`.

56. Physical battle test 4276 combined the validated admissions and decoded LZ4 roster.
    Four participants were visible (PR, Cyrus, two NPCs), with Mew, Iron Hands, Arboliva and
    Dudunsparce. Brief general buff-like animation, no HP bar or move menu; eventual disconnect
    returned Violet to normal play. Guest contiguous host ACK advanced to 127, versus 64 in 8264,
    while the replay sent through 219. This is a real roster/visibility advance, not gameplay.
    Capture hash and reliability comparison are in `RAID-RELIABLE-RETRY.md`.

57. Added opt-in `--raid-reliable-retry`: retain exact emitted battle fragments, remove those
    acknowledged by guest ACK entry 0, retry the earliest gap at 350 ms up to eight times,
    preserve sequence/payload/fragment flags, keep lowest pending from skipping outstanding
    tracked data, and defer records outside a conservative 96-sequence outstanding window.
    Session rejoin resets tracking. All 52 tests pass and runtime compiles. Physical validation
    pending; this is bounded replay reliability, not yet a complete dynamic battle host.

58. Retry test 8352 again stalled after Pokemon release, without HP/menu, then returned to
    the world. Guest ACK reached 116; eight retries of sequence 116 brought no new confirmation.
    The bounded window deferred the end (last sent 211). Guest deauthentication reason 3 was
    logged, with no runtime traceback. Retry alone is insufficient. Prepared opt-in
    `--raid-replay-spacing 0.02` to process reception between scheduled battle fragments and
    collect ESP32 trace counters, preserving the validated lobby/roster. See
    `RAID-RELIABLE-RETRY.md` for the private capture hash. Physical paced validation pending.

59. Paced test 6407 still froze without HP/menu and returned to the world. Actual sends
    exposed a new scheduler regression: later fragments overtook deferred earlier ones (58
    before 57; 86 before 72–84). ACK stopped at 77, retries targeted 85 and last send was 175.
    Added ordered pacing guard and regression test, preserving captured old-sequence retries.
    This trial is not a clean rejection of pacing. ESP32 wire-drop counters stayed unchanged
    through join/Ready/last guest traffic and UART overflow stayed zero; no hardware fault
    established. Hash/counter details in `RAID-RELIABLE-RETRY.md`. Ordered paced validation next.

60. Ordered paced test 2185 had zero send-order overtakes, but still no HP/menu and returned
    Violet to the world. Guest ACK max 110, eight retries of 110, last scheduled sequence 205.
    Ordered pacing/retries remain insufficient; capture hash in `RAID-RELIABLE-RETRY.md`.
    At the user's request added opt-in `--start-on-ready`: begin the host transition about
    100 ms after received Ready, advance pending countdown predecessors without dropping IDs,
    move late Session commit together, preserve all internal phase intervals/order. The battle
    roster still follows the first transition by 7.445 s plus loading. Timing validation pending;
    this reduces the reference's artificial wait, not an established initialization fix.

Item 49 was tested as 8264 (item 50). Continue offline on game-level player/seat association:
the wire now contains distinct host/guest Pokemon, but the physical player still sees Mew.
Another live test should isolate a supported association change; physical gameplay still
requires the chosen guest Pokemon, a running timer, and an actionable move menu.

Offline comparison completed: the working two-Eden Session updates contain exactly two
stations, indexed 0/1, with one PlayerInfo each. The host and guest kind-1 stream records carry
their game-level trainer identities. The later distinct-save control proves that `0x80332f`
is LZ4-compressed with independent host/guest PK9s at decoded offsets 0/344 and Mewtwo at 1376.
The original compressed-offset-21 rewrite duplicated a Pokemon into both human seats. The
opt-in correction now replaces the decoded fields and recompresses. Lobby crossing remains
unresolved; see `RAID-START-LZ4.md` and `ROSTER-AUDIT.md`.
Decryption of runs 7318 and 6418 additionally showed that the earlier HP-bar attempt sent
battle-start fragments 52/53 as two complete messages and gave the physical guest PR's Mew,
despite its captured Iron Hands selection. The newer run repaired both faults and still received
guest sequences 1–6, but no move menu. Do not restore the older packet shape merely to recover
the HP animation.

## Gameplay success gate

The host is not working until Violet shows exactly two human-trainer seats in the correct slots (synthetic host PR/Mew in slot 1 and the physical Violet guest with their own chosen Pokémon in slot 2), correctly initialized NPC allies after Start, a running raid timer, and an actionable move menu. The physical guest's name can change with the save/profile. Evan is a Scarlet save/reference identity and should not be injected as another synthetic player. The user's observed fill-with-others message appears at Start; whether the host must send NPC selection/seed data remains unverified. Disconnect/NPC replacement should be tested only after that state is reached.

## Data handling

Private evidence remains in the local `lab/` folder and is excluded from GitHub snapshots. Public snapshots include code and summarized observations only. Do not publish keys, ROM/update, saves, PK9, raw packets, or captures with participant identifiers.

New private capture SHA-256: `sv-raid-slot0-4186.jsonl` = `ADABE182F4BC43FF333C2B87DAACC3F916F465C6F38C338345618108B34AD732`; `sv-raid-slot1-control-9024.jsonl` = `D6A4D1A2D63547157095CCB60C36D13A2644A09743F719E37EFE184CE6323350`; `sv-raid-reference-timing-5649.jsonl` = `9BC0387D60E6BAD65C77DA44EC453464D65BEAD9101C71428293081F123F1B3B`; `sv-raid-offline-account-6742.jsonl` = `6AF1BD64EA84704BB46298DB6F261970A0F4619F7A3E0F24EE5325EF2A3A5E27`; `sv-raid-session-gen0-2851.jsonl` = `A1169AB8F2DDAB2B72085DBDFA3F99143686EB0791CC6A630C03215ADEC8410A`; `sv-raid-no-session-ack-4638.jsonl` = `1E96722159F711B469106FE2ED654C129D7B88AB6D0A03FA3D47723C749089A8`; `sv-raid-pair-map-6184.jsonl` = `5456C53FC3B84F91A9FF5BD4725F2993A542848349AB20E29CDC315CB914E2D3`; `sv-raid-type6-fixed-7023.jsonl` = `EFD567A466306A05B1D642C88EE43FA28B76CAA2F3559825574DDA69070C2194`; `sv-raid-type6-hosttwice-8167.jsonl` = `FE081384DE6A1C13357E4545C1260617FC3D54048435A72693010D2BFA787CD6`; `sv-raid-type6-no-type7-7284.jsonl` = `E1F0EBC2D8BD2E7F45E2E1DE51DE5DBCC99F30B37BAB35FD7582AE63BC516828`; `sv-raid-session-flags0-4792.jsonl` = `BC3EF0A4D853B5F764C0BA312614E35A731F5B639410B52E9707462D86FD27F4`.
