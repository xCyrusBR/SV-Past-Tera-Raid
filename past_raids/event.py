"""Read a Project Pokémon Scarlet/Violet Poké Portal event package."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class RaidBoss:
    event_no: int
    species: int
    difficulty: int
    tera_type: int
    level: int
    moves: tuple[int, int, int, int]
    hp_multiplier: int
    capture_rate_mode: int


@dataclass(frozen=True)
class EventPackage:
    root: Path
    identifier: int
    bosses: tuple[RaidBoss, ...]
    files: dict[str, str]

    @classmethod
    def load(cls, root: str | Path) -> "EventPackage":
        root = Path(root)
        identifier_path = root / "Identifier.txt"
        raid_json_path = root / "Json" / "raid_enemy_array_1_3_0.json"
        if not identifier_path.is_file():
            raise FileNotFoundError(identifier_path)
        if not raid_json_path.is_file():
            raise FileNotFoundError(raid_json_path)

        identifier = int(identifier_path.read_text(encoding="utf-8-sig").strip())
        document = json.loads(raid_json_path.read_text(encoding="utf-8-sig"))
        bosses = []
        for row in document.get("Table", []):
            info = row["Info"]
            pokemon = info["BossPokePara"]
            desc = info["BossDesc"]
            bosses.append(
                RaidBoss(
                    event_no=int(info["No"]),
                    species=int(pokemon["DevId"]),
                    difficulty=int(info["Difficulty"]),
                    tera_type=int(pokemon["GemType"]),
                    level=int(info["CaptureLv"]),
                    moves=tuple(int(pokemon[f"Waza{i}"]["WazaId"]) for i in range(1, 5)),
                    hp_multiplier=int(desc["HpCoef"]),
                    capture_rate_mode=int(info["CaptureRate"]),
                )
            )

        hashes = {}
        files_dir = root / "Files"
        for path in sorted(files_dir.iterdir()):
            if path.is_file():
                hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return cls(root=root, identifier=identifier, bosses=tuple(bosses), files=hashes)

    def boss(self, *, species: int, difficulty: int | None = None) -> RaidBoss:
        matches = [b for b in self.bosses if b.species == species]
        if difficulty is not None:
            matches = [b for b in matches if b.difficulty == difficulty]
        if len(matches) != 1:
            raise ValueError(f"expected one boss, found {len(matches)}")
        return matches[0]

