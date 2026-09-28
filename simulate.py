#!/usr/bin/env python3
"""Inspect an event package and exercise the minimum host lifecycle offline."""

from argparse import ArgumentParser
from pathlib import Path

from past_raids import EventPackage, HostSimulator


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument(
        "--event",
        type=Path,
        default=Path(__file__).parent / "source-materials" / "mewtwo-event",
    )
    args = parser.parse_args()

    package = EventPackage.load(args.event)
    boss = package.boss(species=150, difficulty=7)
    print(f"event={package.identifier} raid={boss.event_no}")
    print(
        f"boss_species={boss.species} stars={boss.difficulty} level={boss.level} "
        f"tera_type={boss.tera_type} moves={','.join(map(str, boss.moves))}"
    )
    simulator = HostSimulator(package.identifier, boss.event_no)
    for transition in simulator.run_dry():
        print(transition)
    print("offline simulation complete; raid-specific wire messages are not implemented")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

