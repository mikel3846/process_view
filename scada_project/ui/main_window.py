"""PyQt5: glowne okno sterowania (wymagane).

Zawiera:
- 4 zbiorniki (widget Zbiornik z projekt_09.pdf),
- sterowanie zbiornikami (napelnij/oproz 3s i 15s, temp zadana),
- 6 zaworow (toggle),
- 3 pompy (suwak predkosci), z blokada "otworz zawor".
- okno alertow (log + alarmy).
- osadzone wykresy matplotlib LIVE.

Uwaga: wizualizacja instalacji i animacje sa w pygame (oddzielne okno) -
spelnia wymagania o widocznym przeplywie przez zakrety 90 stopni.
"""

from __future__ import annotations

import time
import threading
from typing import Dict, Tuple

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QListWidget,
    QSplitter,
)

from ..log.tk_log import TkLogWindow
from ..model.simulation import Instalacja
from ..utils.event_bus import EventBus, LogEvent
from ..viz.mpl_plots import LivePlots
from ..viz.pygame_view import PygameView, PlantSnapshot, PipeSnapshot, TankSnapshot
from .tank_widget import Zbiornik as TankWidget


class AlertsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Okno alertow")
        self.resize(520, 380)
        layout = QVBoxLayout(self)
        self.list = QListWidget()
        layout.addWidget(self.list)

    def add_line(self, line: str) -> None:
        self.list.addItem(line)
        self.list.scrollToBottom()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Etap II - SCADA: 4 zbiorniki, 3 rury, 3 pompy, 6 zaworow")
        self.resize(1350, 760)

        # Bus zdarzen (logi, alarmy, zmiany)
        self.bus = EventBus()

        # Tkinter log (watek)
        self.tk_log = TkLogWindow("Diagnostyka / Log (Tkinter)")
        self.tk_log.start()

        # Stan instalacji (logika)
        self._lock = threading.Lock()
        self.instalacja = Instalacja(log_cb=lambda m: self.bus.emit(m))

        # Okno alertow (PyQt)
        self.alerts = AlertsDialog(self)

        # Subskrypcje logow
        self.bus.subscribe(self._on_log_event)

        # pygame view
        self.pygame_view = PygameView(self._snapshot_for_pygame)
        self.pygame_view.start()

        # matplotlib
        self.plots = LivePlots(history_s=120.0, maxlen=800)

        # --- UI ---
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter)

        # Lewa strona: zbiorniki + sterowanie
        left = QWidget()
        splitter.addWidget(left)
        left_layout = QVBoxLayout(left)

        # Tank widgets (PyQt)
        tanks_box = QGroupBox("Zbiorniki (PyQt5)")
        tanks_grid = QGridLayout(tanks_box)
        self.tank_widgets: Dict[str, TankWidget] = {}
        positions = [(0, 0, "T1"), (0, 1, "T2"), (0, 2, "T3"), (0, 3, "T4")]
        for r, c, name in positions:
            w = TankWidget()
            w.setMinimumSize(250, 340)
            w.setStyleSheet("background-color: #222;")
            w.setPolozenie(25, 20)
            tanks_grid.addWidget(w, r, c)
            self.tank_widgets[name] = w
        left_layout.addWidget(tanks_box)

        controls_split = QSplitter(Qt.Vertical)
        left_layout.addWidget(controls_split, 1)

        # Sterowanie zbiornikami
        tank_ctrl = QGroupBox("Sterowanie zbiornikami")
        tank_ctrl_layout = QGridLayout(tank_ctrl)

        for idx, name in enumerate(["T1", "T2", "T3", "T4"]):
            gb = QGroupBox(name)
            v = QVBoxLayout(gb)
            row1 = QHBoxLayout()
            b_f3 = QPushButton("Napelnij 3s")
            b_f15 = QPushButton("Napelnij 15s")
            row1.addWidget(b_f3)
            row1.addWidget(b_f15)
            v.addLayout(row1)
            row2 = QHBoxLayout()
            b_e3 = QPushButton("Oproznij 3s")
            b_e15 = QPushButton("Oproznij 15s")
            row2.addWidget(b_e3)
            row2.addWidget(b_e15)
            v.addLayout(row2)

            temp_row = QHBoxLayout()
            temp_row.addWidget(QLabel("Temp zadana:"))
            sp = QSpinBox()
            sp.setRange(0, 120)
            sp.setValue(20)
            btn_set = QPushButton("Ustaw")
            temp_row.addWidget(sp)
            temp_row.addWidget(btn_set)
            v.addLayout(temp_row)

            b_f3.clicked.connect(lambda _=False, n=name: self._tank_fill(n, 3.0))
            b_f15.clicked.connect(lambda _=False, n=name: self._tank_fill(n, 15.0))
            b_e3.clicked.connect(lambda _=False, n=name: self._tank_empty(n, 3.0))
            b_e15.clicked.connect(lambda _=False, n=name: self._tank_empty(n, 15.0))
            btn_set.clicked.connect(lambda _=False, n=name, s=sp: self._tank_set_temp(n, s.value()))

            tank_ctrl_layout.addWidget(gb, idx // 2, idx % 2)

        controls_split.addWidget(tank_ctrl)

        # Zawory + pompy
        vp_box = QGroupBox("Zawory i pompy")
        vp = QGridLayout(vp_box)

        # 6 zaworow: kazda rura ma 2
        self.valve_buttons = []  # (idx, which)
        valve_labels = [
            (0, "a", "Zawor T1 (rura T1-T2)"),
            (0, "b", "Zawor T2 (rura T1-T2)"),
            (1, "a", "Zawor T2 (rura T2-T3)"),
            (1, "b", "Zawor T3 (rura T2-T3)"),
            (2, "a", "Zawor T3 (rura T3-T4)"),
            (2, "b", "Zawor T4 (rura T3-T4)"),
        ]
        for i, (pidx, which, text) in enumerate(valve_labels):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setChecked(False)
            btn.setFixedWidth(240)
            btn.clicked.connect(lambda checked, pi=pidx, w=which: self._set_valve(pi, w, checked))
            self.valve_buttons.append((btn, pidx, which))
            vp.addWidget(btn, i // 2, i % 2)

        # 3 pompy: suwak
        self.pump_sliders: Dict[int, QSlider] = {}
        for pidx, name in enumerate(["Pompa P12", "Pompa P23", "Pompa P34"]):
            lbl = QLabel(name)
            s = QSlider(Qt.Horizontal)
            s.setRange(0, 100)
            s.setValue(0)
            s.valueChanged.connect(lambda val, pi=pidx: self._set_pump(pi, val))
            self.pump_sliders[pidx] = s
            row = 3 + pidx
            vp.addWidget(lbl, row, 0)
            vp.addWidget(s, row, 1)

        # przyciski okien
        btn_row = QHBoxLayout()
        b_alerts = QPushButton("Pokaz okno alertow")
        b_alerts.clicked.connect(self.alerts.show)
        btn_row.addWidget(b_alerts)
        btn_row.addStretch(1)
        wrap = QWidget()
        wrap.setLayout(btn_row)
        vp.addWidget(wrap, 6, 0, 1, 2)

        controls_split.addWidget(vp_box)

        # Prawa strona: wykresy
        right = QWidget()
        splitter.addWidget(right)
        rlayout = QVBoxLayout(right)
        plots_box = QGroupBox("Wykresy LIVE (matplotlib)")
        pl = QVBoxLayout(plots_box)
        pl.addWidget(self.plots.canvas)
        rlayout.addWidget(plots_box)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        # Timer symulacji
        self._last_tick = time.time()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(50)  # 20 Hz

        # pierwszy sync
        self._sync_ui_from_model()

    # --- Log handling ---
    def _on_log_event(self, ev: LogEvent) -> None:
        line = ev.format()
        # PyQt alerts
        self.alerts.add_line(line)
        # Tkinter
        self.tk_log.log(line)

    # --- Snapshot for pygame ---
    def _snapshot_for_pygame(self) -> PlantSnapshot:
        with self._lock:
            tanks = [
                TankSnapshot(z.nazwa, z.x, z.y, z.width, z.height, z.poziom, z.temperatura)
                for z in self.instalacja.zbiorniki
            ]
            pipes = []
            for pol in self.instalacja.polaczenia:
                pipes.append(
                    PipeSnapshot(
                        name=pol.nazwa,
                        points=list(pol.rura.punkty),
                        flowing=pol.rura.czy_plynie,
                        direction=pol.rura.kierunek,
                        pump_speed=pol.pompa.predkosc if pol.pompa.wlaczona else 0.0,
                        valve_a_open=pol.zawor_a.otwarty,
                        valve_b_open=pol.zawor_b.otwarty,
                    )
                )
            return PlantSnapshot(tanks=tanks, pipes=pipes)

    # --- Sterowanie zbiornikami ---
    def _tank_fill(self, name: str, dur: float) -> None:
        with self._lock:
            self.instalacja.napelnij(name, dur)

    def _tank_empty(self, name: str, dur: float) -> None:
        with self._lock:
            self.instalacja.oproznij(name, dur)

    def _tank_set_temp(self, name: str, temp: float) -> None:
        with self._lock:
            self.instalacja.ustaw_temp_zadana(name, float(temp))

    # --- Sterowanie zaworami/pompami ---
    def _set_valve(self, pol_idx: int, which: str, open_: bool) -> None:
        with self._lock:
            self.instalacja.ustaw_zawor(pol_idx, which, bool(open_))

    def _set_pump(self, pol_idx: int, slider_value: int) -> None:
        # slider_value 0-100 => 0..1
        speed = float(slider_value) / 100.0
        with self._lock:
            err = self.instalacja.ustaw_pompe_predkosc(pol_idx, speed)

        if err:
            # blokada: nie mozna wlaczyc pompy, jesli zawor zamkniety
            QMessageBox.warning(self, "Blokada pompy", err)
            # reset suwaka
            s = self.pump_sliders[pol_idx]
            s.blockSignals(True)
            s.setValue(0)
            s.blockSignals(False)
            self.bus.emit(err)

    # --- Tick symulacji ---
    def _on_tick(self) -> None:
        now = time.time()
        dt = max(0.001, now - self._last_tick)
        self._last_tick = now

        with self._lock:
            self.instalacja.tick(dt)

            # dane do wykresow
            levels = {z.nazwa: z.poziom * 100.0 for z in self.instalacja.zbiorniki}
            temps = {z.nazwa: z.temperatura for z in self.instalacja.zbiorniki}

        self.plots.push(now, levels, temps)
        self._sync_ui_from_model()

    def _sync_ui_from_model(self) -> None:
        """Synchronizacja GUI (PyQt) ze stanem modelu."""
        with self._lock:
            # zbiorniki
            for z in self.instalacja.zbiorniki:
                tw = self.tank_widgets.get(z.nazwa)
                if tw:
                    tw.setName(z.nazwa)
                    tw.setTemp(z.temperatura)
                    tw.setPoziom(z.poziom)

            # zawory
            for btn, pidx, which in self.valve_buttons:
                pol = self.instalacja.polaczenia[pidx]
                st = pol.zawor_a.otwarty if which == "a" else pol.zawor_b.otwarty
                btn.blockSignals(True)
                btn.setChecked(st)
                # prosta sygnalizacja kolorem
                btn.setStyleSheet("background-color: #2b7;" if st else "background-color: #b22;")
                btn.blockSignals(False)

            # pompy
            for pidx, s in self.pump_sliders.items():
                pol = self.instalacja.polaczenia[pidx]
                val = int(pol.pompa.predkosc * 100) if pol.pompa.wlaczona else 0
                s.blockSignals(True)
                s.setValue(val)
                s.blockSignals(False)


def run_app() -> None:
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w.show()
    app.exec_()
