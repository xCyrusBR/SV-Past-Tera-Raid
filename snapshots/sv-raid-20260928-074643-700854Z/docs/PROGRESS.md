# Protocol progress and next gate

Updated 2026-09-28. Synthetic host and Eden bridge are independent tracks.

## Synthetic host

1. Confirmed: physical Violet associates with the ESP32-S3-hosted LDN network, completes Net and Pia Session, and reaches the local Mewtwo lobby.
2. Confirmed: guest `0x80332d` Ready is identifiable by its trailing state `1`. The host now gates battle-transition records until this event; the 8642 run previously began transition before Ready.
3. Confirmed: with gating, run 6418 received guest game sequences 1–6. The first four post-transition messages matched the working two-Eden session, but sequence 7 never arrived. On-screen: three Iron Hands, one Dudunsparce, two invisible allies; no HP bar or move menu.
4. Run 7354 configured trainer PR with full ID `4294423561`, independent of the Mew PK9. Violet initially displayed Evan in slot 1. The user later observed PR in slot 3 with Evan's Iron Hands when leaving: host identity is not simply absent; player/slot state is late or misassigned. A matching Pokémon OT is not required for a valid host.
5. The working Eden raid sends port-2 type 9 accept but no type 7 announcement. In the standalone radio host, A/B 2846 omitted type 7 but retained type 9 and the full replay. Violet stayed on “Communicating”; type 7 is restored by default despite being absent in the Eden trace. The difference is still unexplained.

## Gameplay success gate

The host is not working until Violet shows exactly two real trainers in the correct slots (host PR/Mew and guest Evan/Iron Hands), game-generated NPCs for empty places, a running raid timer, and an actionable move menu. Disconnect/NPC replacement should be tested only after that state is reached.

## Data handling

Private evidence remains in the local `lab/` folder and is excluded from GitHub snapshots. Public snapshots include code and summarized observations only. Do not publish keys, ROM/update, saves, PK9, raw packets, or captures with participant identifiers.
