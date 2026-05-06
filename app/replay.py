from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ReplayEngine:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.index = 0
        self.is_paused = True

    def load_file(self, path: str | Path) -> int:
        p = Path(path)
        self.events = []
        self.index = 0
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                self.events.append(json.loads(line))
        print(f"Replay loaded: {p} events={len(self.events)}")
        return len(self.events)

    def play(self, speed: float = 1.0) -> None:
        self.is_paused = False
        print(f"Replay play speed={speed:.2f}")
        while not self.is_paused and self.index < len(self.events):
            event = self.events[self.index]
            print(f"REPLAY[{self.index}] ts={event.get('ts')} price={event.get('price')} signal={event.get('signal')}")
            self.index += 1

    def pause(self) -> None:
        self.is_paused = True
        print("Replay paused")

    def step(self) -> dict[str, Any] | None:
        if self.index >= len(self.events):
            print("Replay end")
            return None
        event = self.events[self.index]
        print(f"REPLAY STEP[{self.index}] {event}")
        self.index += 1
        return event
