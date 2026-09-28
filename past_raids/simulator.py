"""Protocol-neutral state machine for the minimum raid-host lifetime.

This deliberately does not invent Scarlet/Violet raid packets.  It defines the observable
contract the future LDN/Pia adapter must satisfy and makes invalid transitions explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class HostState(Enum):
    CREATED = auto()
    ADVERTISING = auto()
    PARTICIPANT_JOINED = auto()
    PARTICIPANT_READY = auto()
    BATTLE_STARTED = auto()
    DISCONNECTED = auto()


_NEXT = {
    HostState.CREATED: HostState.ADVERTISING,
    HostState.ADVERTISING: HostState.PARTICIPANT_JOINED,
    HostState.PARTICIPANT_JOINED: HostState.PARTICIPANT_READY,
    HostState.PARTICIPANT_READY: HostState.BATTLE_STARTED,
    HostState.BATTLE_STARTED: HostState.DISCONNECTED,
}


@dataclass
class HostSimulator:
    event_identifier: int
    raid_event_no: int
    state: HostState = HostState.CREATED
    journal: list[str] = field(default_factory=list)

    def advance(self, target: HostState) -> None:
        expected = _NEXT.get(self.state)
        if target is not expected:
            raise ValueError(f"invalid transition {self.state.name} -> {target.name}; expected {expected}")
        self.journal.append(f"{self.state.name} -> {target.name}")
        self.state = target

    def run_dry(self) -> tuple[str, ...]:
        while self.state is not HostState.DISCONNECTED:
            self.advance(_NEXT[self.state])
        return tuple(self.journal)

