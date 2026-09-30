import json
import socket
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "pokeldn-research"))
from pokeldn import sv
from pokeldn.ldn import pia_connect, pia6


def identities(path, radio=False):
    join = None
    updates = []
    with path.open(encoding="utf-8") as capture:
        if radio:
            host = json.loads(next(capture))
            keys = sv.session_keys(bytes.fromhex(host["ssid"]))
        for line in capture:
            row = json.loads(line)
            if not radio:
                messages = row.get("messages", ())
            elif row.get("rec") == "msg":
                messages = [row]
            elif row.get("rec") == "out" and row.get("kind") == "session update":
                _, plain, _ = pia6.parse_packet(
                    keys.session_key, socket.inet_aton(host["our_ip"]), keys.network_id,
                    bytes.fromhex(row["hex"]))
                messages = [{"protocol": m.protocol, "payload": m.payload.hex()}
                            for m in pia6.parse_messages(plain)]
            else:
                continue
            for message in messages:
                if message.get("protocol") != 0x98:
                    continue
                payload = bytes.fromhex(message["payload"])
                if payload and payload[0] == 0 and join is None:
                    join = pia_connect.parse_session_join_players_v11(payload)
                elif payload and payload[0] == 5:
                    updates.append(pia_connect.parse_session_update_v11(payload, route_bytes=0))
    return join, updates


class SessionPlayerIdentityTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / "lab/eden-live-proxy-20260930-005118-decoded.jsonl").is_file(),
                         "private distinct-save Eden control missing")
    def test_working_control_preserves_guest_and_has_distinct_host_player(self):
        join, updates = identities(ROOT / "lab/eden-live-proxy-20260930-005118-decoded.jsonl")
        self.assertEqual(1, join["num_players"])
        self.assertTrue(updates)
        player = join["players"][0]
        for update in updates:
            self.assertEqual(player, update["stations"][1]["players"][0])
            self.assertNotEqual(player["player_id"],
                                update["stations"][0]["players"][0]["player_id"])

    @unittest.skipUnless((ROOT / "lab/sv-raid-lz4-roster-8264.jsonl").is_file(),
                         "private physical failure control missing")
    def test_synthetic_failure_replaced_guest_player_with_host_reference_id(self):
        join, updates = identities(ROOT / "lab/sv-raid-lz4-roster-8264.jsonl", radio=True)
        self.assertTrue(updates)
        for update in updates:
            host, guest = update["stations"]
            self.assertNotEqual(join["players"][0]["player_id"],
                                guest["players"][0]["player_id"])
            self.assertEqual(host["players"][0]["player_id"],
                             guest["players"][0]["player_id"])

    def test_missing_player_trailer_is_rejected(self):
        with self.assertRaises(ValueError):
            pia_connect.parse_session_join_players_v11(b"\0")


if __name__ == "__main__":
    unittest.main()
