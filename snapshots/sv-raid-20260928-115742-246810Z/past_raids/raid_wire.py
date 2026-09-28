from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct


NETWORK_INFO_SIZE = 0x480
OFF_SCENE_ID = 0x0A
OFF_SESSION_ID = 0x10
OFF_HOST_MAC = 0x20
OFF_CHANNEL = 0x48
OFF_NODE_COUNT_MAX = 0x66
OFF_NODE_COUNT = 0x67
OFF_NODES = 0x68
OFF_NODE_LOCAL_COMM_VERSION = 0x2E
OFF_ADVERTISE_SIZE = 0x26A
OFF_ADVERTISE_DATA = 0x26C

PIA_HEADER_SIZE = 0x5C
GAME_DATA_SIZE = 40
RAID_SCENE_ID = 7
RAID_MAX_PARTICIPANTS = 4
RAID_GAME_MARKER = bytes.fromhex("aadb8104")
RAID_PASSWORD_MASK = bytes.fromhex("e5ab19ed")
RAID_PASSWORD_SUFFIX = bytes.fromhex("742b6d40885998bf968aa166")


@dataclass(frozen=True)
class RaidNetworkProfile:
    scene_id: int
    session_id: bytes
    host_mac: bytes
    channel: int
    node_count_max: int
    node_count: int
    local_comm_version: int
    advertise_data: bytes

    @property
    def link_code(self) -> str:
        raw = self.advertise_data[PIA_HEADER_SIZE : PIA_HEADER_SIZE + 4]
        return raw.decode("ascii")


def parse_network_info(data: bytes) -> RaidNetworkProfile:
    raw = bytes(data)
    if len(raw) != NETWORK_INFO_SIZE:
        raise ValueError(f"NetworkInfo must be {NETWORK_INFO_SIZE} bytes, got {len(raw)}")
    advertise_size = struct.unpack_from("<H", raw, OFF_ADVERTISE_SIZE)[0]
    advertise = raw[OFF_ADVERTISE_DATA : OFF_ADVERTISE_DATA + advertise_size]
    if len(advertise) != advertise_size:
        raise ValueError("NetworkInfo advertises data beyond the end of the structure")
    if len(advertise) != PIA_HEADER_SIZE + GAME_DATA_SIZE:
        raise ValueError(f"SV advertise data must be 132 bytes, got {len(advertise)}")
    return RaidNetworkProfile(
        scene_id=struct.unpack_from("<H", raw, OFF_SCENE_ID)[0],
        session_id=raw[OFF_SESSION_ID : OFF_SESSION_ID + 16],
        host_mac=raw[OFF_HOST_MAC : OFF_HOST_MAC + 6],
        channel=struct.unpack_from("<h", raw, OFF_CHANNEL)[0],
        node_count_max=raw[OFF_NODE_COUNT_MAX],
        node_count=raw[OFF_NODE_COUNT],
        local_comm_version=struct.unpack_from(
            "<H", raw, OFF_NODES + OFF_NODE_LOCAL_COMM_VERSION
        )[0],
        advertise_data=advertise,
    )


def load_network_info(path: str | Path) -> RaidNetworkProfile:
    return parse_network_info(Path(path).read_bytes())


def raid_game_data(link_code: str, marker: bytes = RAID_GAME_MARKER) -> bytes:
    if len(link_code) != 4 or not link_code.isdigit():
        raise ValueError("link code must contain exactly four decimal digits")
    marker = bytes(marker)
    if len(marker) != 4:
        raise ValueError("raid marker must be four bytes")
    game = bytearray(GAME_DATA_SIZE)
    game[0:4] = link_code.encode("ascii")
    game[33:37] = marker
    return bytes(game)


def raid_user_password(link_code: str) -> bytes:
    """Return the 16-byte Pia password selected by Scarlet/Violet for a raid code."""
    if len(link_code) != 4 or not link_code.isdigit():
        raise ValueError("link code must contain exactly four decimal digits")
    prefix = bytes(a ^ b for a, b in zip(link_code.encode("ascii"), RAID_PASSWORD_MASK))
    return prefix + RAID_PASSWORD_SUFFIX


def build_raid_advertise_data(build_pia_header, link_code: str, *, password: bytes | None = None,
                              num_players: int = 1) -> bytes:
    if not 1 <= num_players <= RAID_MAX_PARTICIPANTS:
        raise ValueError("raid player count must be between 1 and 4")
    header = build_pia_header(
        sys_comm_ver=0x15,
        app_comm_ver=0x15,
        user_password=raid_user_password(link_code) if password is None else bytes(password),
        player_limit_enabled=True,
        num_players=num_players,
        nickname=" ",
        name_encoding=1,
    )
    if len(header) != PIA_HEADER_SIZE:
        raise ValueError(f"Pia header must be {PIA_HEADER_SIZE} bytes, got {len(header)}")
    return header + raid_game_data(link_code)
