from pathlib import Path
import unittest

from tools.compare_radio_selections import summarize


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "lab" / "sv-raid-type6-no-type7-7284.jsonl"


@unittest.skipUnless(CAPTURE.is_file(), "private physical-radio capture not available")
class CompareRadioSelectionsTests(unittest.TestCase):
    def test_source_identity_matches_session_join(self):
        result = summarize(CAPTURE)
        self.assertGreater(result["authenticated_pia_packets"], 0)
        join = result["join_variable_ids"]
        self.assertIsNotNone(join)
        selections = result["selections"]
        self.assertEqual(
            [(item["source_role"], item["species"]) for item in selections],
            [("guest", 992), ("host", 151), ("guest", 992)],
        )
        for item in selections:
            self.assertEqual(item["pia_src_var"], join[item["source_role"]])
            self.assertEqual(item["destination_bitmap"],
                             [1] if item["source_role"] == "guest" else [2])


if __name__ == "__main__":
    unittest.main()
