# Protocol progress and next gate

Updated 2026-09-28. Synthetic host and Eden bridge are independent tracks.

## Synthetic host

1. Confirmed: physical Violet associates with the ESP32-S3-hosted LDN network, completes Net and Pia Session, and reaches the local Mewtwo lobby.
2. Confirmed: guest `0x80332d` Ready is identifiable by its trailing state `1`. The host now gates battle-transition records until this event; the 8642 run previously began transition before Ready.
3. Confirmed: with gating, run 6418 received guest game sequences 1–6. The first four post-transition messages matched the working two-Eden session, but sequence 7 never arrived. On-screen: three Iron Hands, one Dudunsparce, two invisible allies; no HP bar or move menu.
4. Run 7354 configured trainer PR with full ID `4294423561`, independent of the Mew PK9. The physical Violet user saw their own Iron Hands in slot 1; on leaving, PR appeared in slot 3 with that Iron Hands. The radio log identified the physical trainer separately from Evan, who belongs to the Scarlet save/reference, not to the physical guest or a second synthetic participant. Host identity is not simply absent; player/slot state is late or misassigned. A matching Pokémon OT is not required for a valid host.
5. The working Eden raid sends port-2 type 9 accept but no type 7 announcement. In the standalone radio host, A/B 2846 omitted type 7 but retained type 9 and the full replay. Violet stayed on “Communicating”; type 7 is restored by default despite being absent in the Eden trace. The difference is still unexplained.
6. A diagnostic `--port2-announce-slot 0` A/B is prepared to test whether the extra type-7 message assigns the host to the wrong position. The ordinary mode remains slot 1, as before. This is a hypothesis, not a validated fix.

## Next controlled comparison

No second synthetic trainer is needed. First compare the offline identity and roster fields in the accepted two-Eden reference with the synthetic host's generated Session updates and kind-1 game record. Keep distinct: PR's trainer ID/name, the Mew's OT/ID, the physical guest's trainer identity, and that guest's selected Pokémon. The current wrapper contains no literal Evan participant; Evan is from the Scarlet save/reference and must not be copied into the synthetic roster. Then, when the physical Switch is available, run one short A/B of port-2 slot assignment while recording the lobby order *before* Ready. If the host still appears late or with the guest's Pokémon, fix that mapping before another full battle attempt. Related raid-injection and bot projects do not supply this live LDN mapping.

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
