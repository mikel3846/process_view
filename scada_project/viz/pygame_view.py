"""pygame: wizualizacja instalacji + animacje przeplywu, zaworow i pomp.

Wymagania:
- 4 zbiorniki T1..T4,
- DOKLADNIE 3 rury, kazda z 2 zakretami 90 stopni (4 punkty),
- widoczny przeplyw (kropki) tylko gdy rzeczywiscie zachodzi,
- zawory (6) jako dwa trojkaty "dziubkami" do siebie, zielony/czerwony,
- pompy (3) z animacja obrotu zalezna od predkosci.

Realizacja: okno pygame w osobnym watku (Spyder-friendly). Stan jest czytany
z obiektu Instalacja przez funkcje snapshot_cb.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple


@dataclass(frozen=True)
class PipeSnapshot:
    name: str
    points: List[Tuple[float, float]]
    flowing: bool
    direction: int
    pump_speed: float
    valve_a_open: bool
    valve_b_open: bool


@dataclass(frozen=True)
class TankSnapshot:
    name: str
    x: float
    y: float
    w: float
    h: float
    level: float  # 0..1
    temp: float


@dataclass(frozen=True)
class PlantSnapshot:
    tanks: List[TankSnapshot]
    pipes: List[PipeSnapshot]


def _polyline_segments(points: List[Tuple[float, float]]):
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        dx, dy = (x2 - x1), (y2 - y1)
        length = math.hypot(dx, dy)
        yield (x1, y1, x2, y2, length)


class PygameView:
    def __init__(self, snapshot_cb: Callable[[], PlantSnapshot], title: str = "Instalacja (pygame)"):
        self.snapshot_cb = snapshot_cb
        self.title = title

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._stop = threading.Event()

        # animacja kropek w rurach
        self._phase: Dict[str, float] = {}
        self._pump_rot: Dict[str, float] = {}

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        import pygame

        pygame.init()
        screen = pygame.display.set_mode((980, 520))
        pygame.display.set_caption(self.title)

        clock = pygame.time.Clock()
        font = pygame.font.SysFont(None, 18)

        def draw_valve(surf, pos, open_):
            # dwa trojkaty dziubkami do siebie
            x, y = pos
            size = 10
            color = (0, 200, 0) if open_ else (200, 0, 0)
            # lewy trojkat
            tri1 = [(x - size, y - size), (x - size, y + size), (x, y)]
            # prawy trojkat
            tri2 = [(x + size, y - size), (x + size, y + size), (x, y)]
            pygame.draw.polygon(surf, color, tri1)
            pygame.draw.polygon(surf, color, tri2)

        def draw_pump(surf, center, speed, dt, key):
            # kolo + wirnik (linia obracajaca sie)
            x, y = center
            r = 16
            pygame.draw.circle(surf, (120, 120, 120), (int(x), int(y)), r, 3)
            rot = self._pump_rot.get(key, 0.0)
            if speed > 0:
                rot += dt * (2.0 + 10.0 * speed)
            self._pump_rot[key] = rot
            angle = rot
            x2 = x + math.cos(angle) * (r - 3)
            y2 = y + math.sin(angle) * (r - 3)
            pygame.draw.line(surf, (180, 180, 180), (int(x), int(y)), (int(x2), int(y2)), 3)

        def draw_flow(surf, points, flowing, direction, speed, key, dt):
            # rysuj obudowe rury
            pygame.draw.lines(surf, (160, 160, 160), False, [(int(x), int(y)) for x, y in points], 10)

            if not flowing:
                return

            # animacja kropek wzdloz polilinii
            phase = self._phase.get(key, 0.0)
            phase += dt * (40.0 + 160.0 * speed) * (1 if direction >= 0 else -1)
            self._phase[key] = phase

            # oblicz dlugosc calkowita
            segs = list(_polyline_segments(points))
            total = sum(s[-1] for s in segs)
            if total <= 0:
                return

            # kilka kropek
            step = 28.0
            for k in range(10):
                dist = (phase + k * step) % total
                # znajdz segment
                acc = 0.0
                for x1, y1, x2, y2, L in segs:
                    if acc + L >= dist:
                        t = 0.0 if L == 0 else (dist - acc) / L
                        x = x1 + (x2 - x1) * t
                        y = y1 + (y2 - y1) * t
                        pygame.draw.circle(surf, (0, 180, 255), (int(x), int(y)), 4)
                        break
                    acc += L

        while not self._stop.is_set():
            dt = clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._stop.set()

            snap = self.snapshot_cb()

            screen.fill((25, 25, 25))

            # zbiorniki
            for t in snap.tanks:
                rect = pygame.Rect(int(t.x), int(t.y), int(t.w), int(t.h))
                pygame.draw.rect(screen, (230, 230, 230), rect, 3)
                # ciecz
                if t.level > 0:
                    hliq = int(t.h * t.level)
                    liq = pygame.Rect(int(t.x) + 3, int(t.y + t.h - hliq) + 2, int(t.w) - 6, hliq - 4)
                    pygame.draw.rect(screen, (0, 120, 255), liq)
                label = font.render(f"{t.name}  {int(t.level*100)}%  {t.temp:.1f}C", True, (240, 240, 240))
                screen.blit(label, (int(t.x), int(t.y) - 18))

            # rury + przeplyw + zawory + pompy
            for p in snap.pipes:
                draw_flow(screen, p.points, p.flowing, p.direction, p.pump_speed, p.name, dt)

                # zawory: przy pierwszym i ostatnim punkcie
                (x1, y1) = p.points[0]
                (x2, y2) = p.points[-1]
                draw_valve(screen, (x1, y1), p.valve_a_open)
                draw_valve(screen, (x2, y2), p.valve_b_open)

                # pompa: na srodku najdluzszego poziomego odcinka rury
                mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                best_L = -1.0
                for (sx, sy, ex, ey, L) in _polyline_segments(p.points):
                    if abs(ey - sy) < 1e-6 and L > best_L:  # poziomy
                        best_L = L
                        mx = (sx + ex) / 2.0
                        my = sy - 25
                draw_pump(screen, (mx, my), p.pump_speed if p.flowing else 0.0, dt, p.name)

            pygame.display.flip()

        pygame.quit()
