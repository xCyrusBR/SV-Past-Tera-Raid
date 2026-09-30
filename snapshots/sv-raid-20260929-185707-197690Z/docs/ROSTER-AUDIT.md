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

The older functional two-Eden reference used identical selected PK9s on host and guest, so it
could not discriminate which selection message belonged to which seat. A new controlled two-Eden
capture (`lab/eden-two-client-distinct-20260929-decoded.jsonl`) resolves that limitation: the
host displayed Skeledirge in slot 1, the guest selected Clodsire in slot 2, and the countdown
advanced. No Ready or battle was attempted. The guest selection changed only slot 2. The
authenticated guest selection in physical synthetic test `7284` changed PR's slot 1 instead.
The received message source variables and destination bitmaps agree with their respective
Session Join station IDs, so merely swapping those outer fields is not an evidenced fix.

The new Eden lobby capture contains one host Session type-5 station-list update (sequence 0)
through the guest's later selection. The physical `7284` lobby-only run sent two (sequences 1
and 2), the second at about +49 s without Ready. The older full-battle two-Eden reference also
contains two, with the second near the start transition. Normalizing both station lists shows
two stations, index/order 0/0 and 1/1, one PlayerInfo per station, matching neutral PlayerInfo
IDs, port 12345, and no route or nonzero token. The station-list contents do not explain the
crossed selection.

The synthetic wrapper omits the late Session update only in `--lobby-only` mode. The full
raid path retains the second update behind its existing Ready gate. Physical test `6248` showed
PR/Mew in slot 1 and Cyrus/Mew in slot 2, then placed the guest's selected Iron Hands in PR's
slot 1. The captured guest selection (species 992) arrived around +47.1 s, before the former
+49 s late-update time, and only the first Session list was transmitted. Thus omission of the
second list does not correct the crossed mapping. Do not add fake players or NPC stations to
address it. The next candidate is the game-level association established before selection,
especially the guest-to-host opening records and their relationship to host trainer identity;
the specific field or order remains unproven. Defer another battle test until the lobby seats
stay correct under a distinct-Pokémon selection.

The first guest opening game record (`0x80332d`, reliable sequence 1) is 42 bytes in both the
distinct-Pokémon Eden lobby and physical `6248`; the only changed body offset is the per-sender
counter at offset 4. The Eden sent the first host lobby state about 0.10 s after the guest's
first `0x80332e` selection. The synthetic host sent it 1.2–1.7 s later in `8167`, `7284`, and
`6248`. Opt-in `--guest-selection-gated-opening` aligns that first host send to the first guest
selection. Physical test `9351` achieved a 0.158 s gap and sent only one Session list, but the
user still saw the same lobby behavior: the guest's Iron Hands appeared on PR's slot. The
timing match alone does not repair the selection association. Guest `0x80332e` arrived at +2.316
s; PR's Mew announcement followed at +2.568 s; the user's Iron Hands change arrived later at
+17.353 s, all with the expected sender variables and destination bitmaps. Next analyze the
port-2 association and opening-record order against the captured Eden exchange; do not repeat
the timing experiment or proceed to battle yet.

The local 4.0.0 main image is available as `lab/sv400-main.bin`. A first static scan found the
little-endian `0x80332e` tag at file offset `0x3d3fdc8`, followed by a signed 32-bit value. Using
the entry start as the relative base lands at `0x17e1ed0`, which begins a routine that inserts
0x30-byte elements into a vector. Neighboring entries in the same area also point at code
addresses, some inside existing function bodies, so this looks like a dispatch/state table; its
exact base convention and role are not verified. It does not expose station-to-seat mapping. A
scan of ADR, ADRP/ADD/LDR, literal loads, and raw 64-bit pointers found no direct reference into
this table page. Follow-up disassembly confirms `0x17e1ed0` is a generic 0x30-byte vector
insertion/growth routine (allocation, element move, and vector-bound updates), not a raid-specific
selection handler. This removes that target as a direct explanation of the crossed seats. The
table's dispatch role and caller remain unverified; continue only if a caller or registration path
can be tied to the roster, otherwise prioritize decoded capture comparison over more blind binary
scanning. Leave wire data unchanged until an association rule is evidenced.

## Reliable opening-order comparison

A decoded comparison of the functional distinct-Pokémon Eden lobby against three physical
synthetic-host captures found one reproducible difference not isolated by the timing A/B. Eden's
host stream order is `80332c` (sequence 1), `80332d` (2), `80332e` (3), then its first `803330`
countdown (4). Synthetic captures `9351`, `6248`, and `7284` instead send `803330` first (sequence
1), followed by `80332c` (2), `80332d` (3), and `80332e` (4). In `9351`, the guest's opening
selection is sequence 2 and PR's Mew is sequence 4; the distinct Eden reference has the guest's
opening selection at sequence 2 and host selection at sequence 3. Thus the payloads and per-sender
selection sequence align, while the host's preceding countdown shifts its subsequent reliable
sequence numbers by one. This is a concrete next hypothesis, not yet a demonstrated cause of the
crossed UI.

The wrapper has opt-in `--match-eden-opening-order`, which delays only that first host `803330`
from 3.20 to 3.36 so the existing `80332c/80332d/80332e` sends precede it. It does not alter
payloads, station IDs, later countdowns, or NPC data. The physical results are recorded below.

## Physical opening-order retests, 29 September

The lobby-only `6842` test enabled only `--match-eden-opening-order` relative to the established
no-type-7 path. Its authenticated host stream sent `80332c/80332d/80332e/803330` on reliable
sequences 1/2/3/4, exactly the Eden order. Violet entered; its initial selection was species 823,
PR announced Mew (151), and the physical guest's subsequent Iron Hands (992) announcement arrived
as guest sequence 3. The user reported that Iron Hands still appeared in PR's slot 1. The host
Mew announcement followed the initial guest selection by about 1.76 s, leaving the separate
opening-time difference. Private capture SHA-256: `A0CEDA70DB5F0ACD6CFEAE81EB7AFAEC079AAC96E0C3632CDAC0CDD41AD7FF0B`.

The `7394` follow-up enabled both the Eden order and the existing guest-selection opening gate.
The host Mew announcement followed Violet's initial selection by 0.234 s; the host order stayed
1/2/3/4. Violet's Iron Hands selection again changed PR's slot, per the user. This rules out the
host countdown-before-opening order as a sufficient cause, including when the opening is also
paced close to the Eden reference. No Ready or battle was attempted. Private capture SHA-256:
`03453E3C452D7BBE0948202596AA127FEC9C4C9A89A5604BE1AF291475E6CD55`.

The three host opening bodies now match the distinct-Pokémon Eden reference in shape and reliable
sequence. `80332c` and `80332d` each differ only at the sender's message counter (byte 4);
`80332e` differs there and in the intentionally different selected PK9 (Mew versus Skeledirge).
The first countdown also carries a different remaining-time byte because the two reference runs
began at different timer values. All 44 decompressed host `0x81:0` records from the old full-battle
Eden capture are byte-identical to the 44 records in the newer distinct-Pokémon Eden lobby capture;
there is no changing host station identifier in that record set across those sessions. The
synthetic host still patches the kind-1 trainer identity to PR. The remaining discrepancy may be
in how the receiving game associates its local station with that identity, or in another admission
message. No field in these three opening bodies currently supports a further targeted patch.

The port-2 admission bodies were checked directly as well. The 197-byte host type-6 body is
identical across the two Eden captures. Compared with `7394`, only the two copies of the current
host's six MAC bytes differ (12 bytes total), as expected for a new station. The 16-byte host
type-9 accept is also identical across the Eden captures; compared with `7394`, only the guest's
six MAC bytes differ. The type-6/type-9 body layout provides no additional unexplained field to
patch. The next useful evidence must come from the receiving game's roster association or from a
reference with a physical Violet guest and a real game host, rather than another arbitrary port-2
field change.

## Guest record acknowledgement gap, 29 September

An offline audit found a separate transport difference. The working two-Eden reference received
all 44 expected guest `0x81:1` records (sequence numbers 1–4 and 7–46; 5–6 are intentionally
unused in the Eden reference). In the physical `7394` capture, the synthetic host received 27
unique records, including sequence 6, but not sequences 3–4, 19–21, or 23–35. The old host
nevertheless sent cumulative ACK 47 after receiving sequence 46, because it tracked only the
highest observed number. Thus it could
acknowledge records it had not received. The other recent physical captures show the same class
of gap. This is a plausible transport contributor to incomplete or crossed lobby state, not yet
an established explanation for the visible roster bug.

The raid wrapper now enables `--ack-received-only`: it tracks received sequence numbers and
acknowledges only through the contiguous prefix, allowing the known 5–6 gap. For the captured
`7394` delivery set, this would have held the cumulative ACK at 3 while 3–4 remained missing,
instead of advancing to 47. Unit tests cover this case and the complete two-Eden reference.
Replaying the arrival sets of captures `6842`, `7394`, `6248`, and `7284` yields projected ACK 3
for all four, whereas each old run ended at ACK 47. The change passed the offline test suite.

### Physical retest `5732`

The Violet entered a lobby-only synthetic host with contiguous ACK tracking, the Eden opening
order, the guest-selection opening gate, and no port-2 type-7 announce. The radio capture received
all guest `0x81:1` sequence numbers 1–46; its final ACK was 47. The initial Violet selection
was species 823, PR announced Mew (151) 0.230 s later, and the guest later selected Iron Hands
(992). The user still saw the same crossed selection: Iron Hands appeared in PR's slot. No Ready
or battle was attempted. This rules out the previously missing guest record delivery as a
sufficient explanation for the visible slot error. It does not negate the safer ACK behavior,
nor establish the cause of the remaining game-level association fault. Private capture:
`lab/sv-raid-ack-contiguous-20260929.jsonl`, SHA-256
`6855561133CCC519F0F525C5A7D3622693B0515A351FFD88A9AB96DEA890679C`.

## Pia header packet IDs: isolated next diagnostic

The `5732` capture has 807 outgoing host Pia packets and only one header packet ID: zero.
The working Eden host increments its header IDs across Net, Session, reliable data and ACK
traffic. This is separate from the reliable-stream sequence numbers. In earlier synthetic
participant research, a constant packet ID stalled an ACK window; whether it affects this
physical guest's slot association is untested. The protocol host now has opt-in
`--monotonic-pia-packet-id`, and the raid wrapper enables it for the next lobby-only A/B.
The allocator and 16-bit wrap are unit-tested. This changes header IDs only, not trainer IDs,
station mapping, Pokémon data or replay order. Do not claim a roster fix until the Violet
shows Iron Hands in Cyrus's slot 2 after Change your Pokémon.

### Physical retest `6187`

The packet-ID diagnostic was exercised in a lobby-only physical Violet join. All 1,032 outgoing
host Pia packets in the private capture have distinct header IDs, starting 0, 1, 2, and so on.
The host received guest record sequences 1–46 and ended at ACK 47. Violet initially selected
species 823, PR announced Mew (151) 0.23 s later, and Cyrus changed to Iron Hands (992) at
+21.48 s. Visually, PR/Mew occupied slot 1 and Cyrus/Mew slot 2; the Iron Hands change still
appeared in PR's slot 1. No Ready or battle was attempted. Thus repeated Pia packet IDs are not
a sufficient explanation for the crossed selection. Private capture:
`lab/sv-raid-pia-pid-20260929.jsonl`, SHA-256
`47BC88E33B52B2057A2FBF25C41DB625ABCDB162DE7622EECA1AFA60A85FAE91`.

### Physical retest `2843`: no extra Session join ACK

The functional two-Eden Session opening has join request type 0, host response type 2,
station-list type 5, and guest acknowledgement type 6; it has no host type-1 join ACK. The
synthetic host's type-1 ACK was omitted in lobby-only run `2843`, with the corrected type-6,
contiguous record ACKs, monotonic Pia packet IDs, and the previous opening settings unchanged.
Violet still entered. The capture has no host type-1 Session ACK, 818 distinct outgoing Pia
packet IDs, all guest record sequences 1–46, and final record ACK 47. Violet selected species
823 initially, PR announced Mew (151), and Cyrus later selected Iron Hands (992). The user
again saw the Iron Hands change in PR's slot 1, while Cyrus's slot 2 retained Mew. Thus the
extra Session join ACK is not a sufficient explanation. No Ready or battle was attempted.
Private capture: `lab/sv-raid-no-session-ack-postfix-20260929.jsonl`, SHA-256
`D3090E844C6C89D81D2D7502BACC22B960C785E8487FB5BD46EA24C39AA3058D`.

### Physical retest `3619`: Eden-like Session opening

Run `3619` kept the established type-6, reliable ACK, packet-ID and game-opening behavior, but
combined the functional Eden Session choices: no type-1 join ACK, first station-list generation
0, and Session message flags 0. Violet entered. The private capture shows a type-2 response and
type-5 generation-0 update, 878 distinct outgoing Pia packet IDs, all guest record sequences
1–46 and final ACK 47. The guest selected species 823 initially, PR announced Mew (151), then
the guest selected Iron Hands (992). The visible Iron Hands again appeared in PR's slot 1,
leaving Cyrus's slot 2 with Mew. No Ready or battle was attempted. This combined Session
normalization did not fix the crossed Pokémon association. Private capture:
`lab/sv-raid-eden-session-20260929.jsonl`, SHA-256
`FE7C2692C8647FE15EF9C327CF176EFB4EB27D2982D98168F9B234C148AC29E6`.

## Kind-1 identity-record interleaving: next diagnostic

Both independent working Eden captures place the host's first `0x81:0` kind-1 identity record
0.079 s after the guest's first kind-1 record. Relative to the first Session station-list
update, the distinct-Pokémon capture has guest at +0.167 s and host at +0.246 s; the earlier
full-raid capture has guest at +0.200 s and host at +0.279 s. The synthetic `3619` host sent the
guest's kind-1 at +0.093 s and PR's at +0.373 s, a 0.280 s gap. This consistent cross-station
ordering may matter while the game establishes ownership of the following selection messages;
it is a hypothesis, not a decoded rule. An opt-in `--gate-records-after-guest` wrapper flag now
schedules PR's identity record set 0.08 s after guest reliable `0x81:0` sequence 1, without
changing its content, order, or later lobby packets. The 34-test suite passes. The visible
Violet slot result and actual captured timing still require a physical retest.

### Physical retest `4952`: gated kind-1 records

Violet entered the lobby-only host with the guest-kind-1 gate and the Eden-like Session opening.
The first guest kind-1 record arrived +0.065 s after the Session list; PR's first kind-1 record
left at +0.169 s, a 0.104 s cross-station gap. This is much closer to the 0.079 s gap in both
working Eden captures than the prior synthetic 0.280 s gap. The host's 807 outgoing Pia IDs were
distinct and the guest record ACK reached 47. Visually, PR/Mew remained slot 1, Cyrus/Mew slot 2,
and the guest's Iron Hands change still appeared in PR's slot 1. No Ready or battle was attempted.
The identity-record interleaving difference alone is not a sufficient cause; a further 0.025 s
timing tweak is not justified by this result. Private capture:
`lab/sv-raid-kind1-gated-20260929.jsonl`, SHA-256
`96F32B5242598893B33EEAEC53E3D2AE7C696A71D5C648B47EF6C6218A5E6473`.

## Identity-record burst overlap: next diagnostic

In the distinct-Pokémon Eden lobby, host `0x81:0` identity records ran from +0.246 to +0.324 s
relative to the Session list, while the guest's `0x81:1` records began at +0.246 s and were
interleaved with them. The earlier full-raid Eden capture has the same host/guest kind-1
ordering. In synthetic `4952`, PR sent its 44 host records from +0.169 to +0.185 s, and the
first guest `0x81:1` record was processed at +0.487 s. The synthetic host therefore sent a much
tighter burst before it observed the guest's corresponding records. It is unknown whether this
is an air-time difference, host receive-loop delay, or a meaningful game-state race. An opt-in
`--pace-identity-records` wrapper flag now adds short spacing without changing record bodies or
order; the 35-test suite passes. The next physical lobby-only capture should measure the actual
burst width and whether guest records begin to overlap before interpreting any visible change.

### Physical retest `7270`: paced host records

Violet entered the lobby and still displayed PR/Mew in slot 1 and Cyrus/Mew in slot 2. Selecting
Iron Hands put it in PR's slot 1. The paced host sent 44 records from +0.158 to +0.204 s after
the Session list, a 0.046 s burst (versus 0.016 s in synthetic `4952`, and about 0.078 s in the
distinct-Pokemon Eden capture). The guest's first `0x81:1` record was not processed until +0.463 s,
after that burst; all 46 distinct guest record sequences were eventually received. The guest's
kind-1 preceded PR's by 0.082 s, nearly the 0.079 s functional-Eden gap. Thus pacing this burst
did not produce overlap or fix the visible slot association. The capture timestamps alone do not
identify whether the late guest stream is on-air behavior or receiver scheduling. No Ready or
battle was attempted. Private capture: `lab/sv-raid-paced-kind1-20260929.jsonl`, SHA-256
`70F276556538744F7F3F2EAC6C8D33290ACA72682627E8181993F3085D4C00C6`.

## Host opening reliable-window discrepancy: pending physical retest

The functional distinct-Pokémon Eden host sends the first `0x80:0` game records with
`(sequence, lowest_pending)` pairs `(1,1)`, `(2,1)`, `(3,1)`, then its first countdown `(4,4)`.
In synthetic `7270`, the corresponding pairs were `(1,1)`, `(2,2)`, `(3,3)`, `(4,4)` because
the replay sender defaults `lowest_pending` to its current sequence. The payloads, reliable
flags, destination bitmap, and guest-selected PK9 species were otherwise of the expected shapes.
The guest's first selection used `(2,1)` in both the working Eden capture and `7270`. An opt-in
`--match-eden-opening-lowest-pending` flag now sets `low=1` only on the host's `80332d` and
`80332e` opening records; it does not force later countdowns or other streams. All 36 local
tests pass. This header mismatch is a concrete reference difference, but it is not yet known
whether it causes the crossed visible selection. A lobby-only physical A/B is required before
advancing to Ready or battle.

### Physical retest `5638`: corrected opening reliable window

The opt-in correction was transmitted: PR's opening selection used reliable sequence 3 with
`lowest_pending=1`, matching the functional two-Eden host. Violet entered and sent Corviknight
(species 823), the first Pokémon in its party, on guest selection sequence 2; after the user
changed Pokémon, it sent Iron Hands (992) on guest sequence 3. PR sent Mew (151) on host sequence
3. The visible lobby nevertheless showed PR/Mew slot 1 and Cyrus/Mew slot 2, then placed Iron
Hands in PR's slot 1. All 46 distinct guest identity-record sequences arrived. The host-record
burst spanned +0.179 to +0.223 s after the Session list; the first guest `0x81:1` was processed
at +0.492 s. Thus this reliable-window mismatch was real but not a sufficient cause of the
crossed selection. Do not promote the flag as a fix or proceed to Ready. Private capture:
`lab/sv-raid-opening-low1-20260929.jsonl`, SHA-256
`B67B9593A79B21982ECA0FD1F8E89BB11430D0C3B1931A73A940E104787E016F`.

Offline follow-up: scanning the 44 decompressed Eden host identity/state records found the
captured trainer's four-byte game ID and UTF-16 display name only in record 1, once each. The
remaining 43 records do not contain another literal copy of either field needing the same PR
rewrite. This does not prove the rest of the record set is semantically independent of trainer
identity, but it rules out an obvious missed literal replacement.

The earlier Violet-as-physical-host capture also has a 132-byte raid advertisement. Compared
with the synthetic `5638` advertisement, only nine byte positions differ: the code-dependent
password/header and game-code bytes at 6–8 and 93–95, plus three bytes at 125–127 of the
four-byte game marker. The physical host was a different raid, so that marker difference is
not evidence of a malformed Mewtwo advertisement. All other fields and the length match. This
is a limited check of the advertised shape, not a functional guest-session reference or evidence
that the whole LDN NetworkInfo is equivalent.

## Offline control: two functional Eden guest record sets

The earlier full-raid Eden capture and the newer distinct-Pokémon Eden lobby each contain 44
guest `0x81:1` records. Comparing every decompressed record by sequence finds **no changed
record bodies**. In the newer lobby, selecting Clodsire still changed only the guest's slot 2.
Thus a guest Pokémon change in a functional two-Eden session does not require a different guest
identity/state record set; it is carried by the later `0x80332e` selection message. This narrows
the crossed physical-Violet behavior toward how that selection is associated with a seat, rather
than a missing guest record body. The new local comparator prints only record counts and change
counts; the private captures remain in `lab/`.

The physical Violet emitted all `0x81:1` sequence numbers 1–46 in `5638`, including 5 and 6;
the functional two-Eden Scarlet guest emitted 44 records and skipped 5–6 in both captures. The
earlier Violet-as-physical-host capture likewise includes host sequences 1–46. Records 5 and 6
are normal 1395-byte kind-2 records after decompression. This is a real source-side difference
between the Violet save/title and the Scarlet Eden reference. It does **not** establish that a
Scarlet host must synthesize two extra records or that the missing records cause crossed slots:
both functional Eden peers used the sparse sequence set. Do not fabricate 5/6 without a
same-title, working reference.
