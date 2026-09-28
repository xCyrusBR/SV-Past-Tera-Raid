from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "sv_raid_host.py"
SPEC = importlib.util.spec_from_file_location("sv_raid_host", MODULE_PATH)
raid_host = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = raid_host
SPEC.loader.exec_module(raid_host)


class RaidReferenceReplayTests(unittest.TestCase):
    def test_host_identity_is_independent_of_selected_pokemon_ot(self):
        player_id, name = raid_host.host_identity("PR", 4294423561)
        self.assertEqual("09b4f7ff" + "00" * 12, player_id)
        self.assertEqual("PR", name)

    def test_fragment_suffix_preserves_all_boundary_shapes(self):
        self.assertEqual(raid_host._fragment_suffix(["ZLIB", "START", "END"]), ":z")
        self.assertEqual(raid_host._fragment_suffix(["START"]), ":start")
        self.assertEqual(raid_host._fragment_suffix(["ZLIB", "END"]), ":z:end")
        self.assertEqual(raid_host._fragment_suffix(["ZLIB"]), ":z:middle")

    @unittest.skipUnless(raid_host.DEFAULT_REFERENCE_CAPTURE.is_file(),
                         "private decoded Eden reference capture is not installed")
    def test_complete_reference_keeps_fragments_retransmissions_and_tail(self):
        sends = raid_host.raid_reference_sends()
        self.assertTrue(any(":start:seq=" in item for item in sends))
        self.assertTrue(any(":z:middle:seq=" in item for item in sends))
        self.assertTrue(any(":seq=219:low=219" in item for item in sends))
        self.assertEqual(2, sum(":seq=53:" in item for item in sends))
        self.assertEqual(2, sum(":seq=85:" in item for item in sends))
        self.assertEqual(2, sum(":seq=87:" in item for item in sends))
        self.assertTrue(any(":seq=70:low=69" in item for item in sends))

    def test_skip_spec_is_not_treated_as_hex_payload(self):
        spec = "63.000:skip:0x80:0"
        self.assertEqual(
            raid_host.patch_host_trainer_announce(spec, object(), Path("unused")), spec
        )

    @unittest.skipUnless(raid_host.DEFAULT_REFERENCE_CAPTURE.is_file(),
                         "private decoded Eden reference capture is not installed")
    def test_reference_battle_start_has_local_pokemon_and_mewtwo(self):
        from pokeldn.sv import pokemon

        fragments = {}
        for line in raid_host.DEFAULT_REFERENCE_CAPTURE.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("event") != "proxy" or row.get("source_ip") != "192.168.1.1":
                continue
            for message in row.get("messages", ()):
                reliable = message.get("reliable") or {}
                sequence = reliable.get("sequence_id")
                if (message.get("protocol"), message.get("port")) != (0x80, 0):
                    continue
                if sequence in (52, 53) and not reliable.get("is_ack"):
                    fragments.setdefault(sequence, bytes.fromhex(reliable["payload"]))
        battle = fragments[52] + fragments[53]
        self.assertEqual(1400, len(battle))
        self.assertTrue(battle.startswith(b"\x80\x33\x2f"))
        local = pokemon.read(pokemon.load(battle[21:365]))
        boss = pokemon.read(pokemon.load(battle[724:1068]))
        self.assertEqual(150, boss["species"])
        self.assertNotEqual(150, local["species"])


if __name__ == "__main__":
    unittest.main()
