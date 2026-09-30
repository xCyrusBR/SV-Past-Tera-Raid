import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT.parent / "pokeldn-research"), str(ROOT / "tests")]
from pokeldn.sv import port2, streams
from test_session_player_identity import identities


class RaidAdmissionTests(unittest.TestCase):
    def test_host_and_guest_second_fields_differ(self):
        host, guest = port2.build_raid_admissions(12, 34)
        self.assertEqual(port2.build_accept(12, slot=0, code=0), host)
        self.assertEqual(port2.build_accept(34, slot=0, code=1), guest)
        self.assertNotEqual(port2.build_accept(34, slot=0, code=0), guest)

    def test_matches_both_private_working_controls(self):
        for name in ("eden-two-client-raid-decoded-pia0.jsonl",
                     "eden-live-proxy-20260930-005118-decoded.jsonl"):
            path = ROOT / "lab" / name
            if not path.exists():
                self.skipTest("private reference missing")
            _, updates = identities(path)
            stations = updates[0]["stations"]
            expected = port2.build_raid_admissions(*(
                port2.station_id(s["constant_id"]) for s in stations))
            found = {}
            with path.open(encoding="utf-8") as capture:
                for line in capture:
                    row = json.loads(line)
                    if row.get("source_ip") != "192.168.1.1":
                        continue
                    for message in row.get("messages", ()):
                        rel = message.get("reliable") or {}
                        if ((message.get("protocol"), message.get("port")) != (0x80, 2)
                                or rel.get("is_ack") or not rel.get("payload")):
                            continue
                        data = bytes.fromhex(rel["payload"])
                        if rel["flags"] & 16:
                            data = streams.decompress(data)
                        if data[0] == 9:
                            found.setdefault(rel["sequence_id"], data)
            self.assertEqual(expected, (found[1], found[2]), name)


if __name__ == "__main__":
    unittest.main()
