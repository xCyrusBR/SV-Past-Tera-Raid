from pathlib import Path
import unittest

from past_raids import EventPackage, HostSimulator, HostState


ROOT = Path(__file__).parents[1]
EVENT = ROOT / "source-materials" / "mewtwo-event"


class EventPackageTests(unittest.TestCase):
    def test_mewtwo_event_fields(self):
        package = EventPackage.load(EVENT)
        boss = package.boss(species=150, difficulty=7)
        self.assertEqual(20230901, package.identifier)
        self.assertEqual(2023090101, boss.event_no)
        self.assertEqual(100, boss.level)
        self.assertEqual(15, boss.tera_type)
        self.assertEqual((540, 396, 58, 347), boss.moves)
        self.assertEqual(5000, boss.hp_multiplier)
        self.assertEqual(5, len(package.files))

    def test_minimum_host_lifecycle(self):
        simulator = HostSimulator(20230901, 2023090101)
        journal = simulator.run_dry()
        self.assertEqual(HostState.DISCONNECTED, simulator.state)
        self.assertEqual(5, len(journal))
        self.assertEqual("BATTLE_STARTED -> DISCONNECTED", journal[-1])

    def test_cannot_skip_ready(self):
        simulator = HostSimulator(20230901, 2023090101)
        simulator.advance(HostState.ADVERTISING)
        simulator.advance(HostState.PARTICIPANT_JOINED)
        with self.assertRaises(ValueError):
            simulator.advance(HostState.BATTLE_STARTED)


if __name__ == "__main__":
    unittest.main()

