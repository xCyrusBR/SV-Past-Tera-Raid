from __future__ import annotations

import argparse
import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path


STATIC_XORPAD = bytes.fromhex(
    "A092D10607DB32A1AE01F5C51E844FE353CA37F4A7B04DA018B7C297DA5F532B"
    "75FA4816F8D48A6F6105F4E2FD04B5A30FFC4492CB32E61BB9B12E01B0565336"
    "D2D1503DDE5B2E0E52FDDF2F7BCA6350A4675D2317C052E1A6307C2BB670365B"
    "2A276933F5637B363F269BA3ED7A5300A448B3509E14A052DE7E102B1B776E"
)
INTRO_HASH = bytes.fromhex(
    "9EC99CD70ED33C44FB9303DCEB39B42A1947E9634BA2334416BF82A2BA6355B6"
    "3D9DF24B5F7B6AB2621DC21B68E5C8B53A059000E8A8103DE2ECF00CB2ED4F6D"
)
OUTRO_HASH = bytes.fromhex(
    "D6C01C598BC8B8CB46E153FC828C757513E045DF32693C75F059F8D9A25FB217"
    "E08052DBEA8973997579AFCB2E8007E6F126E0030AE66FF641BF7E59C2AE55FD"
)

BOOL_TYPES = {1, 2, 3}
OBJECT = 4
ARRAY = 5
TYPE_SIZES = {3: 1, 8: 1, 9: 2, 10: 4, 11: 8, 12: 1, 13: 2, 14: 4, 15: 8, 16: 4, 17: 8}

RAID_BLOCKS = {
    "event_raid_identifier": 0x37B99B4D,
    "raid_enemy_array": 0x0520A1B0,
    "fixed_reward_item_array": 0x7D6C2B82,
    "lottery_reward_item_array": 0xA52B4811,
    "raid_priority_array": 0x095451E4,
}
KEY_TERA_RAID_PALDEA = 0xCAAC8800
RAID_LIST_HEADER_SIZE = 0x10
RAID_DETAIL_SIZE = 0x20
RAID_OFFSET_ENABLED = 0x00
RAID_OFFSET_CONTENT = 0x18
RAID_CONTENT_BLACK6 = 1
RAID_CONTENT_MIGHT7 = 3
VERSION_SUFFIXES = ("_3_0_0", "_2_0_0", "_1_3_0", "")


class SaveFormatError(ValueError):
    pass


class XorShift32:
    def __init__(self, seed: int):
        self.state = seed & 0xFFFFFFFF
        for _ in range(self.state.bit_count()):
            self.state = self._advance(self.state)
        self.counter = 0

    @staticmethod
    def _advance(value: int) -> int:
        value ^= (value << 2) & 0xFFFFFFFF
        value ^= value >> 15
        value ^= (value << 13) & 0xFFFFFFFF
        return value & 0xFFFFFFFF

    def next_byte(self) -> int:
        result = (self.state >> (self.counter * 8)) & 0xFF
        if self.counter == 3:
            self.state = self._advance(self.state)
            self.counter = 0
        else:
            self.counter += 1
        return result

    def next_u32(self) -> int:
        return sum(self.next_byte() << shift for shift in (0, 8, 16, 24))


@dataclass
class Block:
    key: int
    type_code: int
    data: bytes = b""
    subtype: int = 0

    def encode(self) -> bytes:
        rng = XorShift32(self.key)
        out = bytearray(struct.pack("<I", self.key))
        out.append(self.type_code ^ rng.next_byte())
        if self.type_code == OBJECT:
            out += struct.pack("<I", len(self.data) ^ rng.next_u32())
        elif self.type_code == ARRAY:
            element_size = TYPE_SIZES.get(self.subtype, 0)
            count = len(self.data) // element_size if element_size else 0
            out += struct.pack("<I", count ^ rng.next_u32())
            out.append(self.subtype ^ rng.next_byte())
        out += bytes(value ^ rng.next_byte() for value in self.data)
        return bytes(out)


def _xorpad(data: bytes) -> bytes:
    return bytes(value ^ STATIC_XORPAD[index % 0x7F] for index, value in enumerate(data))


def decode_save(raw: bytes) -> list[Block]:
    if len(raw) < 32:
        raise SaveFormatError("save menor que o hash SHA-256")
    payload = _xorpad(raw[:-32])
    blocks: list[Block] = []
    offset = 0
    while offset < len(payload):
        if offset + 5 > len(payload):
            raise SaveFormatError(f"bloco truncado em 0x{offset:X}")
        key = struct.unpack_from("<I", payload, offset)[0]
        offset += 4
        rng = XorShift32(key)
        type_code = payload[offset] ^ rng.next_byte()
        offset += 1
        subtype = 0
        if type_code in BOOL_TYPES:
            size = 0
        elif type_code == OBJECT:
            if offset + 4 > len(payload):
                raise SaveFormatError("comprimento de objeto truncado")
            size = struct.unpack_from("<I", payload, offset)[0] ^ rng.next_u32()
            offset += 4
        elif type_code == ARRAY:
            if offset + 5 > len(payload):
                raise SaveFormatError("cabeçalho de array truncado")
            count = struct.unpack_from("<I", payload, offset)[0] ^ rng.next_u32()
            offset += 4
            subtype = payload[offset] ^ rng.next_byte()
            offset += 1
            if subtype not in TYPE_SIZES:
                raise SaveFormatError(f"subtipo desconhecido {subtype} na chave 0x{key:08X}")
            size = count * TYPE_SIZES[subtype]
        else:
            if type_code not in TYPE_SIZES:
                raise SaveFormatError(f"tipo desconhecido {type_code} na chave 0x{key:08X}")
            size = TYPE_SIZES[type_code]
        if size < 0 or offset + size > len(payload):
            raise SaveFormatError(f"dados truncados na chave 0x{key:08X}")
        encrypted = payload[offset : offset + size]
        data = bytes(value ^ rng.next_byte() for value in encrypted)
        offset += size
        blocks.append(Block(key, type_code, data, subtype))
    return blocks


def encode_save(blocks: list[Block]) -> bytes:
    payload = _xorpad(b"".join(block.encode() for block in blocks))
    digest = hashlib.sha256(INTRO_HASH + payload + OUTRO_HASH).digest()
    return payload + digest


def verify_round_trip(raw: bytes) -> None:
    rebuilt = encode_save(decode_save(raw))
    if rebuilt != raw:
        raise SaveFormatError("o save falhou na verificação de ida e volta")


def _find_event_file(files_dir: Path, base_name: str) -> Path:
    for suffix in VERSION_SUFFIXES:
        candidate = files_dir / f"{base_name}{suffix}"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"arquivo do evento ausente: {base_name}")


def inject_event(source: Path, event_dir: Path, output: Path) -> dict[str, object]:
    source = source.resolve()
    output = output.resolve()
    if source == output:
        raise ValueError("a saída deve ser diferente do save de origem")
    if output.exists():
        raise FileExistsError(f"a saída já existe: {output}")

    raw = source.read_bytes()
    verify_round_trip(raw)
    blocks = decode_save(raw)
    by_key = {block.key: block for block in blocks}
    files_dir = event_dir / "Files"
    replaced: dict[str, int] = {}
    for base_name, key in RAID_BLOCKS.items():
        if key not in by_key:
            raise SaveFormatError(f"bloco 0x{key:08X} ausente no save")
        event_data = _find_event_file(files_dir, base_name).read_bytes()
        by_key[key].data = event_data
        replaced[base_name] = len(event_data)

    patched = encode_save(blocks)
    verify_round_trip(patched)
    if len(patched) != len(raw):
        raise SaveFormatError(f"tamanho mudou de {len(raw)} para {len(patched)} bytes")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(patched)
    return {
        "identifier": (event_dir / "Identifier.txt").read_text(encoding="utf-8").strip(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "output_sha256": hashlib.sha256(patched).hexdigest(),
        "size": len(patched),
        "blocks": replaced,
    }


def materialize_might7(source: Path, output: Path) -> dict[str, object]:
    """Convert the existing active black crystal into a 7-star event crystal."""
    source = source.resolve()
    output = output.resolve()
    if source == output:
        raise ValueError("a saída deve ser diferente do save de origem")
    if output.exists():
        raise FileExistsError(f"a saída já existe: {output}")

    raw = source.read_bytes()
    verify_round_trip(raw)
    blocks = decode_save(raw)
    block = next((item for item in blocks if item.key == KEY_TERA_RAID_PALDEA), None)
    if block is None:
        raise SaveFormatError("bloco de raids de Paldea ausente")

    data = bytearray(block.data)
    count = (len(data) - RAID_LIST_HEADER_SIZE) // RAID_DETAIL_SIZE
    selected = None
    for index in range(count):
        offset = RAID_LIST_HEADER_SIZE + index * RAID_DETAIL_SIZE
        enabled = struct.unpack_from("<I", data, offset + RAID_OFFSET_ENABLED)[0]
        content = struct.unpack_from("<I", data, offset + RAID_OFFSET_CONTENT)[0]
        if enabled and content == RAID_CONTENT_BLACK6:
            selected = index
            struct.pack_into("<I", data, offset + RAID_OFFSET_CONTENT, RAID_CONTENT_MIGHT7)
            break
    if selected is None:
        raise SaveFormatError("nenhum cristal preto ativo foi encontrado")

    block.data = bytes(data)
    patched = encode_save(blocks)
    verify_round_trip(patched)
    if len(patched) != len(raw):
        raise SaveFormatError("o tamanho do save mudou")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(patched)
    return {
        "raid_index": selected,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "output_sha256": hashlib.sha256(patched).hexdigest(),
        "size": len(patched),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Injeta um evento de Tera Raid em uma cópia do save de Scarlet/Violet.")
    parser.add_argument("source", type=Path)
    parser.add_argument("event_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = inject_event(args.source, args.event_dir, args.output)
    print(f"Evento: {result['identifier']}")
    print(f"Tamanho: {result['size']} bytes")
    print(f"SHA-256 origem: {result['source_sha256']}")
    print(f"SHA-256 saída: {result['output_sha256']}")
    for name, size in result["blocks"].items():
        print(f"Bloco {name}: {size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
