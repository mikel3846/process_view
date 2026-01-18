"""Prosty bus zdarzen / logger.

Wymagania Etap II:
- dedykowane okno alertow (w PyQt5),
- dodatkowe okno/panel pomocniczy (Tkinter) do logow/diagnostyki,
- wpisy o zmianach zaworow/pomp/predkosci + alarmy.

Ten modul dostarcza wspolny dispatcher komunikatow, aby latwo wysylac logi
do wielu odbiorcow (PyQt, Tkinter).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List


@dataclass(frozen=True)
class LogEvent:
    timestamp: datetime
    message: str

    def format(self) -> str:
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.message}"


class EventBus:
    def __init__(self):
        self._subs: List[Callable[[LogEvent], None]] = []
        self._lock = threading.Lock()

    def subscribe(self, cb: Callable[[LogEvent], None]) -> None:
        with self._lock:
            self._subs.append(cb)

    def emit(self, message: str) -> None:
        ev = LogEvent(datetime.now(), str(message))
        with self._lock:
            subs = list(self._subs)
        for cb in subs:
            try:
                cb(ev)
            except Exception:
                # Nie wysypuj calej aplikacji przez pojedynczy blad subskrybenta
                pass
