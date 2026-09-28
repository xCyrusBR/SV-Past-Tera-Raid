#!/usr/bin/env python3
"""Bridge one Eden-room LDN host to a retail console through the ESP32-S3.

Eden assigns 192.168.1.x addresses, while an over-air LDN network uses
169.254.N.x.  Pia authenticates the sender address, so forwarding ciphertext is
not sufficient: this bridge verifies each packet on its source side, translates
the two station addresses in the plaintext, and seals the same Pia envelope for
the destination side.

This is deliberately a diagnostic bridge.  It mirrors the live NetworkInfo
advertisement and records every translated packet; it does not synthesize raid
game messages.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import struct
import sys
import time
import zlib


ROOT = Path(__file__).resolve().parents[1]
POKELDN = ROOT.parent / "pokeldn-research"
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(POKELDN))
sys.path.insert(0, str(POKELDN / "vendor" / "LDN"))

# This must be set before importing pokeldn.ldn; its package initializer binds
# the vendor LDN implementation to the board radio once per process.
DEFAULT_PORT = "COM4"
DEFAULT_KEYS = ROOT / "lab" / "eden-participant" / "user" / "keys" / "prod.keys"

# Select the board backend before importing any pokeldn.ldn module.  Several
# LDN classes bind their WLAN implementation at import time; calling use()
# later is not a complete substitute even though basic TX still appears to
# work.  This matches the initialization order of the proven synthetic host.
os.environ.setdefault("POKELDN_RADIO", f"esp32:{DEFAULT_PORT}")

import enet  # noqa: E402
import zstandard  # noqa: E402

from eden_ldn_participant_probe import (  # noqa: E402
    ID_JOIN_SUCCESS,
    ID_LDN_PACKET,
    ID_PROXY_PACKET,
    ID_SET_GAME_INFO,
    LDN_SCAN,
    LDN_SCAN_RESPONSE,
    game_info_packet,
    join_packet,
    ldn_packet,
)
from pokeldn import sv  # noqa: E402
from pokeldn.host_support import resolve_keys  # noqa: E402
from pokeldn.ldn import ldn_mitm, ldn_mitm_host, pia6, pia_connect, userspace_ip  # noqa: E402
from pokeldn.ldn.transport import HostTransport  # noqa: E402
from past_raids.raid_wire import RAID_GAME_MARKER  # noqa: E402


def proxy_datagram(local_ip: bytes, remote_ip: bytes, data: bytes) -> bytes:
    packed = zstandard.ZstdCompressor().compress(data)
    return (
        bytes([ID_PROXY_PACKET, 1]) + local_ip + struct.pack(">H", sv.PIA_PORT)
        + bytes([1]) + remote_ip + struct.pack(">H", sv.PIA_PORT)
        + bytes([4, 0]) + struct.pack(">I", len(packed)) + packed
    )


def parse_proxy(payload: bytes) -> tuple[bytes, bytes, bool, bytes]:
    if len(payload) < 21 or payload[0] != ID_PROXY_PACKET:
        raise ValueError("short/foreign room proxy packet")
    size = struct.unpack(">I", payload[17:21])[0]
    packed = payload[21:21 + size]
    if len(packed) != size:
        raise ValueError("truncated room proxy packet")
    return (payload[2:6], payload[9:13], bool(payload[16]),
            zstandard.ZstdDecompressor().decompress(packed))


def translate_bytes(data: bytes, mappings: tuple[tuple[bytes, bytes], ...]) -> bytes:
    """Translate station IPv4 byte strings without cascading replacements.

    All mappings are four bytes and are applied longest-path atomically through
    temporary sentinels, preventing A->B followed by B->C from cascading.
    """
    out = bytes(data)
    sentinels = []
    for index, (old, new) in enumerate(mappings):
        marker = bytes((0xF1, 0x7E, index & 0xFF, 0xD3))
        while marker in out:
            marker = bytes((marker[0], marker[1], (marker[2] + 1) & 0xFF, marker[3]))
        out = out.replace(old, marker)
        sentinels.append((marker, new))
    for marker, new in sentinels:
        out = out.replace(marker, new)
    return out


def translate_plaintext(data: bytes, mappings: tuple[tuple[bytes, bytes], ...],
                        net_opening: dict[str, object] | None = None) -> bytes:
    """Translate addresses inside Pia messages, including compressed payloads."""
    messages = pia6.parse_messages(data)
    changed = False
    translated = []
    for message in messages:
        body = translate_bytes(message.payload, mappings)
        changed |= body != message.payload
        flags = message.message_flags
        compressed = message.compressed
        # A retail Violet answered the captured synthetic host only when the
        # establishing Net 0x11 used its native radio spelling: uncompressed,
        # unicast, with the physical LDN station addresses.  Eden emits the
        # same logical request compressed and as a subnet broadcast.  Rebuild
        # only this opening message; subsequent Pia traffic remains a faithful
        # translation of the live Eden host.
        if (net_opening is not None and message.protocol == 0x2C
                and len(body) >= 10 and body[:2] == b"\x01\x11"):
            body = pia_connect.build_net_conn_request(
                int.from_bytes(body[4:8], "big"),
                int.from_bytes(body[8:10], "big"),
                net_opening["host_mac"],
                int(net_opening["network_id"]),
                net_opening["stations"],
                max_stations=4,
                station_size=21,
            )
            flags &= ~(pia6.MESSAGE_FLAG_ZLIB | pia6.MESSAGE_FLAG_NO_BUNDLING)
            compressed = False
            changed = True
        if compressed:
            body = zlib.compress(body)
        translated.append(pia6.build_message(
            body,
            protocol=message.protocol,
            port=message.port,
            message_flags=flags,
            destination=message.destination,
        ))
    if changed and translated:
        return b"".join(translated)
    # Covers uncompressed data that is not a well-formed Pia message bundle.
    return translate_bytes(data, mappings)


def reseal(from_keys, to_keys, from_source_ip: str, to_source_ip: str, raw: bytes,
           mappings, net_opening: dict[str, object] | None = None) -> tuple[bytes | None, str]:
    header, plain, footer = pia6.parse_packet(
        from_keys.session_key, from_source_ip, from_keys.network_id, raw)
    if plain is None:
        return None, "authentication failed"
    plain = translate_plaintext(plain, mappings, net_opening=net_opening)
    return pia6.build_packet(
        to_keys.session_key,
        to_keys.network_id,
        to_source_ip,
        plain,
        dst_var=header.dst_var,
        src_var=header.src_var,
        packet_id=header.packet_id,
        nonce8=header.nonce8,
        footer_ids=footer,
    ), "ok"


def describe_pia(keys, source_ip: str, raw: bytes) -> dict[str, object]:
    """Return a compact decoded packet record for bridge diagnostics."""
    try:
        header, plain, footer = pia6.parse_packet(
            keys.session_key, source_ip, keys.network_id, raw)
        messages = []
        if plain is not None:
            for message in pia6.parse_messages(plain):
                messages.append({
                    "protocol": message.protocol,
                    "port": message.port,
                    "flags": message.message_flags,
                    "destination": message.destination,
                    "compressed": message.compressed,
                    "payload_hex": message.payload.hex(),
                })
        return {
            "authenticated": plain is not None,
            "dst_var": header.dst_var,
            "src_var": header.src_var,
            "packet_id": header.packet_id,
            "nonce": header.nonce8.hex(),
            "footer": footer,
            "messages": messages,
            "raw_hex": raw.hex(),
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "raw_hex": raw.hex()}


def network_fields(info: bytes) -> dict[str, object]:
    if len(info) != ldn_mitm.NETWORK_INFO_SIZE:
        raise ValueError(f"NetworkInfo must be 0x480 bytes, got {len(info):#x}")
    return {
        # Eden's room tunnel publishes a placeholder local communication id
        # (0xffffffffffffffff), so use Scarlet's title id.  Scene 7 is not a
        # placeholder: it is Tera Raid's discovery filter and must be mirrored.
        "comm_id": sv.COMM_ID_SCARLET,
        "scene_id": struct.unpack_from("<H", info, 0x0A)[0],
        "ssid": ldn_mitm.session_id(info),
        "host_mac": ldn_mitm.host_mac(info),
        "channel": struct.unpack_from("<h", info, ldn_mitm_host.OFF_CHANNEL)[0],
        "max_participants": info[ldn_mitm_host.OFF_NODE_COUNT_MAX],
        "app_version": ldn_mitm_host.node_local_comm_version(info, 0),
        "app_data": ldn_mitm.advertise_data(info),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--room-port", type=int, default=24872)
    ap.add_argument("--password", default="1234")
    ap.add_argument("--radio", default=DEFAULT_PORT)
    ap.add_argument("--keys", default=None)
    ap.add_argument("--nickname", default="RadioBridge")
    ap.add_argument("--seconds", type=float, default=600)
    ap.add_argument("--capture", type=Path, required=True)
    args = ap.parse_args()

    os.environ["POKELDN_RADIO"] = f"esp32:{args.radio}"
    # The ldn package may have been imported above before the environment was
    # set. Bind explicitly; use() is idempotent within this process.
    from pokeldn.ldn import esp32_wlan
    esp32_wlan.use(args.radio, log=print)

    args.capture.parent.mkdir(parents=True, exist_ok=True)
    capture = args.capture.open("w", encoding="utf-8", buffering=1)
    start = time.monotonic()

    def record(**row) -> None:
        row["elapsed"] = round(time.monotonic() - start, 6)
        capture.write(json.dumps(row, separators=(",", ":")) + "\n")

    client = enet.Host(None, 1, 1, 0, 0)
    peer = client.connect(enet.Address(args.host.encode(), args.room_port), 1)
    room_ip = room_host_ip = b""
    joined = False
    scan_at = 0.0
    radio = None
    info = None
    room_keys = air_keys = None
    room_associated = False
    physical_guest = None
    physical_guest_ip = None
    physical_guest_mac = None
    room_to_air = air_to_room = auth_failures = 0
    room_packet_samples = 0
    next_radio_status = start
    deadline = start + args.seconds

    try:
        while time.monotonic() < deadline:
            event = client.service(10)
            now = time.monotonic()
            if event.type == enet.EVENT_TYPE_CONNECT:
                peer.send(0, enet.Packet(
                    join_packet(args.nickname, args.password), enet.PACKET_FLAG_RELIABLE))
                client.flush()
                record(event="room_connected")
            elif event.type == enet.EVENT_TYPE_RECEIVE:
                payload = bytes(event.packet.data)
                mid = payload[0] if payload else -1
                if mid == ID_JOIN_SUCCESS and len(payload) >= 5:
                    room_ip = payload[1:5]
                    joined = True
                    peer.send(0, enet.Packet(game_info_packet(), enet.PACKET_FLAG_RELIABLE))
                    client.flush()
                    record(event="room_joined", ip=socket.inet_ntoa(room_ip))
                elif mid == ID_LDN_PACKET and len(payload) >= 15:
                    kind = payload[1]
                    size = struct.unpack(">I", payload[11:15])[0]
                    body = payload[15:15 + size]
                    if kind == LDN_SCAN_RESPONSE and radio is None:
                        room_host_ip = payload[2:6]
                        info = network_fields(body)
                        room_keys = sv.session_keys(info["ssid"])
                        # Eden's per-session four-byte raid marker varies, but
                        # the physical-host sessions that Violet actually
                        # discovered all advertised the canonical marker below.
                        # This is discovery-only: the live Eden application
                        # traffic remains untouched after the station joins.
                        air_app_data = bytearray(info["app_data"])
                        marker_at = 0x5C + 33
                        air_app_data[marker_at:marker_at + 4] = RAID_GAME_MARKER
                        # The proven physical host creates a fresh LDN
                        # SessionId for every hosted network.  Eden reuses its
                        # virtual-room id, which a retail console can cache
                        # after a failed join and then omit from later search
                        # results.  Use independent radio keys and translate
                        # both the Pia authentication and network id.
                        record(event="eden_network", room_host_ip=socket.inet_ntoa(room_host_ip),
                               **{k: (v.hex() if isinstance(v, bytes) else v)
                                  for k, v in info.items()})
                        radio = HostTransport(
                            app_data=air_app_data, password=sv.PASSPHRASE,
                            nickname="PR", keys_path=resolve_keys(
                                args.keys or str(DEFAULT_KEYS)),
                            local_comm_id=info["comm_id"], scene_id=info["scene_id"],
                            app_version=info["app_version"],
                            max_participants=info["max_participants"],
                            channel=info["channel"], protocol=sv.LDN_PROTOCOL,
                            platform=sv.PLATFORM,
                            # Match the exact ESP32/physical-host radio profile
                            # used by the successful SV captures.
                            skip_encryption=True,
                            accept_decrypted_ccmp=True,
                        )
                        radio.start(preflight=False)
                        air_keys = sv.session_keys(radio.ssid)
                        record(event="radio_hosted", ip=radio.our_ip,
                               broadcast=radio.broadcast, ssid=radio.ssid.hex(),
                               room_ssid=info["ssid"].hex(),
                               network_id=air_keys.network_id)
                        print(f"BRIDGE READY code={info['app_data'][92:96].decode(errors='ignore')} "
                              f"air={radio.our_ip} room={socket.inet_ntoa(room_ip)}", flush=True)
                    elif kind == 3:
                        record(event="room_ldn_synced", size=len(body))
                elif (mid == ID_PROXY_PACKET and radio is not None
                      and room_keys is not None and air_keys is not None):
                    source, remote, room_broadcast, raw = parse_proxy(payload)
                    if source != room_host_ip or physical_guest_ip is None:
                        continue
                    if room_packet_samples < 5:
                        record(event="room_pia_sample", sample=room_packet_samples + 1,
                               **describe_pia(room_keys, socket.inet_ntoa(room_host_ip), raw))
                        room_packet_samples += 1
                    mappings = (
                        (room_host_ip, socket.inet_aton(radio.our_ip)),
                        (room_ip, socket.inet_aton(physical_guest_ip)),
                        (pia_connect.ldn_constant_id(info["host_mac"]),
                         pia_connect.ldn_constant_id(radio.our_mac)),
                        (room_keys.network_id.to_bytes(4, "big"),
                         air_keys.network_id.to_bytes(4, "big")),
                    )
                    rebuilt, status = reseal(
                        room_keys, air_keys,
                        socket.inet_ntoa(room_host_ip), radio.our_ip,
                        raw, mappings,
                        net_opening={
                            "host_mac": radio.our_mac,
                            "network_id": air_keys.network_id,
                            "stations": [radio.our_ip, physical_guest_ip],
                        })
                    if rebuilt is None:
                        auth_failures += 1
                        record(event="auth_failed", side="room", count=auth_failures)
                    else:
                        # The proven physical host trace sends Net 0x11 by
                        # unicast.  Other Eden broadcasts keep their original
                        # delivery semantic.
                        rebuilt_desc = describe_pia(air_keys, radio.our_ip, rebuilt)
                        is_net_opening = any(
                            item.get("protocol") == 0x2C
                            and item.get("payload_hex", "").startswith("0111")
                            for item in rebuilt_desc.get("messages", [])
                        )
                        air_destination = (
                            physical_guest_ip if is_net_opening else
                            radio.broadcast
                            if room_broadcast or (len(remote) == 4 and remote[-1] == 0xFF)
                            else physical_guest_ip
                        )
                        radio.send(rebuilt, air_destination)
                        room_to_air += 1
                        if room_to_air <= 5:
                            record(event="air_pia_sample", sample=room_to_air,
                                   **rebuilt_desc)
                        record(event="forward", direction="room_to_air",
                               count=room_to_air, size=len(rebuilt),
                               destination=air_destination,
                               broadcast=air_destination == radio.broadcast)
            elif event.type == enet.EVENT_TYPE_DISCONNECT:
                record(event="room_disconnected")
                break

            if joined and radio is None and now - scan_at >= 0.5:
                peer.send(0, enet.Packet(
                    ldn_packet(LDN_SCAN, room_ip, bytes(4), True), enet.PACKET_FLAG_RELIABLE))
                client.flush()
                scan_at = now

            if radio is not None:
                if now >= next_radio_status:
                    stack = userspace_ip.lookup(radio.iface)
                    record(
                        event="radio_status",
                        rx_seen=getattr(radio, "_rx_seen", 0),
                        participants=len(radio.participants),
                        stack_counters=dict(stack.counters) if stack is not None else {},
                    )
                    next_radio_status = now + 1.0
                if radio.participants and physical_guest is None:
                    physical_guest = radio.participants[0]
                    _index, physical_guest_ip, physical_guest_mac, physical_name = physical_guest
                    # Retail SV changes the Pia advertisement's player count
                    # from one to two as soon as the LDN station is seated.
                    # Keep the mirrored NetworkInfo participant list and the
                    # game-visible count coherent before the Net opening.
                    joined_app_data = bytearray(info["app_data"])
                    if len(joined_app_data) > 0x16:
                        joined_app_data[0x16] = 2
                        radio.set_app_data_later(joined_app_data)
                        record(event="radio_players_updated", num_players=2)
                    # The userspace IPv4 stack otherwise tries ARP before it
                    # can deliver Eden's first Net 0x11.  A retail console may
                    # time out before that resolution completes.  The LDN join
                    # event already gives us the authoritative mapping.
                    radio._pin_neighbour(physical_guest_ip, physical_guest_mac)
                    # Seat the physical station in Eden's LDN network under the
                    # room address while preserving its real MAC/constant id.
                    version = int(info["app_version"])
                    node = ldn_mitm.build_node_info(
                        socket.inet_ntoa(room_ip), physical_guest_mac,
                        physical_name or b"Cyrus", version=version)
                    peer.send(0, enet.Packet(
                        ldn_packet(2, room_ip, room_host_ip, False, node),
                        enet.PACKET_FLAG_RELIABLE))
                    client.flush()
                    room_associated = True
                    record(event="physical_joined", ip=physical_guest_ip,
                           mac=physical_guest_mac.hex(), name=physical_name.hex())
                    print(f"PHYSICAL JOIN {physical_guest_ip}; seating it in Eden", flush=True)

                if (room_associated and physical_guest_ip is not None
                        and room_keys is not None and air_keys is not None):
                    for raw, source_ip in radio.recv():
                        if source_ip != physical_guest_ip:
                            continue
                        mappings = (
                            (socket.inet_aton(radio.our_ip), room_host_ip),
                            (socket.inet_aton(physical_guest_ip), room_ip),
                            (pia_connect.ldn_constant_id(radio.our_mac),
                             pia_connect.ldn_constant_id(info["host_mac"])),
                            (air_keys.network_id.to_bytes(4, "big"),
                             room_keys.network_id.to_bytes(4, "big")),
                        )
                        rebuilt, status = reseal(
                            air_keys, room_keys,
                            physical_guest_ip, socket.inet_ntoa(room_ip),
                            raw, mappings)
                        if rebuilt is None:
                            auth_failures += 1
                            record(event="auth_failed", side="air", count=auth_failures)
                            continue
                        peer.send(0, enet.Packet(
                            proxy_datagram(room_ip, room_host_ip, rebuilt),
                            enet.PACKET_FLAG_RELIABLE))
                        client.flush()
                        air_to_room += 1
                        record(event="forward", direction="air_to_room",
                               count=air_to_room, size=len(rebuilt))
        return 0
    finally:
        if radio is not None:
            radio.stop()
        try:
            peer.disconnect()
            client.flush()
        except Exception:
            pass
        record(event="done", room_to_air=room_to_air, air_to_room=air_to_room,
               auth_failures=auth_failures)
        capture.close()


if __name__ == "__main__":
    raise SystemExit(main())
