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
    @unittest.skipUnless(raid_host.DEFAULT_REFERENCE_CAPTURE.is_file(),
                         "private decoded Eden reference capture is not installed")
    def test_replay_can_stop_before_first_unacknowledged_live_sequence(self):
        self.assertEqual(219, raid_host.parser().parse_args([]).replay_last_seq)
        self.assertEqual(65, raid_host.parser().parse_args(
            ["--replay-last-seq", "65"]).replay_last_seq)
        sends = raid_host.raid_reference_sends(last=65)
        sequences = {int(part[4:]) for spec in sends for part in spec.split(":")
                     if part.startswith("seq=")}
        self.assertEqual(set(range(44, 66)), sequences)

    def test_lobby_omits_only_late_session_update(self):
        self.assertEqual(["--no-late-session-update"],
                         raid_host.session_update_mode_args(True))
        self.assertEqual(["--raid-ready-gate-after", "42.7",
                          "--raid-ready-lead", "4.6"],
                         raid_host.session_update_mode_args(False))

    def test_start_on_ready_is_opt_in_and_lobby_mode_stays_unchanged(self):
        self.assertFalse(raid_host.parser().parse_args([]).start_on_ready)
        self.assertEqual(["--raid-ready-gate-after", "42.7", "--raid-ready-lead", "0.1",
                          "--raid-start-on-ready"], raid_host.session_update_mode_args(False, True))
        self.assertEqual(["--no-late-session-update"], raid_host.session_update_mode_args(True, True))

    def test_guest_selection_gated_opening_is_opt_in(self):
        self.assertFalse(raid_host.parser().parse_args([]).guest_selection_gated_opening)
        self.assertTrue(raid_host.parser().parse_args(
            ["--guest-selection-gated-opening"]).guest_selection_gated_opening)

    def test_identity_record_gate_is_opt_in(self):
        self.assertFalse(raid_host.parser().parse_args([]).gate_records_after_guest)
        self.assertTrue(raid_host.parser().parse_args(
            ["--gate-records-after-guest"]).gate_records_after_guest)

    def test_identity_record_pacing_is_opt_in(self):
        self.assertFalse(raid_host.parser().parse_args([]).pace_identity_records)
        self.assertTrue(raid_host.parser().parse_args(
            ["--pace-identity-records"]).pace_identity_records)

    def test_eden_opening_order_diagnostic_delays_only_initial_countdown(self):
        self.assertFalse(raid_host.parser().parse_args([]).match_eden_opening_order)
        self.assertTrue(raid_host.parser().parse_args(
            ["--match-eden-opening-order"]).match_eden_opening_order)
        baseline = raid_host.opening_sends()
        diagnostic = raid_host.opening_sends(True)
        self.assertEqual(len(baseline), len(diagnostic))
        self.assertEqual(baseline[:4], diagnostic[:4])
        self.assertTrue(baseline[4].startswith("3.20:0x80:0:803330"))
        self.assertTrue(diagnostic[4].startswith("3.36:0x80:0:803330"))
        self.assertEqual(baseline[5:], diagnostic[5:])

    def test_eden_opening_lowest_pending_changes_only_two_headers(self):
        self.assertFalse(raid_host.parser().parse_args([]).match_eden_opening_lowest_pending)
        self.assertTrue(raid_host.parser().parse_args(
            ["--match-eden-opening-lowest-pending"]).match_eden_opening_lowest_pending)
        baseline = raid_host.opening_sends(True)
        diagnostic = raid_host.opening_sends(True, True)
        self.assertEqual(len(baseline), len(diagnostic))
        changed = [index for index, (left, right) in enumerate(zip(baseline, diagnostic))
                   if left != right]
        self.assertEqual([6, 7], changed)
        self.assertEqual([baseline[index] + ":low=1" for index in changed],
                         [diagnostic[index] for index in changed])

    @unittest.skipUnless(raid_host.SV_HOST.is_file(),
                         "pokeldn host implementation is not installed")
    def test_guest_record_ack_does_not_skip_lost_records(self):
        spec = importlib.util.spec_from_file_location("radio_sv_host", raid_host.SV_HOST)
        radio_host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(radio_host)
        received = set(range(1, 5)) | set(range(7, 19)) | set(range(36, 47))
        self.assertEqual(18, radio_host.contiguous_record_high(
            received, skip_record_gaps=True))
        self.assertEqual(19, radio_host.reliable5.parse_ack_payload(
            radio_host.build_bulk_ack({1: 18}, 1)[13:])["entries"][1]["ack_id"])
        self.assertEqual(2, radio_host.contiguous_record_high(
            received - {3, 4}, skip_record_gaps=True))
        self.assertEqual(46, radio_host.contiguous_record_high(
            set(range(1, 5)) | set(range(7, 47)), skip_record_gaps=True))
        self.assertEqual(4, radio_host.contiguous_record_high({1, 2, 3, 4, 7}))

    @unittest.skipUnless(raid_host.SV_HOST.is_file(),
                         "pokeldn host implementation is not installed")
    def test_pia_packet_ids_advance_for_every_host_packet(self):
        spec = importlib.util.spec_from_file_location("radio_sv_host_ids", raid_host.SV_HOST)
        radio_host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(radio_host)
        ids = radio_host.PiaPacketIdAllocator()
        self.assertEqual([0, 1, 2, 3], [ids.next() for _ in range(4)])
        ids.value = 0xFFFF
        self.assertEqual([0xFFFF, 0], [ids.next() for _ in range(2)])

    @unittest.skipUnless(raid_host.SV_HOST.is_file(),
                         "pokeldn host implementation is not installed")
    def test_opening_gate_keeps_only_lobby_port_zero_and_relative_timing(self):
        spec = importlib.util.spec_from_file_location("radio_sv_host", raid_host.SV_HOST)
        radio_host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(radio_host)
        gate = radio_host.raid_opening_delay
        self.assertIsNone(gate("0.14:0x7c:2:00", 3.2))
        self.assertIsNone(gate("3.20:0x81:0:00", 3.2))
        self.assertIsNone(gate("3.19:0x80:0:00", 3.2))
        self.assertAlmostEqual(0.0, gate("3.20:0x80:0:00", 3.2))
        self.assertAlmostEqual(1.0, gate("4.20:0x80:0:00", 3.2))

    def test_session_sequence_diagnostic_changes_only_generation(self):
        self.assertEqual(
            ["--join-seq", "1", "--update-first-seq", "1", "--update-seq", "2"],
            raid_host.session_sequence_args(1),
        )
        self.assertEqual(
            ["--join-seq", "0", "--update-first-seq", "0", "--update-seq", "1"],
            raid_host.session_sequence_args(0),
        )
        with self.assertRaises(ValueError):
            raid_host.session_sequence_args(2)

    def test_session_ack_diagnostic_is_opt_in(self):
        self.assertFalse(raid_host.parser().parse_args([]).omit_session_ack)
        self.assertTrue(raid_host.parser().parse_args(["--omit-session-ack"]).omit_session_ack)

    def test_session_message_flags_default_and_reference_diagnostic(self):
        self.assertEqual(1, raid_host.parser().parse_args([]).session_message_flags)
        self.assertEqual(0, raid_host.parser().parse_args(
            ["--session-message-flags", "0"]).session_message_flags)

    @unittest.skipUnless(raid_host.SV_HOST.is_file(),
                         "pokeldn host implementation is not installed")
    def test_type6_pair_mapping_repeats_current_host_id_inside_zlib(self):
        from pokeldn.ldn import reliable5
        from pokeldn.sv import streams

        spec = importlib.util.spec_from_file_location("radio_sv_host", raid_host.SV_HOST)
        radio_host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(radio_host)
        send = next(spec for spec in raid_host.RAID_OPENING_SENDS
                    if ":0x7c:2:" in spec)
        self.assertTrue(send.startswith("0.14:0x7c:2:"))
        payload = bytes.fromhex(send.split(":")[3])
        original = streams.decompress(payload)
        self.assertEqual(6, original[0])
        positions = [i for i, byte in enumerate(original) if byte == 0x83]
        self.assertEqual(2, len(positions))
        self.assertEqual(original[positions[0] + 1:positions[0] + 9],
                         original[positions[1] + 1:positions[1] + 9])
        host_id = bytes.fromhex("0102030405060708")
        patched = radio_host.patch_port2_pair_payload(
            payload, reliable5.FLAG_ZLIB, host_id)
        result = streams.decompress(patched)
        self.assertEqual(len(original), len(result))
        self.assertNotEqual(original, result)
        self.assertEqual(2, result.count(bytes.fromhex("0807060504030201")))
        self.assertEqual(payload, radio_host.patch_port2_pair_payload(
            payload, 0, host_id))

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
        sequences = {int(item.rsplit(":seq=", 1)[1].split(":", 1)[0]) for item in sends}
        self.assertEqual(set(range(44, 220)), sequences)
        self.assertEqual(179, len(sends))
        self.assertTrue(any(":start:seq=" in item for item in sends))
        self.assertTrue(any(":z:middle:seq=" in item for item in sends))
        self.assertTrue(any(":seq=219:low=219" in item for item in sends))
        self.assertEqual(2, sum(":seq=53:" in item for item in sends))
        self.assertEqual(2, sum(":seq=85:" in item for item in sends))
        self.assertEqual(2, sum(":seq=87:" in item for item in sends))
        self.assertTrue(any(":seq=70:low=69" in item for item in sends))
        self.assertTrue(any(":start:seq=52:" in item for item in sends))
        self.assertTrue(any(":end:seq=53:" in item for item in sends))

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

    @unittest.skipUnless(raid_host.DEFAULT_RECORD_SET.is_dir(),
                         "private extracted host record set is not installed")
    def test_pr_identity_preserves_offline_account_field(self):
        from pokeldn.sv import streams

        spec = importlib.util.spec_from_file_location("radio_sv_host", raid_host.SV_HOST)
        radio_host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(radio_host)
        captured = (raid_host.DEFAULT_RECORD_SET / "001.bin").read_bytes()
        original = streams.decompress(captured)
        self.assertEqual(bytes(22), original[45:67])
        player_id, player_name = raid_host.host_identity("PR", 4294423561)
        patched = radio_host.patch_record_identity(
            captured, bytes.fromhex(player_id), player_name, "")
        result = streams.decompress(patched)
        self.assertEqual(b"\x09\xb4\xf7\xff", result[11:15])
        self.assertEqual("PR", result[19:45].decode("utf-16le").split("\x00")[0])
        self.assertEqual(original[45:67], result[45:67])


if __name__ == "__main__":
    unittest.main()
