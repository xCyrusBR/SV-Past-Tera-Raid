from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "pokeldn-research"))
sys.path.insert(0, str(ROOT / "tools"))

from pokeldn.sv import pokemon, raid_start, streams
import sv_raid_host

OLD = ROOT / "lab/eden-two-client-raid-decoded-pia0.jsonl"
NEW = ROOT / "lab/eden-live-proxy-20260930-005118-decoded.jsonl"


def captured_start(path, sequences):
    pieces = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("source_ip") != "192.168.1.1":
            continue
        for message in row.get("messages", ()):
            rel = message.get("reliable") or {}
            seq = rel.get("sequence_id")
            if (message.get("protocol"), message.get("port")) != (0x80, 0):
                continue
            if seq not in sequences or rel.get("is_ack"):
                continue
            data = bytes.fromhex(rel["payload"])
            if "ZLIB" in rel.get("flag_names", ()):
                data = streams.decompress(data)
            pieces.setdefault(seq, data)
    return b"".join(pieces[s] for s in sequences)


@unittest.skipUnless(OLD.is_file() and NEW.is_file(), "private Eden controls unavailable")
class BattleRosterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = captured_start(OLD, (52, 53))
        cls.new = captured_start(NEW, (58, 59))

    def test_both_working_captures_use_same_decoded_layout(self):
        for message, guest in ((self.old, 911), (self.new, 992)):
            _, body = raid_start.decode(message)
            self.assertEqual(2720, len(body))
            species = [pokemon.read(pokemon.load(body[i:i + 344]))["species"]
                       for i in (0, 344, 688, 1032, 1376)]
            self.assertEqual([911, guest, 0, 0, 150], species)

    def test_old_literal_rewrite_duplicates_guest_into_both_human_seats(self):
        _, distinct = raid_start.decode(self.new)
        guest = distinct[344:688]
        wrong = self.old[:21] + guest + self.old[365:]
        _, decoded = raid_start.decode(wrong)
        self.assertEqual(guest, decoded[:344])
        self.assertEqual(guest, decoded[344:688])

    def test_correct_rewrite_preserves_boss_npcs_tail_and_separates_players(self):
        host = pokemon.encrypt(pokemon.load(sv_raid_host.DEFAULT_MEW.read_bytes()))
        _, distinct = raid_start.decode(self.new)
        guest = distinct[344:688]
        header, original = raid_start.decode(self.old)
        fixed = raid_start.patch_roster(self.old, host, guest)
        result_header, decoded = raid_start.decode(fixed)
        self.assertEqual(header, result_header)
        self.assertEqual(host, decoded[:344])
        self.assertEqual(guest, decoded[344:688])
        self.assertEqual(original[688:], decoded[688:])
        fragments = raid_start.split_two(fixed)
        self.assertTrue(all(0 < len(p) <= 1395 for p in fragments))
        self.assertEqual(fixed, b"".join(fragments))

    def test_runtime_template_joins_reference_and_keeps_retry_out_of_body(self):
        spec = importlib.util.spec_from_file_location("raid_runtime", sv_raid_host.SV_HOST)
        runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runtime)
        start, end, message = runtime.raid_start_template(sv_raid_host.raid_reference_sends())
        self.assertEqual((52, 53), (start, end))
        self.assertEqual(self.old, message)

    def test_invalid_selected_record_is_rejected(self):
        with self.assertRaises(ValueError):
            raid_start.patch_roster(self.old, b"short", bytes(344))


if __name__ == "__main__":
    unittest.main()
