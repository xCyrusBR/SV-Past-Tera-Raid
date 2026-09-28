import hashlib
from pathlib import Path
import tempfile
import unittest

from past_raids.save_injector import (
    KEY_TERA_RAID_PALDEA,
    RAID_BLOCKS,
    decode_save,
    encode_save,
    inject_event,
    materialize_might7,
    verify_round_trip,
)


ROOT = Path(__file__).parents[1]
SAVE = ROOT / "source-materials" / "scarlet-save" / "main"
EVENT = ROOT / "source-materials" / "mewtwo-event"


class SaveInjectorTests(unittest.TestCase):
    def test_source_save_round_trip_is_byte_identical(self):
        raw = SAVE.read_bytes()
        verify_round_trip(raw)
        self.assertEqual(encode_save(decode_save(raw)), raw)

    def test_injects_all_five_mewtwo_blocks_without_changing_size(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "main"
            result = inject_event(SAVE, EVENT, output)
            self.assertEqual(result["identifier"], "20230901")
            self.assertEqual(output.stat().st_size, SAVE.stat().st_size)
            self.assertNotEqual(result["source_sha256"], result["output_sha256"])

            blocks = {block.key: block.data for block in decode_save(output.read_bytes())}
            for base_name, key in RAID_BLOCKS.items():
                expected = (EVENT / "Files" / f"{base_name}_1_3_0").read_bytes()
                self.assertEqual(blocks[key], expected)

    def test_refuses_in_place_or_overwrite(self):
        with self.assertRaises(ValueError):
            inject_event(SAVE, EVENT, SAVE)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "main"
            output.write_bytes(b"keep")
            before = hashlib.sha256(output.read_bytes()).digest()
            with self.assertRaises(FileExistsError):
                inject_event(SAVE, EVENT, output)
            self.assertEqual(hashlib.sha256(output.read_bytes()).digest(), before)

    def test_materializes_might7_from_active_black_crystal(self):
        with tempfile.TemporaryDirectory() as directory:
            injected = Path(directory) / "injected"
            materialized = Path(directory) / "materialized"
            inject_event(SAVE, EVENT, injected)
            result = materialize_might7(injected, materialized)
            self.assertEqual(result["raid_index"], 0)
            block = next(x for x in decode_save(materialized.read_bytes()) if x.key == KEY_TERA_RAID_PALDEA)
            self.assertEqual(int.from_bytes(block.data[0x10 + 0x18:0x10 + 0x1C], "little"), 3)


if __name__ == "__main__":
    unittest.main()
