# Session PlayerInfo preservation — 30 September 2026

Physical test 5831 completed: preserving the identity did not resolve the lobby association.
This compares actual join identities with the host's station lists.
It does not publish player IDs or packet bodies.

| Capture | Guest identity in station list matches its own join | Host and guest PlayerInfo IDs |
| --- | --- | --- |
| Same-save Eden battle (26 September) | yes | equal |
| Distinct-save Eden battle (30 September) | yes | different |
| Synthetic physical test 8264 | no | equal |
| Synthetic physical test 5831, preservation enabled | yes | different |

The old same-save reference made the fixed copied PlayerInfo appear correct. The distinct-save
control reveals that the working Eden host retains the guest's actual Session PlayerInfo,
whereas the synthetic wrapper puts its old captured Eden ID in both host and guest entries.
This is separate from trainer OT/TID/SID and from selected-Pokemon records. The existing
`parse_session_join_v11` reads station locations but ignores the PlayerInfo trailer, which begins
after the second location with player/participant counts and normal encoded PlayerInfo entries.

Added strict `parse_session_join_players_v11` and opt-in `--preserve-guest-session-player` to
retain the joiner's one PlayerInfo when constructing both Session lists. The host's existing
captured PlayerInfo stays unchanged. The concrete physical hypothesis is that the guest's
missing local PlayerInfo causes its game to use the wrong player/seat; this is not established
until the lobby selection test changes visibly.

Tests confirm the exact guest PlayerInfo matches both working distinct-save station lists,
while the physical 8264 lists replace it with the host reference ID. Another test rejects a
missing trailer. Next controlled test is lobby-only, with the established admission and opening
settings plus this single identity-preservation flag. Check default Corviknight on Cyrus, PR/Mew,
then change Cyrus to Iron Hands. Do not start battle until that association is correct.

The battle-start LZ4 rewrite is documented independently in `RAID-START-LZ4.md` and is inactive
in lobby-only mode. Raw evidence remains private.

## Physical result 5831

The incoming selection was Corviknight (823), followed by Iron Hands (992). The outgoing
Session list retained the guest's actual PlayerInfo and distinct host/guest identities.
Nevertheless Cyrus entered visually with Mew, and changing to Iron Hands updated PR's slot 1.
No Ready or battle was attempted. The identity mismatch is real, but correcting it alone is
insufficient; this result does not establish a playable host or correct local-seat association.

Private capture: `lab/sv-raid-session-player-5831.jsonl`, SHA256
`68CA9C8A2A1064AEB3440F9D3FF0D0544785B39783A2D5ED6421629D4929AE55`.
