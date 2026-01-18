"""Silnik symulacji (tick-based)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .entities import PolaczenieRury, Pompa, Rura, Zawor, Zbiornik


@dataclass
class RampAction:
    """Akcja liniowa w czasie: zmiana wartosci z start do target w czasie duration."""

    start_time: float
    duration: float
    start_value: float
    target_value: float

    def value_at(self, now: float) -> float:
        if self.duration <= 0:
            return self.target_value
        t = (now - self.start_time) / self.duration
        if t <= 0:
            return self.start_value
        if t >= 1:
            return self.target_value
        return self.start_value + (self.target_value - self.start_value) * t

    def finished(self, now: float) -> bool:
        return (now - self.start_time) >= self.duration


class Instalacja:
    """Stan calej instalacji + logika procesu."""

    def __init__(self, log_cb: Optional[Callable[[str], None]] = None):
        self.log_cb = log_cb

        # Zbiorniki (pozycje x,y sa uzywane przez pygame; w PyQt sa niezalezne)
        self.T1 = Zbiornik(80, 260, nazwa="T1")
        self.T2 = Zbiornik(280, 260, nazwa="T2")
        self.T3 = Zbiornik(480, 260, nazwa="T3")
        self.T4 = Zbiornik(680, 260, nazwa="T4")
        self.zbiorniki: List[Zbiornik] = [self.T1, self.T2, self.T3, self.T4]

        # Poczatkowy stan (dla efektu): T1 ma troche wody
        self.T1.aktualna_ilosc = 50.0
        self.T1.aktualizuj_poziom()

        # Akcje ramp (napelnianie/oproz) per zbiornik
        self._ramp_actions: Dict[str, Optional[RampAction]] = {z.nazwa: None for z in self.zbiorniki}

        # Rury: musza miec 2 zakrety (4 punkty)
        self.polaczenia: List[PolaczenieRury] = self._zbuduj_polaczenia()

        # Alarmy
        self._last_alarm_state: Dict[str, Dict[str, bool]] = {z.nazwa: {"hi": False, "lo": False, "temp": False} for z in self.zbiorniki}

    def _log(self, msg: str) -> None:
        if self.log_cb:
            self.log_cb(msg)

    def _zbuduj_polaczenia(self) -> List[PolaczenieRury]:
        def mk_pipe(zA: Zbiornik, zB: Zbiornik) -> Rura:
            """Tworzy przebieg rury jak na rysunku uzytkownika:
            start w dolnym srodku zbiornika A, odcinek w dol,
            potem poziomo do srodka miedzy zbiornikami, pionowo w gore
            do poziomu gornej krawedzi zbiornika B i poziomo do wejscia.

            Daje to "U"-ksztalt z wyraznymi zakretami 90 stopni.
            """

            p_start = zA.punkt_dol_srodek()      # (x, y) - dol A
            p_end = zB.punkt_gora_srodek()       # (x, y) - gora B

            # zejscie ponizej zbiornikow
            y_low = p_start[1] + 60
            # punkt posredni w polowie odleglosci w osi X
            x_mid = (p_start[0] + p_end[0]) / 2.0
            # wzniesienie do poziomu gornej krawedzi zbiornika B
            y_top = p_end[1]

            return Rura([
                p_start,
                (p_start[0], y_low),
                (x_mid, y_low),
                (x_mid, y_top),
                p_end,
            ])

        pol = []
        # T1-T2
        p1 = Pompa("P12", on_change=self._log)
        v1a = Zawor("T1 (T1-T2)", "rura T1-T2", on_change=self._log)
        v1b = Zawor("T2 (T1-T2)", "rura T1-T2", on_change=self._log)
        pol.append(PolaczenieRury("T1-T2", self.T1, self.T2, mk_pipe(self.T1, self.T2), p1, v1a, v1b))

        # T2-T3
        p2 = Pompa("P23", on_change=self._log)
        v2a = Zawor("T2 (T2-T3)", "rura T2-T3", on_change=self._log)
        v2b = Zawor("T3 (T2-T3)", "rura T2-T3", on_change=self._log)
        pol.append(PolaczenieRury("T2-T3", self.T2, self.T3, mk_pipe(self.T2, self.T3), p2, v2a, v2b))

        # T3-T4
        p3 = Pompa("P34", on_change=self._log)
        v3a = Zawor("T3 (T3-T4)", "rura T3-T4", on_change=self._log)
        v3b = Zawor("T4 (T3-T4)", "rura T3-T4", on_change=self._log)
        pol.append(PolaczenieRury("T3-T4", self.T3, self.T4, mk_pipe(self.T3, self.T4), p3, v3a, v3b))

        return pol

    # ---- Sterowanie zbiornikami ----
    def napelnij(self, nazwa: str, duration_s: float) -> None:
        z = self._get_tank(nazwa)
        now = time.time()
        self._ramp_actions[nazwa] = RampAction(now, duration_s, z.aktualna_ilosc, z.pojemnosc)
        self._log(f"{nazwa}: napelnianie przez {int(duration_s)}s")

    def oproznij(self, nazwa: str, duration_s: float) -> None:
        z = self._get_tank(nazwa)
        now = time.time()
        self._ramp_actions[nazwa] = RampAction(now, duration_s, z.aktualna_ilosc, 0.0)
        self._log(f"{nazwa}: oproznianie przez {int(duration_s)}s")

    def ustaw_temp_zadana(self, nazwa: str, temp: float) -> None:
        z = self._get_tank(nazwa)
        z.temp_zadana = float(temp)
        self._log(f"{nazwa}: temp zadana = {z.temp_zadana:.1f}C")

    def _get_tank(self, nazwa: str) -> Zbiornik:
        for z in self.zbiorniki:
            if z.nazwa == nazwa:
                return z
        raise KeyError(nazwa)

    # ---- Sterowanie pompami/zaworami ----
    def ustaw_zawor(self, pol_idx: int, which: str, otwarty: bool) -> None:
        pol = self.polaczenia[pol_idx]
        zawor = pol.zawor_a if which == "a" else pol.zawor_b
        zawor.ustaw(otwarty)

        # jesli pompa pracuje, a ktorys zawor zostal zamkniety -> wylacz pompe
        if pol.pompa.wlaczona and not pol.zawory_otwarte():
            pol.pompa.ustaw_wlaczenie(False)
            pol.pompa.ustaw_predkosc(0.0)
            self._log(f"Pompa {pol.pompa.identyfikator}: wylaczona (zamkniety zawor)")

    def ustaw_pompe_predkosc(self, pol_idx: int, predkosc_0_1: float) -> Optional[str]:
        """Ustawia predkosc. Zwraca komunikat bledu jesli nie mozna wlaczyc."""
        pol = self.polaczenia[pol_idx]
        predkosc_0_1 = max(0.0, min(1.0, float(predkosc_0_1)))

        if predkosc_0_1 <= 0.0:
            # wylacz
            pol.pompa.ustaw_predkosc(0.0)
            if pol.pompa.wlaczona:
                pol.pompa.ustaw_wlaczenie(False)
                pol.zawor_a.ustaw(False)
                pol.zawor_b.ustaw(False)
            return None

        # proba wlaczenia
        if not pol.zawory_otwarte():
            # wymaganie: komunikat + identyfikator zamknietego zaworu
            zamkniete = []
            if not pol.zawor_a.otwarty:
                zamkniete.append(pol.zawor_a.identyfikator)
            if not pol.zawor_b.otwarty:
                zamkniete.append(pol.zawor_b.identyfikator)
            return "Otworz zawor: " + ", ".join(zamkniete)

        pol.pompa.ustaw_wlaczenie(True)
        pol.pompa.ustaw_predkosc(predkosc_0_1)
        # wymaganie: wlaczenie pompy otwiera oba zawory
        pol.zawor_a.ustaw(True)
        pol.zawor_b.ustaw(True)
        return None

    def wymus_otworz_zawory_dla_pompy(self, pol_idx: int) -> None:
        pol = self.polaczenia[pol_idx]
        pol.zawor_a.ustaw(True)
        pol.zawor_b.ustaw(True)

    # ---- Tick symulacji ----
    def tick(self, dt_s: float) -> None:
        now = time.time()

        # 1) rampy napelniania/oproz
        for z in self.zbiorniki:
            act = self._ramp_actions.get(z.nazwa)
            if not act:
                continue
            z.aktualna_ilosc = max(0.0, min(z.pojemnosc, act.value_at(now)))
            z.aktualizuj_poziom()
            if act.finished(now):
                self._ramp_actions[z.nazwa] = None

        # 2) grzanie (stopniowo do temp_zadana)
        for z in self.zbiorniki:
            if z.temperatura < z.temp_zadana:
                z.temperatura = min(z.temp_zadana, z.temperatura + 0.8 * dt_s)
            elif z.temperatura > z.temp_zadana:
                z.temperatura = max(z.temp_zadana, z.temperatura - 0.3 * dt_s)

        # 3) przeplywy przez pompy
        base_flow_per_s = 20.0  # jednostek/sek przy predkosc=1
        for pol in self.polaczenia:
            # domyslnie brak przeplywu
            pol.rura.ustaw_przeplyw(False, 1)

            if not (pol.pompa.wlaczona and pol.zawory_otwarte()):
                continue

            # kierunek: od A do B (jak w opisie rur). Mozna rozbudowac o odwrotny.
            z_src = pol.zbiornik_a
            z_dst = pol.zbiornik_b
            kierunek = 1

            if z_src.czy_pusty():
                pol.rura.ustaw_przeplyw(False, kierunek)
                self._log(f"{pol.nazwa}: brak wody w zrodle, wylacz pompe")
                pol.pompa.ustaw_wlaczenie(False)
                pol.pompa.ustaw_predkosc(0.0)
                continue

            if z_dst.czy_pelny():
                continue

            amount = base_flow_per_s * pol.pompa.predkosc * dt_s
            removed = z_src.usun_ciecz(amount)
            added = z_dst.dodaj_ciecz(removed)
            if added < removed:
                # gdyby dst sie zapelnil, zwroc nadmiar do src
                z_src.dodaj_ciecz(removed - added)

            if removed > 0:
                pol.rura.ustaw_przeplyw(True, kierunek)

        # 4) alarmy
        self._update_alarms()

    def _update_alarms(self) -> None:
        for z in self.zbiorniki:
            hi = (z.poziom * 100.0) > 80.0
            lo = (z.poziom * 100.0) < 5.0
            tt = z.temperatura > 80.0

            last = self._last_alarm_state[z.nazwa]
            if hi and not last["hi"]:
                self._log(f"ALARM: {z.nazwa} poziom > 80%")
            if lo and not last["lo"]:
                self._log(f"ALARM: {z.nazwa} poziom < 5%")
            if tt and not last["temp"]:
                self._log(f"ALARM: {z.nazwa} temperatura > 80C")

            last["hi"], last["lo"], last["temp"] = hi, lo, tt
