import importlib.util
import json
import socket
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "pokeldn-research"))
from pokeldn import sv
from pokeldn.ldn import pia6

spec = importlib.util.spec_from_file_location("net_body_host", ROOT.parent / "pokeldn-research/bin/sv_host.py")
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class NetPropertyBodyTests(unittest.TestCase):
    def test_opt_in_changes_only_byte_27(self):
        keys = sv.session_keys(bytes(16))
        bodies = []
        for enabled in (False, True):
            packet = runtime.build_net_property(keys, "192.168.1.1", 3, bytes(8),
                                                match_eden_body=enabled)
            _, plain, _ = pia6.parse_packet(keys.session_key, socket.inet_aton("192.168.1.1"),
                                            keys.network_id, packet)
            bodies.append(pia6.parse_messages(plain)[0].payload)
        self.assertEqual([27], [i for i, (a, b) in enumerate(zip(*bodies)) if a != b])
        self.assertEqual((4, 7), (bodies[0][27], bodies[1][27]))

    def test_both_working_private_controls_use_7(self):
        for name in ("eden-two-client-raid-decoded-pia0.jsonl",
                     "eden-live-proxy-20260930-005118-decoded.jsonl"):
            path = ROOT / "lab" / name
            if not path.is_file():
                self.skipTest("private Eden reference missing")
            found = False
            with path.open(encoding="utf-8") as capture:
                for line in capture:
                    row = json.loads(line)
                    if row.get("source_ip") != "192.168.1.1":
                        continue
                    for message in row.get("messages", ()):
                        payload = bytes.fromhex(message["payload"])
                        if message.get("protocol") == 0x2C and payload[:2] == b"\x01\x50":
                            self.assertEqual(170, len(payload))
                            self.assertEqual(7, payload[27])
                            found = True
                            break
                    if found:
                        break
            self.assertTrue(found, name)


if __name__ == "__main__":
    unittest.main()
