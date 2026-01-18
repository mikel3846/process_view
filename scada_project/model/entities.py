"""Logika procesu (bez GUI).

Wymagane klasy z projekt10.pdf: Rura, Zbiornik.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

Point = Tuple[float, float]


@dataclass
class Zawor:
    identyfikator: str
    opis: str
    otwarty: bool = False
    on_change: Optional[Callable[[str], None]] = None

    def ustaw(self, otwarty: bool) -> None:
        if self.otwarty == otwarty:
            return
        self.otwarty = otwarty
        if self.on_change:
            stan = "otwarty" if self.otwarty else "zamkniety"
            self.on_change(f"Zawor {self.identyfikator} {stan} ({self.opis})")


@dataclass
class Pompa:
    identyfikator: str
    predkosc: float = 0.0  # 0.0-1.0
    wlaczona: bool = False
    on_change: Optional[Callable[[str], None]] = None

    def ustaw_predkosc(self, predkosc: float) -> None:
        predkosc = max(0.0, min(1.0, float(predkosc)))
        if abs(self.predkosc - predkosc) < 1e-6:
            return
        self.predkosc = predkosc
        if self.on_change:
            self.on_change(f"Pompa {self.identyfikator} predkosc: {int(self.predkosc*100)}%")

    def ustaw_wlaczenie(self, wlaczona: bool) -> None:
        if self.wlaczona == wlaczona:
            return
        self.wlaczona = wlaczona
        if self.on_change:
            self.on_change(f"Pompa {self.identyfikator} {'wlaczona' if wlaczona else 'wylaczona'}")


class Rura:
    """Klasa Rura wg projekt10.pdf (punkty linii lamanej + flaga przeplywu)."""

    def __init__(self, punkty: List[Point], grubosc: int = 12, kolor_rury: Tuple[int, int, int] = (160, 160, 160)):
        self.punkty: List[Point] = [(float(x), float(y)) for x, y in punkty]
        self.grubosc = int(grubosc)
        self.kolor_rury = kolor_rury
        self.czy_plynie: bool = False
        self.kierunek: int = 1  # 1: start->koniec, -1: odwrotnie

    def ustaw_przeplyw(self, plynie: bool, kierunek: int = 1) -> None:
        self.czy_plynie = bool(plynie)
        self.kierunek = 1 if kierunek >= 0 else -1


class Zbiornik:
    """Klasa Zbiornik wg projekt10.pdf (stan, dodaj_ciecz, usun_ciecz)."""

    def __init__(self, x: float, y: float, width: float = 100, height: float = 140, nazwa: str = ""):
        self.x = float(x)
        self.y = float(y)
        self.width = float(width)
        self.height = float(height)
        self.nazwa = nazwa

        self.pojemnosc = 100.0
        self.aktualna_ilosc = 0.0
        self.poziom = 0.0  # 0.0-1.0

        self.temperatura = 20.0
        self.temp_zadana = 20.0

    def dodaj_ciecz(self, ilosc: float) -> float:
        wolne = self.pojemnosc - self.aktualna_ilosc
        dodano = min(float(ilosc), wolne)
        self.aktualna_ilosc += dodano
        self.aktualizuj_poziom()
        return dodano

    def usun_ciecz(self, ilosc: float) -> float:
        usunieto = min(float(ilosc), self.aktualna_ilosc)
        self.aktualna_ilosc -= usunieto
        self.aktualizuj_poziom()
        return usunieto

    def aktualizuj_poziom(self) -> None:
        self.poziom = 0.0 if self.pojemnosc <= 0 else self.aktualna_ilosc / self.pojemnosc

    def czy_pusty(self) -> bool:
        return self.aktualna_ilosc <= 0.0001

    def czy_pelny(self) -> bool:
        return self.aktualna_ilosc >= self.pojemnosc - 0.0001

    def punkt_gora_srodek(self) -> Point:
        return (self.x + self.width / 2.0, self.y)

    def punkt_dol_srodek(self) -> Point:
        return (self.x + self.width / 2.0, self.y + self.height)


@dataclass
class PolaczenieRury:
    """Jedna rura w instalacji: 2 zawory + pompa + 2 zbiorniki."""

    nazwa: str
    zbiornik_a: Zbiornik
    zbiornik_b: Zbiornik
    rura: Rura
    pompa: Pompa
    zawor_a: Zawor
    zawor_b: Zawor

    def zawory_otwarte(self) -> bool:
        return self.zawor_a.otwarty and self.zawor_b.otwarty
