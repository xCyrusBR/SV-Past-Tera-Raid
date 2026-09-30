import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pokeldn-research"))
from pokeldn.sv.raid_retry import RetryWindow, replay_send_due, ready_schedule_shift


class RaidRetryTests(unittest.TestCase):
    def test_immediate_ready_can_advance_without_changing_relative_phase_intervals(self):
        shift = ready_schedule_shift(42.7, 10, 0.1, immediate=True)
        self.assertAlmostEqual(10.1, 42.7 + shift)
        self.assertAlmostEqual(17.545, 50.145 + shift)
        self.assertEqual(0, ready_schedule_shift(42.7, 10, 0.1))
        self.assertAlmostEqual(2.4, ready_schedule_shift(42.7, 45, 0.1, immediate=True))

    def test_pacing_cannot_overtake_deferred_predecessor(self):
        self.assertFalse(replay_send_due(58, 57, 4, 3))
        self.assertFalse(replay_send_due(86, 72, 4, 3))
        self.assertTrue(replay_send_due(72, 72, 4, 3))
        self.assertFalse(replay_send_due(73, 73, 4, 4.02))
        self.assertTrue(replay_send_due(73, 73, 4.03, 4.02))
        self.assertTrue(replay_send_due(53, 74, 4.03, 4.02))

    def test_gap_preserves_payload_and_flags(self):
        window = RetryWindow()
        window.acknowledge(127)
        window.remember(127, 19, b"original compressed fragment", 127, 0)
        window.remember(128, 17, b"continuation", 127, 0)
        self.assertIsNone(window.due(0.1))
        self.assertEqual((127, 19, b"original compressed fragment", 127), window.due(0.4))
        self.assertEqual(127, window.lowest(220))
        window.acknowledge(128)
        self.assertEqual(128, window.due(0.8)[0])
        window.acknowledge(129)
        self.assertIsNone(window.due(2))
        self.assertEqual(220, window.lowest(220))

    def test_ack_monotonic_and_replayed_acked_retry_not_reinserted(self):
        window = RetryWindow()
        window.acknowledge(60)
        window.acknowledge(1)
        window.remember(53, 5, b"old retry", 52, 0)
        self.assertEqual(60, window.ack_id)
        self.assertFalse(window.pending)
        window.acknowledge(65535)
        self.assertEqual(60, window.ack_id)

    def test_retry_bounded_and_does_not_originate_opening(self):
        window = RetryWindow(interval=0.1, max_attempts=2)
        window.remember(3, 7, b"lobby", 1, 0)
        self.assertFalse(window.pending)
        window.remember(44, 7, b"battle", 44, 0)
        self.assertIsNone(window.due(1))
        window.acknowledge(44)
        self.assertIsNotNone(window.due(1))
        self.assertIsNotNone(window.due(2))
        self.assertIsNone(window.due(3))


if __name__ == "__main__":
    unittest.main()
