from pathlib import Path
import unittest

from tools.compare_eden_opening_records import compare


ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "lab" / "eden-two-client-raid-decoded.jsonl"
NEW = ROOT / "lab" / "eden-two-client-distinct-20260929-decoded.jsonl"


@unittest.skipUnless(OLD.is_file() and NEW.is_file(), "private Eden captures not available")
class CompareEdenOpeningRecordsTests(unittest.TestCase):
    def test_only_counter_and_countdown_change(self):
        by_type = {item["type"]: item for item in compare(OLD, NEW)}
        self.assertEqual(by_type["80332c"]["changed_offsets"], [4])
        self.assertEqual(by_type["80332d"]["changed_offsets"], [4])
        self.assertEqual(by_type["80332e"]["changed_offsets"], [4])
        self.assertEqual(by_type["803330"]["changed_offsets"], [4, 34])


if __name__ == "__main__":
    unittest.main()
