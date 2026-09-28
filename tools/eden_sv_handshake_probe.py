from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import time
from pathlib import Path

import enet
import zstandard


POKELDN = Path(__file__).resolve().parents[2] / "pokeldn-research"
sys.path.insert(0, str(POKELDN))

from pokeldn import sv  # noqa: E402
from pokeldn.sv import streams  # noqa: E402
from pokeldn.ldn import pia6, pia_connect, reliable5  # noqa: E402
from pokeldn.pla import game_channel  # noqa: E402


ID_JOIN_REQUEST = 1
ID_JOIN_SUCCESS = 2
ID_SET_GAME_INFO = 4
ID_PROXY_PACKET = 5
ID_LDN_PACKET = 6
LDN_SCAN = 0
LDN_SCAN_RESPONSE = 1
LDN_CONNECT = 2

PROTO_NET = 0x2C
PROTO_RTT = 0x58
PROTO_RELIABLE = 0x7C
PROTO_BROADCAST_RELIABLE = 0x80
PROTO_STREAM_BROADCAST_RELIABLE = 0x81
PROTO_SESSION = 0x98
PROTO_CLONE_CLOCK = 0x77
CLOCK_REQUEST = bytes(18)
RELIABLE_PROTOCOLS = (PROTO_BROADCAST_RELIABLE, PROTO_STREAM_BROADCAST_RELIABLE)
MESH_ADDRESSED = (PROTO_RTT,) + RELIABLE_PROTOCOLS
ESTABLISHING_FLAGS = pia6.MESSAGE_FLAG_SKIP_SOURCE_CHECK
OUR_VAR = 0xC493
CHANNEL_PORT1_OPEN = bytes.fromhex(
    "b90104b902b9027b0001b902b902320101b902b902320201b902b902320301"
)
CHANNEL_PORT2_OPEN = bytes.fromhex("03b90200bc09000000000000000000")
CHANNEL_PORT1_READY = bytes.fromhex(
    "b90102b902b90280803301b902b90280803401"
)
# First Scarlet application record emitted by a real joiner immediately after
# the game channels become ready.  This opens broadcast-reliable port 0 and
# announces the joiner's lobby state; unlike the following trainer blob, this
# record contains no captured player-specific material.
BROADCAST_GAME_OPEN = bytes.fromhex(
    "1f000023000100010300000001"
    "484b6a30d66564640001090608e001936c409a054822c401000000ffff03002b36013b"
)
# The immediately-following trainer announcement from the validated two-Eden
# capture.  It is the application record that causes Scarlet to construct the
# guest slot; replaying it is intentional for this protocol milestone test.
BROADCAST_TRAINER_ANNOUNCE = bytes.fromhex(
    "0700016a00020001030000000180332e01020000000000580100000000000023779f190000"
    "8324cb84b743062805abd2bc683b80be69c4750616e80a43215ca40b6485ce17c8c1b709"
    "c8f6418534fbb30ce35f0a8591ee87f30d139f11c491bc9f42a507b01de5d34c81ffc179"
    "26ff309c0517ed88f656d9d766f6c836c65f7d43629004cbc44938514d61b78127fc95b3"
    "c50c830b829c53942853f7eb6f376c734a66515e015e52f26305d48793cd7b0f46200772"
    "64731f96d821fea0866240c6beb18b79a28ea77839dd7c057d60d2448fdb78530875a666"
    "29e2ecdb7f24f3723db8287fb4958912830a901b6e846f50339d1d8c1af0903b12eb1449"
    "c46bbee8c38ce889ab8ef8d067ada40be694cf06bbd1703ea9f89586acba63cb7f387c37"
    "bc999018ef71278a6fb65ea680eed448e40bdd01aaf58887ad5e8b9a643dbdee3078af0cc"
    "e8caac83f32a4f9c4b3f848b9b554c26ffbfcd4a94bcc06ffe4a65caebaafc524ab2087"
    "d8420137c3561290613a0bbe68c4"
)
BROADCAST_READY = bytes.fromhex(
    "17000026000300030300000001"
    "484b6a30d66564660001090608e001936c409a054832303042c501000000ffff03002aca0126"
)
BROADCAST_READY_REFRESH = bytes.fromhex(
    "17000026000400040300000001"
    "484b6a30d66564610001090608e001936c409a05483230f042c501000000ffff03002b500133"
)
BROADCAST_START_ACK = bytes.fromhex(
    "0700001a000500050300000001"
    "3201730001000000000008000000000000000100000001000000"
)
BROADCAST_LOAD_ACK = bytes.fromhex(
    "07000016000600060300000001"
    "803493010100000000000400000000000000ed030000"
)
BROADCAST_BATTLE_LOAD = (
    bytes.fromhex("17000022000700070300000001484baa66105667606062806005280d028c0ca880152a01000000ffff030028a700e4"),
    bytes.fromhex("17000026000800080300000001484baa6610566760606280600520166280002628cd08a559a10200000000ffff03002acf00f6"),
    bytes.fromhex("17000026000900090300000001484baa6610566760606280600520166380006628cd04a559a10c00000000ffff03002b7700fc"),
    bytes.fromhex("17000026000a000a0300000001484baa6610566760606280600520666380007628cd04a559a10c00000000ffff030029d700f0"),
    bytes.fromhex("17000026000b000b0300000001484baa6610566760606280600520f66080000e28cd04a559a10c00000000ffff0300322f0133"),
)
CAPTURED_GUEST_PLAYER_ID = bytes.fromhex("a5b9defccd3b551fb249360d27546e03")


def string(value: str) -> bytes:
    raw = value.encode("utf-8")
    return struct.pack(">I", len(raw)) + raw


def room_join(nickname: str, password: str) -> bytes:
    return bytes([ID_JOIN_REQUEST]) + string(nickname) + bytes([255]) * 4 + struct.pack(">I", 1) + string(password) + string("")


def game_info() -> bytes:
    return bytes([ID_SET_GAME_INFO]) + string("Pokemon Scarlet") + struct.pack(">Q", 0x0100A3D008C5C000) + string("4.0.0")


def ldn(packet_type: int, local_ip: bytes, remote_ip: bytes, broadcast: bool, data: bytes = b"") -> bytes:
    return bytes([ID_LDN_PACKET, packet_type]) + local_ip + remote_ip + bytes([broadcast]) + struct.pack(">I", len(data)) + data


def node_info(local_ip: bytes, name: str, version: int) -> bytes:
    return (
        local_ip[::-1]
        + bytes([2, 0]) + local_ip
        + bytes([0, 1])
        + name.encode()[:32].ljust(33, bytes(1))
        + bytes(1)
        + struct.pack("<h", version)
        + bytes(16)
    )


def proxy_datagram(local_ip: bytes, remote_ip: bytes, raw: bytes) -> bytes:
    compressed = zstandard.ZstdCompressor().compress(raw)
    return (
        bytes([ID_PROXY_PACKET, 1]) + local_ip + struct.pack(">H", sv.PIA_PORT)
        + bytes([1]) + remote_ip + struct.pack(">H", sv.PIA_PORT)
        + bytes([4, 0]) + struct.pack(">I", len(compressed)) + compressed
    )


def parse_proxy(payload: bytes) -> tuple[bytes, bytes, bytes]:
    size = struct.unpack(">I", payload[17:21])[0]
    return payload[2:6], payload[9:13], zstandard.ZstdDecompressor().decompress(payload[21:21 + size])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=24872)
    ap.add_argument("--password", default="past-raids")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--timeout", type=float, default=150)
    args = ap.parse_args()

    client = enet.Host(None, 1, 1, 0, 0)
    peer = client.connect(enet.Address(args.host.encode(), args.port), 1)
    start = time.monotonic()
    deadline = start + args.timeout
    local_ip = host_ip = b""
    keys = None
    our_const = None
    host_var = None
    host_const = None
    session_joined = False
    session_joined_at = None
    clock_sent = False
    last_rtt_originated = 0.0
    join_sequence = None
    pending_update = None
    streams_opened = False
    identity_sent = False
    identity_acked = False
    identity_payload = None
    last_identity_send = 0.0
    mirrored_records: list[bytes] = []
    mirrored_host_sequences: set[int] = set()
    next_mirror_to_send = 0
    channel_table = None
    channel_opened = False
    channel_seq = {game_channel.JOINER_PORT: 1, 2: 1}
    channel_port2_opened = False
    channel_port2_opened_at = None
    channel_port1_ready = False
    broadcast_game_open_sent = False
    broadcast_trainer_sent = False
    broadcast_game_open_at = None
    broadcast_trainer_at = None
    broadcast_ready_sent = False
    broadcast_ready_at = None
    post_ready_stage = 0
    host_start_seen_at = None
    battle_load_next_at = None
    battle_load_index = 0
    channel_port1_ready_at = None
    stream_high: dict[tuple[int, int], int] = {}
    our_seq: dict[tuple[int, int], int] = {}
    joined_room = associated = False
    last_scan = last_join = 0.0
    nonce_counter = int.from_bytes(os.urandom(8), "big")
    packet_counter = 0
    # The application-layer trainer announcement below is still a replay from
    # the validated RaidGuest capture.  Keep Session PlayerInfo and the first
    # mirrored state record on that same identity until the announcement is
    # generated structurally rather than replayed.
    player_id = CAPTURED_GUEST_PLAYER_ID
    record_count = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("", encoding="utf-8")

    def record(**item: object) -> None:
        nonlocal record_count
        item["elapsed"] = round(time.monotonic() - start, 6)
        with args.output.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(item, separators=(",", ":")) + "\n")
        record_count += 1

    def send_pia(body: bytes, protocol: int, dst_var: int, flags: int = 0,
                 label: str = "", port: int = 0) -> None:
        nonlocal nonce_counter, packet_counter
        assert keys is not None and local_ip and host_ip
        msg = pia6.build_message(body, protocol=protocol, port=port, message_flags=flags)
        packet_dst = 1 if protocol in MESH_ADDRESSED else dst_var
        footer_ids = (dst_var,) if protocol in MESH_ADDRESSED else ()
        raw = pia6.build_packet(
            keys.session_key, keys.network_id, bytes(local_ip), msg,
            dst_var=packet_dst, src_var=OUR_VAR, nonce8=nonce_counter.to_bytes(8, "big"),
            packet_id=packet_counter, footer_ids=footer_ids,
        )
        nonce_counter = (nonce_counter + 1) & ((1 << 64) - 1)
        packet_counter = (packet_counter + 1) & 0xFFFF
        peer.send(0, enet.Packet(proxy_datagram(local_ip, host_ip, raw), enet.PACKET_FLAG_RELIABLE))
        client.flush()
        record(event="pia_out", label=label, protocol=protocol, dst_var=dst_var, raw=raw.hex())

    while time.monotonic() < deadline:
        event = client.service(25)
        now = time.monotonic()
        if event.type == enet.EVENT_TYPE_CONNECT:
            peer.send(0, enet.Packet(room_join(f"RaidHandshake-{os.getpid()}", args.password), enet.PACKET_FLAG_RELIABLE))
            record(event="enet_connected")
        elif event.type == enet.EVENT_TYPE_RECEIVE:
            payload = bytes(event.packet.data)
            mid = payload[0] if payload else -1
            if mid == ID_JOIN_SUCCESS:
                local_ip = payload[1:5]
                our_const = pia_connect.ldn_constant_id(bytes([2, 0]) + local_ip)
                joined_room = True
                peer.send(0, enet.Packet(game_info(), enet.PACKET_FLAG_RELIABLE))
                record(event="room_joined", local_ip=".".join(map(str, local_ip)))
            elif mid == ID_LDN_PACKET and len(payload) >= 15:
                kind = payload[1]
                size = struct.unpack(">I", payload[11:15])[0]
                data = payload[15:15 + size]
                record(event="ldn_in", kind=kind, size=len(data))
                if kind == LDN_SCAN_RESPONSE and not associated:
                    host_ip = payload[2:6]
                    keys = sv.session_keys(data[0x10:0x20])
                    version = struct.unpack_from("<h", data, 0x68 + 46)[0]
                    peer.send(0, enet.Packet(ldn(LDN_CONNECT, local_ip, host_ip, False, node_info(local_ip, "Player", version)), enet.PACKET_FLAG_RELIABLE))
                    client.flush()
                    associated = True
                    record(event="ldn_connect_sent", host_ip=".".join(map(str, host_ip)), ssid=keys.ssid.hex(), network_id=keys.network_id)
            elif mid == ID_PROXY_PACKET and keys is not None:
                source_ip, _, raw = parse_proxy(payload)
                header, plain, footer = pia6.parse_packet(keys.session_key, bytes(source_ip), keys.network_id, raw)
                record(event="pia_in", authenticated=plain is not None, header=repr(header), footer=footer, raw=raw.hex())
                if plain is None:
                    continue
                for msg in pia6.parse_messages(plain):
                    record(event="message", protocol=msg.protocol, port=msg.port, flags=msg.message_flags, payload=msg.payload.hex())
                    if msg.protocol == PROTO_NET:
                        req = pia_connect.parse_net_conn_request(msg.payload)
                        if req:
                            host_var, host_const, seqid = req
                            send_pia(pia_connect.build_net_response(seqid), PROTO_NET, 0, ESTABLISHING_FLAGS, "net_0x12")
                        elif len(msg.payload) >= 8 and msg.payload[:2] == bytes([1, pia_connect.NET_UPDATE_PROPERTY]):
                            seqid = int.from_bytes(msg.payload[4:8], "big")
                            send_pia(pia_connect.build_net_property_ack(seqid), PROTO_NET, 0, ESTABLISHING_FLAGS, "net_0x51")
                    elif msg.protocol == PROTO_SESSION and msg.payload:
                        kind = msg.payload[0]
                        if kind == pia_connect.SESSION_JOIN_RESPONSE:
                            response = pia_connect.parse_session_join_response_v11(msg.payload)
                            if response is not None and response["status"] == 1:
                                session_joined = True
                                session_joined_at = now
                                join_sequence = response["sequence_id"]
                                record(event="session_joined", via="response", sequence=join_sequence)
                                if pending_update is not None:
                                    ack = pia_connect.build_session_update_ack_v11(our_const, pending_update["sequence_id"])
                                    send_pia(ack, PROTO_SESSION, host_var or 0, 0, "session_update_ack")
                                    pending_update = None
                        elif kind == pia_connect.SESSION_UPDATE:
                            update = pia_connect.parse_session_update_v11(msg.payload, route_bytes=0)
                            if update is not None:
                                record(event="session_update", sequence=update["sequence_id"], stations=len(update["stations"]))
                                if (broadcast_ready_sent and update["sequence_id"] >= 1
                                        and len(update["stations"]) >= 2 and host_start_seen_at is None):
                                    host_start_seen_at = now
                                    record(event="host_start_seen", sequence=update["sequence_id"])
                                if not session_joined and any(st["variable_id"] == OUR_VAR for st in update["stations"]):
                                    session_joined = True
                                    session_joined_at = now
                                    join_sequence = update["sequence_id"]
                                    record(event="session_joined", via="update", sequence=join_sequence)
                                if join_sequence is None:
                                    pending_update = update
                                else:
                                    ack = pia_connect.build_session_update_ack_v11(our_const, update["sequence_id"])
                                    send_pia(ack, PROTO_SESSION, host_var or 0, 0, "session_update_ack")
                    elif msg.protocol == PROTO_RTT and msg.payload and msg.payload[0] == 0:
                        send_pia(streams.build_rtt_response(msg.payload, header.src_var), PROTO_RTT, header.src_var, 0, "rtt_response")
                    elif msg.protocol == PROTO_RELIABLE and len(msg.payload) >= reliable5.HEADER_SIZE:
                        try:
                            channel_message = reliable5.parse(msg.payload)
                        except ValueError:
                            continue
                        if channel_message["flags"] & reliable5.FLAG_APPLICATION_DATA:
                            channel_ack = game_channel.build_ack(
                                channel_message["sequence_id"] + 1,
                                lowest_pending=channel_seq.get(msg.port, 1),
                            )
                            send_pia(channel_ack, PROTO_RELIABLE, host_var or header.src_var, 0,
                                     "channel_ack", port=msg.port)
                            if msg.port == game_channel.JOINER_PORT:
                                if (channel_table is None
                                        and channel_message["flags"] & reliable5.FLAG_IS_INITIALIZED):
                                    channel_table = channel_message["payload"]
                                    record(event="channel_table_captured",
                                           host_sequence=channel_message["sequence_id"],
                                           size=len(channel_table))
                    elif msg.protocol in RELIABLE_PROTOCOLS and len(msg.payload) >= reliable5.HEADER_SIZE:
                        try:
                            reliable = reliable5.parse(msg.payload)
                        except ValueError:
                            continue
                        if reliable["flags"] & reliable5.FLAG_APPLICATION_DATA:
                            key = (msg.protocol, msg.port)
                            stream_high[key] = max(stream_high.get(key, 0), reliable["sequence_id"])
                            ack = streams.build_ack(
                                {streams.HOST_INDEX: stream_high[key]},
                                our_seq.get(key, 1), streams.JOINER_INDEX,
                            )
                            # Scarlet 4.0.0's emulated-host path drops otherwise identical bulk
                            # acknowledgements under 0xA0; 0x00 reaches and advances its window.
                            send_pia(ack, msg.protocol, host_var or header.src_var, 0,
                                     "reliable_ack", port=msg.port)
                            if (msg.protocol == streams.PROTOCOL_STREAM
                                    and msg.port == streams.HOST_INDEX
                                    and reliable["flags"] & reliable5.FLAG_ZLIB
                                    and reliable["sequence_id"] not in mirrored_host_sequences):
                                mirrored_host_sequences.add(reliable["sequence_id"])
                                mirrored_records.append(reliable["payload"])
                                record(event="record_queued", host_sequence=reliable["sequence_id"],
                                       queue_index=len(mirrored_records))
                            if (not identity_sent
                                    and msg.protocol == streams.PROTOCOL_STREAM
                                    and msg.port == streams.HOST_INDEX
                                    and reliable["flags"] & reliable5.FLAG_ZLIB):
                                try:
                                    identity = bytearray(streams.decompress(reliable["payload"]))
                                except Exception:
                                    identity = bytearray()
                                if len(identity) == 1395 and identity[0] == 1:
                                    # The two-client Scarlet capture differs only here: bytes
                                    # 11..14 are the player's four-byte identity and bytes
                                    # 19..82 are its UTF-16LE display-name field. Every later
                                    # state record is byte-identical between host and joiner.
                                    identity[11:15] = player_id[:4]
                                    identity[19:83] = bytes(64)
                                    display_name = "RaidProbe".encode("utf-16le")
                                    identity[19 : 19 + len(display_name)] = display_name
                                    identity_payload = streams.compress(identity)
                                    identity_sent = True
                                    record(event="identity_captured", mode="patched_guest_identity",
                                           plain_size=len(identity),
                                           compressed_size=len(identity_payload),
                                           identity4=player_id[:4].hex(), name="RaidProbe")
                        elif (msg.protocol == streams.PROTOCOL_STREAM
                              and msg.port == streams.JOINER_INDEX and reliable.get("is_ack")):
                            try:
                                ack_payload = reliable5.parse_ack_payload(reliable["payload"])
                            except ValueError:
                                ack_payload = {"entries": []}
                            entries = ack_payload["entries"]
                            if len(entries) > streams.JOINER_INDEX and entries[streams.JOINER_INDEX]["ack_id"] > 1:
                                identity_acked = True
                                record(event="identity_acked", ack_id=entries[streams.JOINER_INDEX]["ack_id"])
        elif event.type == enet.EVENT_TYPE_DISCONNECT:
            record(event="enet_disconnected")
            break

        if joined_room and not associated and now - last_scan >= 1:
            peer.send(0, enet.Packet(ldn(LDN_SCAN, local_ip, bytes(4), True), enet.PACKET_FLAG_RELIABLE))
            client.flush()
            last_scan = now
        if associated and not session_joined and host_var is not None and host_const is not None and now - last_join >= 0.75:
            body = pia6.build_session_join(
                our_const, OUR_VAR, bytes(local_ip), host_const, host_var,
                " ", os.urandom(4), player_id=player_id,
            )
            send_pia(body, PROTO_SESSION, 0, ESTABLISHING_FLAGS, "session_join")
            last_join = now
        if session_joined and not clock_sent and host_var is not None:
            send_pia(CLOCK_REQUEST, PROTO_CLONE_CLOCK, host_var, 0, "clone_clock_request")
            clock_sent = True
        if session_joined and host_var is not None and now - last_rtt_originated >= 0.5:
            stamp = (int(now * 1000) & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "big")
            send_pia(streams.build_rtt_request(stamp), PROTO_RTT, host_var, 0, "rtt_request")
            last_rtt_originated = now
        if session_joined and not streams_opened and session_joined_at is not None and now - session_joined_at >= 0.75:
            streams_opened = True
            for protocol, port in streams.every_stream():
                ack = streams.build_ack({}, 1, streams.JOINER_INDEX, unknown0=1)
                send_pia(ack, protocol, host_var or 0, 0, "opening_ack", port=port)
                if protocol == streams.PROTOCOL_STREAM and port in streams.OPEN_PORTS[streams.JOINER_INDEX]:
                    opening = streams.build_open(port, streams.JOINER_INDEX)
                    our_seq[(protocol, port)] = 2
                    send_pia(opening, protocol, host_var or 0, streams.MESSAGE_FLAGS_DATA,
                             "stream_open", port=port)
            record(event="streams_opened")
        if streams_opened and next_mirror_to_send < len(mirrored_records):
            record_sequence = next_mirror_to_send + 1
            record_payload = (
                identity_payload
                if record_sequence == 1 and identity_payload is not None
                else mirrored_records[next_mirror_to_send]
            )
            record_message = streams.build_record_message(
                record_payload, record_sequence, streams.JOINER_INDEX,
                initialized=(record_sequence == 1),
            )
            send_pia(record_message, streams.PROTOCOL_STREAM, host_var or 0,
                     streams.MESSAGE_FLAGS_DATA, "mirrored_record", port=streams.JOINER_INDEX)
            our_seq[(streams.PROTOCOL_STREAM, streams.JOINER_INDEX)] = record_sequence + 1
            next_mirror_to_send += 1
        if streams_opened and channel_table is not None and not channel_opened:
            outgoing = game_channel.build_open(
                CHANNEL_PORT1_OPEN, channel_seq[game_channel.JOINER_PORT], initialized=True,
            )
            send_pia(outgoing, PROTO_RELIABLE, host_var or 0, 0,
                     "channel_table_open", port=game_channel.JOINER_PORT)
            channel_seq[game_channel.JOINER_PORT] += 1
            channel_opened = True
            record(event="channel_opened")
        if channel_opened and not channel_port2_opened:
            outgoing = game_channel.build_open(CHANNEL_PORT2_OPEN, channel_seq[2], initialized=True)
            send_pia(outgoing, PROTO_RELIABLE, host_var or 0, 0,
                     "channel_port2_join", port=2)
            channel_seq[2] += 1
            channel_port2_opened = True
            channel_port2_opened_at = now
            record(event="channel_port2_opened")
        if (channel_port2_opened and not channel_port1_ready
                and channel_port2_opened_at is not None and now - channel_port2_opened_at >= 0.25):
            outgoing = game_channel.build_open(
                CHANNEL_PORT1_READY,
                channel_seq[game_channel.JOINER_PORT],
                initialized=False,
            )
            send_pia(outgoing, PROTO_RELIABLE, host_var or 0, 0,
                     "channel_port1_ready", port=game_channel.JOINER_PORT)
            channel_seq[game_channel.JOINER_PORT] += 1
            channel_port1_ready = True
            channel_port1_ready_at = now
            record(event="channel_port1_ready")
        if (channel_port1_ready and not broadcast_game_open_sent
                and channel_port1_ready_at is not None and now - channel_port1_ready_at >= 0.25):
            send_pia(
                BROADCAST_GAME_OPEN,
                PROTO_BROADCAST_RELIABLE,
                host_var or 0,
                0,
                "broadcast_game_open",
                port=0,
            )
            our_seq[(PROTO_BROADCAST_RELIABLE, 0)] = 2
            broadcast_game_open_sent = True
            broadcast_game_open_at = now
            record(event="broadcast_game_open_sent")
        if (broadcast_game_open_sent and not broadcast_trainer_sent
                and broadcast_game_open_at is not None and now - broadcast_game_open_at >= 0.05):
            send_pia(
                BROADCAST_TRAINER_ANNOUNCE,
                PROTO_BROADCAST_RELIABLE,
                host_var or 0,
                0,
                "broadcast_trainer_announce",
                port=0,
            )
            our_seq[(PROTO_BROADCAST_RELIABLE, 0)] = 3
            broadcast_trainer_sent = True
            broadcast_trainer_at = now
            record(event="broadcast_trainer_sent")
        if (broadcast_trainer_sent and not broadcast_ready_sent
                and broadcast_trainer_at is not None and now - broadcast_trainer_at >= 0.75):
            send_pia(
                BROADCAST_READY,
                PROTO_BROADCAST_RELIABLE,
                host_var or 0,
                0,
                "broadcast_ready",
                port=0,
            )
            our_seq[(PROTO_BROADCAST_RELIABLE, 0)] = 4
            broadcast_ready_sent = True
            broadcast_ready_at = now
            record(event="broadcast_ready_sent")
        if broadcast_ready_sent and broadcast_ready_at is not None:
            post_ready_elapsed = now - broadcast_ready_at
            if post_ready_stage == 0 and post_ready_elapsed >= 10.0:
                send_pia(BROADCAST_READY_REFRESH, PROTO_BROADCAST_RELIABLE,
                         host_var or 0, 0, "broadcast_ready_refresh", port=0)
                our_seq[(PROTO_BROADCAST_RELIABLE, 0)] = 5
                post_ready_stage = 1
                record(event="broadcast_ready_refresh_sent")
            elif (post_ready_stage == 1 and host_start_seen_at is not None
                  and now - host_start_seen_at >= 9.0):
                send_pia(BROADCAST_START_ACK, PROTO_BROADCAST_RELIABLE,
                         host_var or 0, 0, "broadcast_start_ack", port=0)
                our_seq[(PROTO_BROADCAST_RELIABLE, 0)] = 6
                post_ready_stage = 2
                record(event="broadcast_start_ack_sent")
            elif (post_ready_stage == 2 and host_start_seen_at is not None
                  and now - host_start_seen_at >= 15.0):
                send_pia(BROADCAST_LOAD_ACK, PROTO_BROADCAST_RELIABLE,
                         host_var or 0, 0, "broadcast_load_ack", port=0)
                our_seq[(PROTO_BROADCAST_RELIABLE, 0)] = 7
                post_ready_stage = 3
                record(event="broadcast_load_ack_sent")
                battle_load_next_at = host_start_seen_at + 40.5
            elif (post_ready_stage == 3 and battle_load_next_at is not None
                  and battle_load_index < len(BROADCAST_BATTLE_LOAD)
                  and now >= battle_load_next_at):
                send_pia(
                    BROADCAST_BATTLE_LOAD[battle_load_index],
                    PROTO_BROADCAST_RELIABLE,
                    host_var or 0,
                    0,
                    f"broadcast_battle_load_{battle_load_index + 1}",
                    port=0,
                )
                battle_load_index += 1
                our_seq[(PROTO_BROADCAST_RELIABLE, 0)] = 7 + battle_load_index
                # The real guest emits the final four records as a short burst.
                battle_load_next_at = now + (0.4 if battle_load_index == 1 else 0.25)
                record(event="broadcast_battle_load_sent", index=battle_load_index)

    peer.disconnect()
    client.flush()
    print(f"DONE records={record_count}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
