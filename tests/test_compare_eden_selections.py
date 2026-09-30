import json
from pathlib import Path
import tempfile
import unittest

from tools.compare_eden_selections import summarize


class CompareEdenSelectionsTests(unittest.TestCase):
    def test_deduplicates_relay_and_retransmission(self):
        def row(source, direction, sequence, pokemon):
            payload = (bytes.fromhex("80332e") + bytes(15) + pokemon * 344).hex()
            return {
                "event": "proxy", "direction": direction, "source_ip": source,
                "elapsed": 1.0, "line": 1,
                "messages": [{"protocol": 0x80, "port": 0,
                              "reliable": {"is_ack": False, "sequence_id": sequence,
                                           "payload": payload}}],
            }

        rows = [row("host", "client_to_server", 4, b"a"),
                row("host", "server_to_client", 4, b"a"),
                row("host", "client_to_server", 4, b"a"),
                row("guest", "client_to_server", 2, b"b")]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.jsonl"
            path.write_text("\n".join(json.dumps(item) for item in rows), encoding="utf-8")
            summary = summarize(path)
        self.assertEqual(summary["stations_with_selection"], 2)
        self.assertTrue(summary["first_selections_distinct"])
        self.assertTrue(summary["latest_selections_distinct"])
        self.assertEqual(len(summary["selections"]), 2)

    def test_identical_selected_pokemon_are_not_distinct(self):
        rows = []
        for source in ("host", "guest"):
            rows.append({"event": "proxy", "direction": "client_to_server",
                         "source_ip": source, "elapsed": 1.0,
                         "messages": [{"protocol": 0x80, "port": 0,
                                       "reliable": {"sequence_id": 2,
                                                    "payload": (bytes.fromhex("80332e")
                                                                + bytes(15) + b"a" * 344).hex()}}]})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.jsonl"
            path.write_text("\n".join(json.dumps(item) for item in rows), encoding="utf-8")
            self.assertFalse(summarize(path)["first_selections_distinct"])
            self.assertFalse(summarize(path)["latest_selections_distinct"])

    def test_host_seen_only_on_relay(self):
        rows = []
        for source, direction, pokemon in (("host", "server_to_client", b"a"),
                                           ("guest", "client_to_server", b"b")):
            rows.append({"event": "proxy", "direction": direction,
                         "source_ip": source, "elapsed": 1.0,
                         "messages": [{"protocol": 0x80, "port": 0,
                                       "reliable": {"sequence_id": 2,
                                                    "payload": (bytes.fromhex("80332e")
                                                                + bytes(15) + pokemon * 344).hex()}}]})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.jsonl"
            path.write_text("\n".join(json.dumps(item) for item in rows), encoding="utf-8")
            self.assertTrue(summarize(path)["first_selections_distinct"])

    def test_late_guest_selection_makes_final_pair_distinct(self):
        rows = []
        for source, sequence, pokemon in (("guest", 2, b"a"),
                                          ("host", 3, b"a"),
                                          ("guest", 4, b"b")):
            rows.append({"event": "proxy", "direction": "client_to_server",
                         "source_ip": source, "elapsed": float(sequence),
                         "messages": [{"protocol": 0x80, "port": 0,
                                       "reliable": {"sequence_id": sequence,
                                                    "payload": (bytes.fromhex("80332e")
                                                                + bytes(15) + pokemon * 344).hex()}}]})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.jsonl"
            path.write_text("\n".join(json.dumps(item) for item in rows), encoding="utf-8")
            summary = summarize(path)
        self.assertFalse(summary["first_selections_distinct"])
        self.assertTrue(summary["latest_selections_distinct"])


if __name__ == "__main__":
    unittest.main()
