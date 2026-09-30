# Battle transition and bounded reliable retry — 30 September 2026

## Physical control 4276

Paired admissions and the independently decoded LZ4 roster were both enabled. The user saw
four visible participants: PR, Cyrus and two NPCs, with Mew, Iron Hands, Arboliva and Dudunsparce.
There was a brief general buff-like animation, not a confirmed Mewtwo action. Neither the HP bar
nor move menu appeared. After a delay the connection ended and Violet returned to normal play;
the user did not report a software crash this time.

The first entry of the guest's 0x80:0 ACK array advanced to 127 (sequences through 126).
The replay still sent through 219. The final ACK had an empty selective mask. The working Eden
reference reaches ACK 220. The synthetic host's outgoing control ACK lowest-pending values
advanced through 159, 213 and 220 while the peer had not confirmed the complete replay.
This exposes a reliability limitation of replaying reference timing without a live resend window;
it does not prove whether packet loss, game initialization, or another defect caused the stall.

Private capture `lab/sv-raid-admission-lz4-battle-4276.jsonl`, SHA256
`893C2CFD6899D9698D2462A096E39FB3817EB37A9E704A7EF82C6874E3F284F6`.

## Opt-in diagnostic

`--raid-reliable-retry` retains the actual outgoing battle fragments (sequences 44–219), including
the corrected LZ4 roster, flags and original sequence numbers. It uses ACK array position 0 for
the host; the repeated stream_id byte is not a station selector. Confirmed fragments are removed.
The oldest outstanding fragment is retried at most eight times, no faster than every 350 ms.
Control and data lowest-pending fields cannot advance past an outstanding tracked fragment.
Scheduled records more than 95 sequences ahead are deferred without losing or renumbering them.
Payloads are not invented, concatenated, or edited during retry. A new Session Join resets tracking.

This is not a full general Pia reliable sender and does not handle sequence wrap, other game
streams or future live battle decisions. The known replay ends at 219. Success still requires an
actual move menu and advancing raid timer, not just ACK 220. No host-disconnect test yet.

Local validation: 52 project tests pass, covering retry payload/flag preservation, oldest-gap
tracking, monotonic ACKs, bounded attempts, default-off behavior and ignored opening records.
The updated runtime and wrapper compile. Next physical test preserves the 4276 settings and
adds only this diagnostic retry mode.

## Physical retry result 8352

No HP or menu appeared; the scene remained after the Pokemon release and brief buff-like sound,
then Violet returned to the world. Guest ACK stopped at 116 (through 115). Fragment 116 was retried
eight times without a new confirmation; the bounded window deferred the end of the replay and
the last sent sequence was 211. The host log records guest deauthentication reason 3. There was
no runtime handler traceback. Retrying alone did not fix the initialization.

Private capture `lab/sv-raid-reliable-retry-8352.jsonl`, SHA256
`967BB5824B8543565BB9C3AE7D8568AC12D85989E56E3EA6922A90E61311F805`.

Next isolated diagnostic: `--raid-replay-spacing 0.02` defers scheduled battle fragments so the
main loop can process incoming traffic between sends rather than sending all overdue records
before its next `transport.recv()`. Sequence, payload and boundary flags remain unchanged; new
Session Join resets pacing. Enable private ESP32 tracing for board TX/drop counters. This tests
burst pressure, not a confirmed explanation for the stall, and does not change working lobby data.

## Paced trial 6407 and scheduler correction

The user reported the same frozen initialization and return to the world. Guest maximum ACK was
77; retries targeted 85 eight times, and the last scheduled send was 175. Auditing the actual
send order found overtaking introduced by the new pacing: 58 preceded unsent 57, and 86/88/89
preceded 72–84. Therefore this trial is not a clean validation of paced delivery. It is a
scheduler regression, not evidence that the validated admission/roster stopped working.

Added `replay_send_due`: a new sequence cannot exceed the sender's next expected sequence;
captured retries of already sent sequences remain allowed. Pacing defers the original record
without renumbering it. A regression test covers both observed overtakes, timing, and old retries.
Next physical trial keeps the same settings with this ordering correction.

ESP32 counters did not grow for wire drops between join, Ready and the last guest message:
50860 throughout; UART overflow stayed 0. ETH TX failures were 10944 at join and Ready, rising
to 10961 near the last guest message/deauthentication; cumulative counters must not be mistaken
for new errors in this trial. This does not establish a hardware fault or justify reflashing.

Private capture `lab/sv-raid-paced-6407.jsonl`, SHA256
`91AB6D4D09AB80059484FBC434AB58EC80D75045D109CA666D9E0DA431CFED91`.
The separate ESP32 trace remains private.

## Ordered paced result 2185

The user again reported no HP/menu and return to the world. Auditing scheduled sends confirms
zero overtakes this time. Maximum guest ACK was 110 (through 109); fragment 110 was retried eight
times and the last scheduled sequence was 205. Therefore ordered pacing plus retries still does
not yield a playable initialization. Keep the validated lobby/visible roster baseline separate
from these unsuccessful delivery diagnostics.

Private capture `lab/sv-raid-ordered-paced-2185.jsonl`, SHA256
`5A4AAB3F0BDD919F1E8E2714011FC2F0140C9F204D37B9B140658F3DA57A4E95`.

## Start promptly after guest Ready

At the user's request, `--start-on-ready` advances the first host transition to approximately
100 ms after receipt of the guest Ready event, rather than retaining the reference's 42.7-second
join-relative floor. It anchors to the actual pending transition after any selection-gate shift.
Remaining countdown predecessors are transmitted, not dropped; fragment ordering still waits
for them. The late Session commit moves with the transition. Relative internal phase delays
remain unchanged: battle roster sequence 52 is 7.445 seconds after transition sequence 44, so
scene loading is not instantaneous. This shortens the avoidable wait without skipping protocol
phases. It is opt-in, requires live timing validation, and is not a fix for the missing battle menu.
