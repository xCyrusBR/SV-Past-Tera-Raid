# Protocol progress and next gate

Updated 2026-09-28. Synthetic host and Eden bridge are independent tracks.

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

## Next controlled comparison

No second synthetic trainer is needed. Keep distinct: PR's trainer ID/name, the Mew's OT/ID, the physical guest's trainer identity, and that guest's selected Pokémon. The current wrapper contains no literal Evan participant; Evan is from the Scarlet save/reference and must not be copied into the synthetic roster. The type-7 slot and offline-account A/Bs failed to correct the lobby. The next controlled physical A/B, when convenient, should hold all else constant and try `--session-seq-base 0` in lobby-only mode. If it again reaches a blank roster, compare Session reply flags/ACK separately; do not sweep several variables at once. Related raid-injection and bot projects do not supply this live LDN mapping.

Offline comparison completed: the working two-Eden Session updates contain exactly two
stations, indexed 0/1, with one PlayerInfo each. The host and guest kind-1 stream records carry
their game-level trainer identities; the battle-start `0x80332f` contains a local selected PK9 at
offset 21 and Mewtwo at 724. The synthetic host already patches the former with Violet's actual
selection, so changing it to Mew would repeat a known regression. The reference used identical
selected PK9 bytes on both Edens, limiting what it proves about different team choices. See
`ROSTER-AUDIT.md`; no protocol change is justified from this offline comparison alone.
Decryption of runs 7318 and 6418 additionally showed that the earlier HP-bar attempt sent
battle-start fragments 52/53 as two complete messages and gave the physical guest PR's Mew,
despite its captured Iron Hands selection. The newer run repaired both faults and still received
guest sequences 1–6, but no move menu. Do not restore the older packet shape merely to recover
the HP animation.

## Gameplay success gate

The host is not working until Violet shows exactly two human-trainer seats in the correct slots (synthetic host PR/Mew in slot 1 and the physical Violet guest with their own chosen Pokémon in slot 2), correctly initialized NPC allies after Start, a running raid timer, and an actionable move menu. The physical guest's name can change with the save/profile. Evan is a Scarlet save/reference identity and should not be injected as another synthetic player. The user's observed fill-with-others message appears at Start; whether the host must send NPC selection/seed data remains unverified. Disconnect/NPC replacement should be tested only after that state is reached.

## Data handling

Private evidence remains in the local `lab/` folder and is excluded from GitHub snapshots. Public snapshots include code and summarized observations only. Do not publish keys, ROM/update, saves, PK9, raw packets, or captures with participant identifiers.

New private capture SHA-256: `sv-raid-slot0-4186.jsonl` = `ADABE182F4BC43FF333C2B87DAACC3F916F465C6F38C338345618108B34AD732`; `sv-raid-slot1-control-9024.jsonl` = `D6A4D1A2D63547157095CCB60C36D13A2644A09743F719E37EFE184CE6323350`; `sv-raid-reference-timing-5649.jsonl` = `9BC0387D60E6BAD65C77DA44EC453464D65BEAD9101C71428293081F123F1B3B`; `sv-raid-offline-account-6742.jsonl` = `6AF1BD64EA84704BB46298DB6F261970A0F4619F7A3E0F24EE5325EF2A3A5E27`.
