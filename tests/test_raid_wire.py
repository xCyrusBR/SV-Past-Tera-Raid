import unittest
from pathlib import Path

from past_raids.raid_wire import (
    RAID_GAME_MARKER,
    RAID_SCENE_ID,
    load_network_info,
    raid_game_data,
    raid_user_password,
)


ROOT = Path(__file__).resolve().parents[1]


class RaidWireTests(unittest.TestCase):
    def test_captured_mewtwo_network_profile(self):
        profile = load_network_info(ROOT / "lab" / "mewtwo-network-info.bin")
        self.assertEqual(profile.scene_id, RAID_SCENE_ID)
        self.assertEqual(profile.channel, 6)
        self.assertEqual(profile.node_count_max, 4)
        self.assertEqual(profile.node_count, 1)
        self.assertEqual(profile.local_comm_version, 21)
        self.assertEqual(profile.link_code, "3065")
        self.assertEqual(profile.advertise_data[125:129], RAID_GAME_MARKER)

    def test_raid_game_data_places_code_and_marker(self):
        game = raid_game_data("0465")
        self.assertEqual(len(game), 40)
        self.assertEqual(game[:4], b"0465")
        self.assertEqual(game[33:37], RAID_GAME_MARKER)

    def test_link_code_is_four_digits(self):
        for invalid in ("123", "12345", "12A4"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    raid_game_data(invalid)

    def test_raid_password_matches_both_physical_captures(self):
        self.assertEqual(raid_user_password("3065").hex(),
                         "d69b2fd8742b6d40885998bf968aa166")
        self.assertEqual(raid_user_password("3387").hex(),
                         "d69821da742b6d40885998bf968aa166")


if __name__ == "__main__":
    unittest.main()
