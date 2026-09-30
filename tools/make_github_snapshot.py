#!/usr/bin/env python3
"""Create a new, strictly allowlisted GitHub collaboration snapshot.

The private project contains keys, saves, ROM-related source material, PK9s and raw
captures. Never upload that directory wholesale. This script copies only reviewed source
and documentation into a timestamped folder; it never deletes an earlier snapshot.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil


ROOT = Path(__file__).resolve().parents[1]
POKELDN = ROOT.parent / "pokeldn-research"
DESTINATION = ROOT / "github-snapshots"

ALLOWLIST = {
    "README.md": ROOT / "docs" / "GITHUB-README.md",
    "docs/PROGRESS.md": ROOT / "docs" / "PROGRESS.md",
    "docs/EDEN-REFERENCE-REPLAY.md": ROOT / "docs" / "EDEN-REFERENCE-REPLAY.md",
    "docs/ROSTER-AUDIT.md": ROOT / "docs" / "ROSTER-AUDIT.md",
    "docs/TWO-EDEN-DISTINCT-POKEMON.md": ROOT / "docs" / "TWO-EDEN-DISTINCT-POKEMON.md",
    "docs/RELATED-WORK.md": ROOT / "docs" / "RELATED-WORK.md",
    "tools/sv_raid_host.py": ROOT / "tools" / "sv_raid_host.py",
    "tools/analyze_eden_capture.py": ROOT / "tools" / "analyze_eden_capture.py",
    "tools/compare_eden_guest_records.py": ROOT / "tools" / "compare_eden_guest_records.py",
    "tools/compare_battle_gap.py": ROOT / "tools" / "compare_battle_gap.py",
    "tests/test_sv_raid_host.py": ROOT / "tests" / "test_sv_raid_host.py",
    "past_raids/__init__.py": ROOT / "past_raids" / "__init__.py",
    "past_raids/raid_wire.py": ROOT / "past_raids" / "raid_wire.py",
    "pokeldn_overlay/bin/sv_host.py": POKELDN / "bin" / "sv_host.py",
    "pokeldn_overlay/pokeldn/sv/streams.py": POKELDN / "pokeldn" / "sv" / "streams.py",
    "pokeldn_overlay/pokeldn/sv/port2.py": POKELDN / "pokeldn" / "sv" / "port2.py",
    "pokeldn_overlay/pokeldn/ldn/pia5.py": POKELDN / "pokeldn" / "ldn" / "pia5.py",
    "pokeldn_overlay/pokeldn/ldn/pia6.py": POKELDN / "pokeldn" / "ldn" / "pia6.py",
    "LICENSE-POKELDN": POKELDN / "LICENSE",
}

FORBIDDEN_SUFFIXES = {".keys", ".pk9", ".jsonl", ".trace", ".nsp", ".xci", ".7z"}


def main() -> int:
    missing = [str(path) for path in ALLOWLIST.values() if not path.is_file()]
    if missing:
        raise SystemExit("Missing required source files: " + ", ".join(missing))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ")
    output = DESTINATION / f"sv-raid-{stamp}"
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"created_utc": stamp, "files": {}}
    for name, source in ALLOWLIST.items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise RuntimeError(f"Unsafe snapshot path: {name}")
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if name == "tools/sv_raid_host.py":
            # The private source has one captured encrypted PK9 as an inline opening
            # template. Runtime replaces it with the user's --mew; a zero placeholder
            # is therefore equivalent and safe to publish.
            original = source.read_text(encoding="utf-8")
            sanitized, count = re.subn(
                r'^    "3\.32:0x80:0:80332e[^\n]*,$',
                '    "3.32:0x80:0:80332e01aa00000000005801000000000000" + "00" * 344,',
                original,
                flags=re.MULTILINE,
            )
            if count != 1:
                raise RuntimeError("Cannot locate exactly one private host PK9 template")
            target.write_text(sanitized, encoding="utf-8")
        elif name == "past_raids/__init__.py":
            # The private package imports unrelated save/event modules that are not part
            # of this narrowly scoped collaboration snapshot.
            target.write_text('"""Public raid-wire research helpers."""\n', encoding="utf-8")
        else:
            shutil.copy2(source, target)
        manifest["files"][name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(output)
    print(f"{len(ALLOWLIST)} allowlisted files; no private captures, keys or game assets copied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
