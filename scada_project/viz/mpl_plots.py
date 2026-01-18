"""matplotlib LIVE: wykresy poziomu i temperatury (4 serie: T1-T4).

Wymagania: aktualizacja na zywo.
Realizacja: FigureCanvasQTAgg osadzony w PyQt5 + QTimer.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


@dataclass
class _Series:
    x: Deque[float]
    y: Deque[float]


class LivePlots:
    """Dwa wykresy: poziom (%) i temperatura (C)."""

    def __init__(self, history_s: float = 120.0, maxlen: int = 600):
        self.history_s = float(history_s)
        self.maxlen = int(maxlen)

        self.fig = Figure(figsize=(6.0, 4.0), dpi=100)
        self.canvas = FigureCanvas(self.fig)

        self.ax_level = self.fig.add_subplot(2, 1, 1)
        self.ax_temp = self.fig.add_subplot(2, 1, 2)
        self.fig.tight_layout(pad=2.0)

        self._t0 = None
        self._series_level: Dict[str, _Series] = {}
        self._series_temp: Dict[str, _Series] = {}
        self._lines_level = {}
        self._lines_temp = {}

    def _ensure(self, names: List[str]) -> None:
        for n in names:
            if n not in self._series_level:
                self._series_level[n] = _Series(deque(maxlen=self.maxlen), deque(maxlen=self.maxlen))
                self._series_temp[n] = _Series(deque(maxlen=self.maxlen), deque(maxlen=self.maxlen))

    def push(self, now_s: float, levels_pct: Dict[str, float], temps_c: Dict[str, float]) -> None:
        if self._t0 is None:
            self._t0 = float(now_s)
        t = float(now_s) - self._t0

        names = sorted(levels_pct.keys())
        self._ensure(names)

        for n in names:
            self._series_level[n].x.append(t)
            self._series_level[n].y.append(float(levels_pct[n]))
            self._series_temp[n].x.append(t)
            self._series_temp[n].y.append(float(temps_c[n]))

        # kasuj stare osie
        self.ax_level.cla()
        self.ax_temp.cla()

        self.ax_level.set_title("Poziom wody (LIVE)")
        self.ax_level.set_xlabel("t [s]")
        self.ax_level.set_ylabel("poziom [%]")
        self.ax_level.set_ylim(0, 100)

        self.ax_temp.set_title("Temperatura (LIVE)")
        self.ax_temp.set_xlabel("t [s]")
        self.ax_temp.set_ylabel("T [C]")

        # rysuj serie
        for n in names:
            xs = list(self._series_level[n].x)
            ys = list(self._series_level[n].y)
            self.ax_level.plot(xs, ys, label=n)

        for n in names:
            xs = list(self._series_temp[n].x)
            ys = list(self._series_temp[n].y)
            self.ax_temp.plot(xs, ys, label=n)

        self.ax_level.legend(loc="upper right", fontsize=8)
        self.ax_temp.legend(loc="upper right", fontsize=8)

        # utrzymaj okno czasu
        if names:
            tmax = max(self._series_level[names[0]].x) if self._series_level[names[0]].x else 0
            self.ax_level.set_xlim(max(0.0, tmax - self.history_s), max(10.0, tmax))
            self.ax_temp.set_xlim(max(0.0, tmax - self.history_s), max(10.0, tmax))

        self.fig.tight_layout(pad=2.0)
        self.canvas.draw_idle()
